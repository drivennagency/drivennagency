// Vercel serverless function: live Google Search Console-cijfers voor het Drivenn Agency dashboard.
// Geeft de top zoekwoorden (clicks/vertoningen/CTR/positie) van de laatste 28 dagen terug,
// zodat nieuwe blogs beter kunnen aansluiten op waar mensen al naar zoeken.
//
// Vereiste environment variables (Vercel -> Settings -> Environment Variables):
//   GOOGLE_SC_CLIENT_EMAIL  - het "client_email" veld uit het service-account JSON-keybestand
//   GOOGLE_SC_PRIVATE_KEY   - het "private_key" veld uit datzelfde bestand (incl. BEGIN/END regels;
//                             newlines mogen als letterlijke \n staan, deze functie zet ze terug om)
//   GOOGLE_SC_SITE_URL      - de property-naam exact zoals die in Search Console staat,
//                             bv. "https://drivennagency.nl/" (URL-prefix) of "sc-domain:drivennagency.nl"
//
// Hoe dit werkt: het service-account tekent zelf een JWT (geen interactieve login nodig) en wisselt
// die in voor een access token bij Google, zolang het service-account als gebruiker is toegevoegd
// aan de Search Console-property (Instellingen -> Gebruikers en API-toegang -> Gebruiker toevoegen,
// "Restricted" volstaat voor deze alleen-lezen koppeling).

function base64url(buf) {
  return buf.toString("base64").replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

async function getAccessToken(clientEmail, privateKeyRaw) {
  const privateKey = privateKeyRaw.includes("\\n") ? privateKeyRaw.replace(/\\n/g, "\n") : privateKeyRaw;
  const crypto = require("crypto");
  const now = Math.floor(Date.now() / 1000);
  const header = { alg: "RS256", typ: "JWT" };
  const claims = {
    iss: clientEmail,
    scope: "https://www.googleapis.com/auth/webmasters.readonly",
    aud: "https://oauth2.googleapis.com/token",
    iat: now,
    exp: now + 3600,
  };
  const signingInput =
    base64url(Buffer.from(JSON.stringify(header))) + "." + base64url(Buffer.from(JSON.stringify(claims)));
  const signature = crypto.createSign("RSA-SHA256").update(signingInput).sign(privateKey);
  const jwt = signingInput + "." + base64url(signature);

  const res = await fetch("https://oauth2.googleapis.com/token", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body:
      "grant_type=" +
      encodeURIComponent("urn:ietf:params:oauth:grant-type:jwt-bearer") +
      "&assertion=" +
      encodeURIComponent(jwt),
  });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data?.error_description || data?.error || `Token-aanvraag mislukt (${res.status})`);
  }
  return data.access_token;
}

module.exports = async function handler(req, res) {
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "GET, OPTIONS");
  if (req.method === "OPTIONS") {
    res.status(204).end();
    return;
  }

  const clientEmail = process.env.GOOGLE_SC_CLIENT_EMAIL;
  const privateKey = process.env.GOOGLE_SC_PRIVATE_KEY;
  const siteUrl = process.env.GOOGLE_SC_SITE_URL;

  if (!clientEmail || !privateKey || !siteUrl) {
    res.status(200).json({
      configured: false,
      message:
        "Search Console-koppeling nog niet ingesteld. Voeg GOOGLE_SC_CLIENT_EMAIL, GOOGLE_SC_PRIVATE_KEY en GOOGLE_SC_SITE_URL toe in Vercel.",
      topQueries: [],
      updatedAt: new Date().toISOString(),
    });
    return;
  }

  try {
    const accessToken = await getAccessToken(clientEmail, privateKey);

    const end = new Date();
    const start = new Date(end.getTime() - 28 * 24 * 60 * 60 * 1000);
    const fmt = (d) => d.toISOString().slice(0, 10);

    const queryRes = await fetch(
      `https://searchconsole.googleapis.com/webmasters/v3/sites/${encodeURIComponent(siteUrl)}/searchAnalytics/query`,
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${accessToken}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          startDate: fmt(start),
          endDate: fmt(end),
          dimensions: ["query"],
          rowLimit: 25,
        }),
      }
    );
    const queryData = await queryRes.json();
    if (!queryRes.ok) {
      throw new Error(queryData?.error?.message || `Search Console-query mislukt (${queryRes.status})`);
    }

    const topQueries = (queryData.rows || []).map((row) => ({
      query: row.keys[0],
      clicks: row.clicks,
      impressions: row.impressions,
      ctr: Math.round(row.ctr * 1000) / 10, // percentage, 1 decimaal
      position: Math.round(row.position * 10) / 10,
    }));

    res.status(200).json({
      configured: true,
      periodDays: 28,
      topQueries,
      updatedAt: new Date().toISOString(),
    });
  } catch (err) {
    res.status(200).json({
      configured: true,
      error: err.message,
      topQueries: [],
      updatedAt: new Date().toISOString(),
    });
  }
};
