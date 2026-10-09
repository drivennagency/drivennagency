// Vercel serverless function: live websitebezoekers (GA4) voor het Drivenn Agency dashboard.
//
// Geeft het aantal actieve gebruikers van de laatste 30 dagen terug, plus de
// procentuele groei t.o.v. de 30 dagen daarvoor.
//
// Vereiste environment variables (Vercel -> Settings -> Environment Variables):
//   GA4_PROPERTY_ID         - het numerieke GA4-property-ID (Admin -> Property Settings
//                             in Google Analytics, bv. "123456789", zonder "properties/"-prefix)
//   GOOGLE_GA_CLIENT_EMAIL  - "client_email" uit het service-account JSON-keybestand
//   GOOGLE_GA_PRIVATE_KEY   - de private key (zelfde vorm als GOOGLE_SC_PRIVATE_KEY:
//                             bij voorkeur 1 regel base64 van het hele PEM-bestand)
//   (ontbreken GOOGLE_GA_CLIENT_EMAIL/GOOGLE_GA_PRIVATE_KEY, dan wordt teruggevallen
//    op GOOGLE_SC_CLIENT_EMAIL/GOOGLE_SC_PRIVATE_KEY -- hetzelfde service-account kan
//    prima ook Viewer-toegang krijgen tot de GA4-property, dan hoeft er geen tweede
//    service-account aangemaakt te worden)
//
// Het service-account moet als gebruiker (rol "Viewer"/"Lezer") zijn toegevoegd aan de
// GA4-property: Beheer -> Property Access Management -> gebruiker toevoegen, met het
// e-mailadres uit GOOGLE_GA_CLIENT_EMAIL (of GOOGLE_SC_CLIENT_EMAIL als je dat hergebruikt).

function base64url(buf) {
  return buf.toString("base64").replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

function normalizePrivateKey(raw) {
  let key = raw.trim();
  if ((key.startsWith('"') && key.endsWith('"')) || (key.startsWith("'") && key.endsWith("'"))) {
    key = key.slice(1, -1).trim();
  }
  if (!key.includes("BEGIN PRIVATE KEY")) {
    try {
      const decoded = Buffer.from(key, "base64").toString("utf8");
      if (decoded.includes("BEGIN PRIVATE KEY")) key = decoded;
    } catch (e) {
      // fall through -- diagnostic hieronder
    }
  }
  key = key.replace(/\\+n/g, "\n");
  key = key.replace(/\r\n/g, "\n").replace(/\r/g, "\n");
  key = key.trim() + "\n";
  if (!key.includes("BEGIN PRIVATE KEY") || !key.includes("END PRIVATE KEY")) {
    const preview = raw.trim().slice(0, 25).replace(/[^\x20-\x7e]/g, "?");
    throw new Error(
      `GOOGLE_GA_PRIVATE_KEY lijkt niet een geldige PEM-key of base64-key te zijn (${raw.length} tekens, begint met "${preview}..."). Verwacht tekst die begint met -----BEGIN PRIVATE KEY----- of de base64-vorm daarvan.`
    );
  }
  return key;
}

async function getAccessToken(clientEmail, privateKeyRaw) {
  const privateKey = normalizePrivateKey(privateKeyRaw);
  const crypto = require("crypto");
  const now = Math.floor(Date.now() / 1000);
  const header = { alg: "RS256", typ: "JWT" };
  const claims = {
    iss: clientEmail,
    scope: "https://www.googleapis.com/auth/analytics.readonly",
    aud: "https://oauth2.googleapis.com/token",
    iat: now,
    exp: now + 3600,
  };
  const signingInput =
    base64url(Buffer.from(JSON.stringify(header))) + "." + base64url(Buffer.from(JSON.stringify(claims)));
  let signature;
  try {
    signature = crypto.createSign("RSA-SHA256").update(signingInput).sign(privateKey);
  } catch (signErr) {
    const lineCount = privateKey.split("\n").length;
    throw new Error(
      `Ondertekenen met GOOGLE_GA_PRIVATE_KEY is mislukt (${privateKey.length} tekens, ${lineCount} regels, header/footer wel aanwezig): ${signErr.message}`
    );
  }
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

  const propertyId = process.env.GA4_PROPERTY_ID;
  const clientEmail = process.env.GOOGLE_GA_CLIENT_EMAIL || process.env.GOOGLE_SC_CLIENT_EMAIL;
  const privateKey = process.env.GOOGLE_GA_PRIVATE_KEY || process.env.GOOGLE_SC_PRIVATE_KEY;

  if (!propertyId || !clientEmail || !privateKey) {
    res.status(200).json({
      configured: false,
      message:
        "GA4-koppeling nog niet ingesteld. Voeg GA4_PROPERTY_ID en GOOGLE_GA_CLIENT_EMAIL/GOOGLE_GA_PRIVATE_KEY (of hergebruik GOOGLE_SC_CLIENT_EMAIL/GOOGLE_SC_PRIVATE_KEY) toe in Vercel.",
      visitors30d: null,
      growthPct: null,
      updatedAt: new Date().toISOString(),
    });
    return;
  }

  try {
    const accessToken = await getAccessToken(clientEmail, privateKey);

    const reportRes = await fetch(
      `https://analyticsdata.googleapis.com/v1beta/properties/${encodeURIComponent(propertyId)}:runReport`,
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${accessToken}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          dateRanges: [
            { startDate: "30daysAgo", endDate: "today", name: "current" },
            { startDate: "60daysAgo", endDate: "31daysAgo", name: "previous" },
          ],
          dimensions: [{ name: "dateRange" }],
          metrics: [{ name: "activeUsers" }],
        }),
      }
    );
    const reportData = await reportRes.json();
    if (!reportRes.ok) {
      throw new Error(reportData?.error?.message || `GA4-rapport mislukt (${reportRes.status})`);
    }

    const rows = reportData.rows || [];
    const currentRow = rows.find((r) => r.dimensionValues?.[0]?.value === "current") || rows[0];
    const previousRow = rows.find((r) => r.dimensionValues?.[0]?.value === "previous") || rows[1];
    const current = currentRow ? parseInt(currentRow.metricValues[0].value, 10) : 0;
    const previous = previousRow ? parseInt(previousRow.metricValues[0].value, 10) : 0;
    const growthPct = previous > 0 ? Math.round(((current - previous) / previous) * 1000) / 10 : null;

    res.status(200).json({
      configured: true,
      visitors30d: current,
      growthPct,
      updatedAt: new Date().toISOString(),
    });
  } catch (err) {
    res.status(200).json({
      configured: true,
      error: err.message,
      visitors30d: null,
      growthPct: null,
      updatedAt: new Date().toISOString(),
    });
  }
};
