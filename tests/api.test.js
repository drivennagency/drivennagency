// Tests voor de serverless functies in /api. Draaien met: node --test tests/
// Er wordt niets naar buiten verstuurd: fetch wordt waar nodig vervangen door een nepversie.
const test = require("node:test");
const assert = require("node:assert/strict");
const crypto = require("node:crypto");

const google = require("../api/_lib/google");
const analytics = require("../api/analytics-stats");
const searchConsole = require("../api/search-console-stats");
const social = require("../api/social-stats");
const auth = require("../api/auth");
const callback = require("../api/callback");

function fakeRes() {
  const res = {
    statusCode: 200, headers: {}, body: "",
    setHeader(k, v) { this.headers[k.toLowerCase()] = v; },
    getHeader(k) { return this.headers[k.toLowerCase()]; },
    writeHead(code, h) { this.statusCode = code; Object.entries(h || {}).forEach(([k, v]) => this.setHeader(k, v)); },
    end(b) { this.body = b || ""; this.ended = true; },
  };
  return res;
}
const req = (extra) => Object.assign({ method: "GET", url: "/", headers: { host: "www.drivennagency.nl" } }, extra);

function withEnv(vars, fn) {
  const old = {};
  for (const k of Object.keys(vars)) { old[k] = process.env[k]; if (vars[k] === undefined) delete process.env[k]; else process.env[k] = vars[k]; }
  const restore = () => { for (const k of Object.keys(old)) { if (old[k] === undefined) delete process.env[k]; else process.env[k] = old[k]; } };
  return Promise.resolve().then(fn).finally(restore);
}

const { privateKey: PEM, publicKey } = crypto.generateKeyPairSync("rsa", {
  modulusLength: 2048,
  privateKeyEncoding: { type: "pkcs8", format: "pem" },
  publicKeyEncoding: { type: "spki", format: "pem" },
});

test("private key: PEM, base64, \\n-escaped en met aanhalingstekens worden allemaal herkend", () => {
  const variants = [
    PEM,
    Buffer.from(PEM).toString("base64"),
    PEM.replace(/\n/g, "\\n"),
    PEM.replace(/\n/g, "\\\\n"),
    '"' + PEM.replace(/\n/g, "\\n") + '"',
    PEM.replace(/\n/g, "\r\n"),
  ];
  for (const v of variants) {
    const key = google.normalizePrivateKey(v, "TEST_KEY");
    assert.ok(key.startsWith("-----BEGIN PRIVATE KEY-----\n"));
    assert.ok(key.endsWith("-----END PRIVATE KEY-----\n"));
  }
});

test("private key: onzin geeft een duidelijke fout zonder de sleutel te tonen", () => {
  assert.throws(() => google.normalizePrivateKey("geheim-maar-geen-sleutel-1234567890", "TEST_KEY"), /TEST_KEY lijkt geen geldige/);
});

test("JWT wordt correct ondertekend en bevat de juiste claims", () => {
  const jwt = google.signJwt("sa@example.iam.gserviceaccount.com", PEM, "scope-x", "TEST_KEY", 1700000000);
  const [h, c, s] = jwt.split(".");
  const ok = crypto.createVerify("RSA-SHA256").update(h + "." + c).verify(publicKey, Buffer.from(s, "base64url"));
  assert.ok(ok);
  const claims = JSON.parse(Buffer.from(c, "base64url").toString());
  assert.deepEqual(claims, {
    iss: "sa@example.iam.gserviceaccount.com", scope: "scope-x",
    aud: "https://oauth2.googleapis.com/token", iat: 1700000000, exp: 1700003600,
  });
});

test("GA4: samenvatting en groeipercentage", () => {
  const report = { rows: [
    { dimensionValues: [{ value: "previous" }], metricValues: [{ value: "80" }] },
    { dimensionValues: [{ value: "current" }], metricValues: [{ value: "100" }] },
  ] };
  assert.deepEqual(analytics.summarize(report), { visitors30d: 100, growthPct: 25 });
  assert.deepEqual(analytics.summarize({}), { visitors30d: 0, growthPct: null });
});

for (const [name, handler, field] of [["analytics-stats", analytics, "visitors30d"], ["search-console-stats", searchConsole, "topQueries"], ["social-stats", social, "instagram"]]) {
  test(`${name}: zonder configuratie een nette melding, niet gecachet`, () => withEnv({
    GA4_PROPERTY_ID: undefined, GOOGLE_GA_CLIENT_EMAIL: undefined, GOOGLE_GA_PRIVATE_KEY: undefined,
    GOOGLE_SC_CLIENT_EMAIL: undefined, GOOGLE_SC_PRIVATE_KEY: undefined, GOOGLE_SC_SITE_URL: undefined,
    META_PAGE_ACCESS_TOKEN: undefined, META_IG_BUSINESS_ID: undefined, META_PAGE_ID: undefined,
  }, async () => {
    const res = fakeRes();
    await handler(req(), res);
    const body = JSON.parse(res.body);
    assert.equal(res.statusCode, 200);
    assert.equal(body.configured, false);
    assert.ok(field in body);
    assert.equal(res.headers["access-control-allow-origin"], "*");
    assert.equal(res.headers["cache-control"], "no-store");
  }));

  test(`${name}: OPTIONS en POST`, async () => {
    const r1 = fakeRes(); await handler(req({ method: "OPTIONS" }), r1); assert.equal(r1.statusCode, 204);
    const r2 = fakeRes(); await handler(req({ method: "POST" }), r2); assert.equal(r2.statusCode, 405);
  });
}

