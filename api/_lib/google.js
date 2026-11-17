// Gedeelde code voor de Google-koppelingen (Search Console en GA4).
// Bestanden in een map die met "_" begint worden door Vercel niet als endpoint gepubliceerd.
//
// Een service-account tekent zelf een JWT en wisselt die in voor een access token,
// zonder interactieve login. Het service-account moet als (lees)gebruiker zijn
// toegevoegd aan de Search Console-property en/of de GA4-property.

const crypto = require("crypto");

const TOKEN_URL = "https://oauth2.googleapis.com/token";

function base64url(buf) {
  return buf.toString("base64").replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

// Private keys raken in omgevingsvariabelen op allerlei manieren beschadigd (echte regeleinden
// weg, \n dubbel ge-escaped, aanhalingstekens eromheen, \r van Windows). Daarom ruim normaliseren.
// Aanbevolen vorm: één regel base64 van het hele PEM-bestand. Foutmeldingen tonen nooit de sleutel.
function normalizePrivateKey(raw, varName) {
  let key = String(raw).trim();
  if ((key.startsWith('"') && key.endsWith('"')) || (key.startsWith("'") && key.endsWith("'"))) {
    key = key.slice(1, -1).trim();
  }
  if (!key.includes("BEGIN PRIVATE KEY")) {
    const decoded = Buffer.from(key, "base64").toString("utf8");
    if (decoded.includes("BEGIN PRIVATE KEY")) key = decoded;
  }
  key = key.replace(/\\+n/g, "\n").replace(/\r\n?/g, "\n").trim() + "\n";
  if (!key.includes("BEGIN PRIVATE KEY") || !key.includes("END PRIVATE KEY")) {
    const preview = String(raw).trim().slice(0, 25).replace(/[^\x20-\x7e]/g, "?");
    throw new Error(
      `${varName} lijkt geen geldige PEM-key of base64-key te zijn (${String(raw).length} tekens, begint met "${preview}..."). ` +
        "Verwacht tekst die begint met -----BEGIN PRIVATE KEY----- of de base64-vorm daarvan."
    );
  }
  return key;
}

function signJwt(clientEmail, privateKey, scope, varName, nowSeconds) {
  const now = nowSeconds || Math.floor(Date.now() / 1000);
  const header = { alg: "RS256", typ: "JWT" };
  const claims = { iss: clientEmail, scope, aud: TOKEN_URL, iat: now, exp: now + 3600 };
  const input = base64url(Buffer.from(JSON.stringify(header))) + "." + base64url(Buffer.from(JSON.stringify(claims)));
  let signature;
  try {
    signature = crypto.createSign("RSA-SHA256").update(input).sign(privateKey);
  } catch (err) {
    throw new Error(
      `Ondertekenen met ${varName} is mislukt (${privateKey.length} tekens, ${privateKey.split("\n").length} regels): ${err.message}`
    );
  }
  return input + "." + base64url(signature);
}

async function getAccessToken({ clientEmail, privateKey, scope, varName }) {
  const key = normalizePrivateKey(privateKey, varName);
  const jwt = signJwt(clientEmail, key, scope, varName);
  const res = await fetch(TOKEN_URL, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body:
      "grant_type=" + encodeURIComponent("urn:ietf:params:oauth:grant-type:jwt-bearer") +
      "&assertion=" + encodeURIComponent(jwt),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.error_description || data.error || `Token-aanvraag mislukt (${res.status})`);
  }
  return data.access_token;
}

// Gemeenschappelijke headers voor de dashboard-endpoints: openbaar leesbaar (CORS), en kort
// gecachet aan de rand van Vercel zodat niet elke paginaweergave de Google-quota aanspreekt.
function sendJson(req, res, status, body, cacheSeconds) {
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "GET, OPTIONS");
  res.setHeader("Content-Type", "application/json; charset=utf-8");
  res.setHeader(
    "Cache-Control",
    cacheSeconds ? `public, max-age=0, s-maxage=${cacheSeconds}, stale-while-revalidate=${cacheSeconds * 4}` : "no-store"
  );
  res.statusCode = status;
  res.end(JSON.stringify(body));
}

// Afhandeling van preflight en niet-ondersteunde methodes. Geeft true terug als het verzoek klaar is.
function handleMethod(req, res) {
  if (req.method === "OPTIONS") {
    res.setHeader("Access-Control-Allow-Origin", "*");
    res.setHeader("Access-Control-Allow-Methods", "GET, OPTIONS");
    res.statusCode = 204;
    res.end();
    return true;
  }
  if (req.method !== "GET" && req.method !== "HEAD") {
    res.setHeader("Allow", "GET, OPTIONS");
    sendJson(req, res, 405, { error: "Alleen GET wordt ondersteund." }, 0);
    return true;
  }
  return false;
}

module.exports = { base64url, normalizePrivateKey, signJwt, getAccessToken, sendJson, handleMethod };
