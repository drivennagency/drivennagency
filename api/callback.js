// Afronding van de GitHub-login: wisselt de code om voor een token en geeft dat terug aan
// Sveltia CMS via postMessage (Decap-compatibel formaat).
//
// Beveiliging:
// - de "state" van GitHub moet overeenkomen met het cookie dat /api/auth heeft gezet;
// - het token wordt alleen gegeven aan een venster op deze website zelf of op een van de
//   toegestane adressen (ALLOWED_ORIGINS, uit te breiden met de env-variabele CMS_ALLOWED_ORIGINS,
//   kommagescheiden), zodat een andere website die dit loginvenster opent het token nooit ziet.
const crypto = require("crypto");
const { STATE_COOKIE } = require("./auth");

const ALLOWED_ORIGINS = ["https://www.drivennagency.nl", "https://drivennagency.nl"];

function allowedOrigins(host) {
  const extra = (process.env.CMS_ALLOWED_ORIGINS || "").split(",").map((o) => o.trim()).filter(Boolean);
  return Array.from(new Set([`https://${host}`, ...ALLOWED_ORIGINS, ...extra]));
}

function readCookie(req, name) {
  const header = req.headers.cookie || "";
  for (const part of header.split(";")) {
    const [k, ...v] = part.trim().split("=");
    if (k === name) return decodeURIComponent(v.join("="));
  }
  return null;
}

function sameState(a, b) {
  if (!a || !b || a.length !== b.length) return false;
  return crypto.timingSafeEqual(Buffer.from(a), Buffer.from(b));
}

// JSON veilig binnen een <script>-blok plaatsen.
function scriptJson(value) {
  return JSON.stringify(value).replace(/</g, "\\u003c").replace(/>/g, "\\u003e").replace(/&/g, "\\u0026");
}

function page(req, res, status, content) {
  const message = "authorization:github:" + status + ":" + JSON.stringify(content);
  const html =
    '<!doctype html><html lang="nl"><head><meta charset="utf-8"><meta name="robots" content="noindex"><title>Inloggen</title></head><body><script>' +
    "(function(){" +
    "var message=" + scriptJson(message) + ";" +
    "var allowed=" + scriptJson(allowedOrigins(req.headers.host)) + ";" +
    "function receive(e){if(allowed.indexOf(e.origin)===-1)return;" +
    "window.opener&&window.opener.postMessage(message,e.origin);" +
    "window.removeEventListener('message',receive,false);}" +
    "window.addEventListener('message',receive,false);" +
    "allowed.forEach(function(o){window.opener&&window.opener.postMessage('authorizing:github',o);});" +
    "})();" +
    "</script><p>" + (status === "success" ? "Inloggen afgerond, je kunt dit venster sluiten." : "Inloggen is niet gelukt. Sluit dit venster en probeer het opnieuw.") +
    "</p></body></html>";

  res.setHeader("Content-Type", "text/html; charset=utf-8");
  res.setHeader("Cache-Control", "no-store");
  // Het state-cookie is eenmalig: altijd opruimen.
  res.setHeader("Set-Cookie", `${STATE_COOKIE}=; Path=/api; Max-Age=0; HttpOnly; Secure; SameSite=Lax`);
  res.end(html);
}

module.exports = async (req, res) => {
  const clientId = process.env.GITHUB_CLIENT_ID;
  const clientSecret = process.env.GITHUB_CLIENT_SECRET;
  if (!clientId || !clientSecret) {
    res.statusCode = 500;
    res.setHeader("Content-Type", "text/plain; charset=utf-8");
    res.end("GitHub OAuth-omgevingsvariabelen ontbreken.");
    return;
  }

  const url = new URL(req.url, `https://${req.headers.host}`);
  const code = url.searchParams.get("code");
  const state = url.searchParams.get("state");

  if (!code) {
    page(req, res, "error", { error: url.searchParams.get("error") || "no_code" });
    return;
  }
  if (!sameState(state, readCookie(req, STATE_COOKIE))) {
    page(req, res, "error", { error: "invalid_state" });
    return;
  }

  try {
    const tokenRes = await fetch("https://github.com/login/oauth/access_token", {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({ client_id: clientId, client_secret: clientSecret, code }),
    });
    const data = await tokenRes.json().catch(() => ({}));
    if (data && data.access_token) {
      page(req, res, "success", { token: data.access_token, provider: "github" });
    } else {
      page(req, res, "error", { error: (data && data.error) || "no_token" });
    }
  } catch (e) {
    page(req, res, "error", { error: "request_failed" });
  }
};

module.exports.readCookie = readCookie;
module.exports.allowedOrigins = allowedOrigins;
module.exports.sameState = sameState;
module.exports.scriptJson = scriptJson;