test("search-console-stats: antwoordvorm blijft gelijk (gebruikt door de blogroutine)", () => withEnv({
  GOOGLE_SC_CLIENT_EMAIL: "sa@example.iam.gserviceaccount.com",
  GOOGLE_SC_PRIVATE_KEY: Buffer.from(PEM).toString("base64"),
  GOOGLE_SC_SITE_URL: "sc-domain:drivennagency.nl",
}, async () => {
  const realFetch = global.fetch;
  const calls = [];
  global.fetch = async (url, opts) => {
    calls.push(url);
    if (url.includes("oauth2")) return { ok: true, json: async () => ({ access_token: "tok" }) };
    assert.equal(opts.headers.Authorization, "Bearer tok");
    return { ok: true, json: async () => ({ rows: [{ keys: ["website laten maken"], clicks: 3, impressions: 120, ctr: 0.025, position: 8.43 }] }) };
  };
  try {
    const res = fakeRes();
    await searchConsole(req(), res);
    const body = JSON.parse(res.body);
    assert.equal(body.configured, true);
    assert.equal(body.periodDays, 28);
    assert.deepEqual(body.topQueries, [{ query: "website laten maken", clicks: 3, impressions: 120, ctr: 2.5, position: 8.4 }]);
    assert.match(res.headers["cache-control"], /s-maxage=3600/);
    assert.ok(calls[1].includes(encodeURIComponent("sc-domain:drivennagency.nl")));
  } finally { global.fetch = realFetch; }
}));

test("auth: stuurt door naar GitHub met state, en bewaart die state in een veilig cookie", () => withEnv({ GITHUB_CLIENT_ID: "abc" }, () => {
  const res = fakeRes();
  auth(req(), res);
  assert.equal(res.statusCode, 302);
  const loc = new URL(res.headers.location);
  assert.equal(loc.origin, "https://github.com");
  assert.equal(loc.searchParams.get("redirect_uri"), "https://www.drivennagency.nl/api/callback");
  const state = loc.searchParams.get("state");
  assert.match(state, /^[0-9a-f]{48}$/);
  assert.match(res.headers["set-cookie"], new RegExp(`^${auth.STATE_COOKIE}=${state};.*HttpOnly; Secure; SameSite=Lax`));
}));

test("callback: weigert een terugkeer zonder geldige state (geen token-aanvraag)", () => withEnv({ GITHUB_CLIENT_ID: "abc", GITHUB_CLIENT_SECRET: "def" }, async () => {
  const realFetch = global.fetch;
  let fetched = false;
  global.fetch = async () => { fetched = true; return { json: async () => ({}) }; };
  try {
    for (const cookie of [undefined, `${auth.STATE_COOKIE}=anders`]) {
      const res = fakeRes();
      await callback(req({ url: "/api/callback?code=x&state=goed", headers: { host: "www.drivennagency.nl", cookie } }), res);
      assert.match(res.body, /invalid_state/);
      assert.doesNotMatch(res.body, /"token"/);
    }
    assert.equal(fetched, false);
  } finally { global.fetch = realFetch; }
}));

test("callback: geldige state levert het token alleen aan toegestane origins", () => withEnv({ GITHUB_CLIENT_ID: "abc", GITHUB_CLIENT_SECRET: "def", CMS_ALLOWED_ORIGINS: undefined }, async () => {
  const realFetch = global.fetch;
  global.fetch = async () => ({ json: async () => ({ access_token: "gho_test</script>" }) });
  try {
    const res = fakeRes();
    await callback(req({ url: "/api/callback?code=x&state=s123", headers: { host: "www.drivennagency.nl", cookie: `a=b; ${auth.STATE_COOKIE}=s123` } }), res);
    assert.match(res.body, /authorization:github:success/);
    assert.doesNotMatch(res.body, /gho_test<\/script>/, "token mag het script-blok niet kunnen afsluiten");
    assert.doesNotMatch(res.body, /postMessage\([^)]*"\*"/, "nooit naar willekeurige origins posten");
    assert.match(res.headers["set-cookie"], /Max-Age=0/);
    assert.deepEqual(callback.allowedOrigins("www.drivennagency.nl"), ["https://www.drivennagency.nl", "https://drivennagency.nl"]);
  } finally { global.fetch = realFetch; }
}));

test("callback: hulpfuncties", () => {
  assert.equal(callback.readCookie({ headers: { cookie: "x=1; y=a%20b" } }, "y"), "a b");
  assert.equal(callback.readCookie({ headers: {} }, "y"), null);
  assert.equal(callback.sameState("abc", "abc"), true);
  assert.equal(callback.sameState("abc", "abd"), false);
  assert.equal(callback.sameState("abc", null), false);
  assert.equal(callback.scriptJson("</script>"), '"\\u003c/script\\u003e"');
});
