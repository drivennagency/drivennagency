// Vercel serverless function: live websitebezoekers (GA4) voor het Drivenn Agency dashboard.
// Geeft het aantal actieve gebruikers van de laatste 30 dagen terug, plus de
// procentuele groei ten opzichte van de 30 dagen daarvoor.
//
// Vereiste environment variables (Vercel -> Settings -> Environment Variables):
//   GA4_PROPERTY_ID         - het numerieke GA4-property-ID (Beheer -> Property-instellingen,
//                             bv. "123456789", zonder "properties/"-prefix)
//   GOOGLE_GA_CLIENT_EMAIL  - "client_email" uit het service-account JSON-keybestand
//   GOOGLE_GA_PRIVATE_KEY   - de private key (zelfde vorm als GOOGLE_SC_PRIVATE_KEY)
//   Ontbreken GOOGLE_GA_CLIENT_EMAIL/GOOGLE_GA_PRIVATE_KEY, dan worden GOOGLE_SC_CLIENT_EMAIL/
//   GOOGLE_SC_PRIVATE_KEY gebruikt: hetzelfde service-account kan ook Lezer worden van de GA4-property.
//
// Het service-account moet als gebruiker met de rol "Lezer" zijn toegevoegd aan de GA4-property
// (Beheer -> Toegangsbeheer voor property -> gebruiker toevoegen).

const { getAccessToken, sendJson, handleMethod } = require("./_lib/google");

const CACHE_SECONDS = 900;

function empty(extra) {
  return Object.assign({ visitors30d: null, growthPct: null, updatedAt: new Date().toISOString() }, extra);
}

// Pure functie (los getest): haalt huidige en vorige periode uit een GA4 runReport-antwoord.
function summarize(report) {
  const rows = (report && report.rows) || [];
  const pick = (name, fallback) =>
    rows.find((r) => r.dimensionValues && r.dimensionValues[0] && r.dimensionValues[0].value === name) || rows[fallback];
  const value = (row) => (row ? parseInt(row.metricValues[0].value, 10) || 0 : 0);
  const current = value(pick("current", 0));
  const previous = value(pick("previous", 1));
  const growthPct = previous > 0 ? Math.round(((current - previous) / previous) * 1000) / 10 : null;
  return { visitors30d: current, growthPct };
}

async function handler(req, res) {
  if (handleMethod(req, res)) return;

  const propertyId = process.env.GA4_PROPERTY_ID;
  const clientEmail = process.env.GOOGLE_GA_CLIENT_EMAIL || process.env.GOOGLE_SC_CLIENT_EMAIL;
  const privateKey = process.env.GOOGLE_GA_PRIVATE_KEY || process.env.GOOGLE_SC_PRIVATE_KEY;

  if (!propertyId || !clientEmail || !privateKey) {
    sendJson(req, res, 200, empty({
      configured: false,
      message:
        "GA4-koppeling nog niet ingesteld. Voeg GA4_PROPERTY_ID en GOOGLE_GA_CLIENT_EMAIL/GOOGLE_GA_PRIVATE_KEY " +
        "(of hergebruik GOOGLE_SC_CLIENT_EMAIL/GOOGLE_SC_PRIVATE_KEY) toe in Vercel.",
    }), 0);
    return;
  }

  try {
    const accessToken = await getAccessToken({
      clientEmail,
      privateKey,
      scope: "https://www.googleapis.com/auth/analytics.readonly",
      varName: process.env.GOOGLE_GA_PRIVATE_KEY ? "GOOGLE_GA_PRIVATE_KEY" : "GOOGLE_SC_PRIVATE_KEY",
    });

    const reportRes = await fetch(
      `https://analyticsdata.googleapis.com/v1beta/properties/${encodeURIComponent(propertyId)}:runReport`,
      {
        method: "POST",
        headers: { Authorization: `Bearer ${accessToken}`, "Content-Type": "application/json" },
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
    const report = await reportRes.json().catch(() => ({}));
    if (!reportRes.ok) {
      throw new Error((report.error && report.error.message) || `GA4-rapport mislukt (${reportRes.status})`);
    }

    sendJson(req, res, 200, Object.assign({ configured: true }, summarize(report), { updatedAt: new Date().toISOString() }), CACHE_SECONDS);
  } catch (err) {
    sendJson(req, res, 200, empty({ configured: true, error: err.message }), 0);
  }
}

module.exports = handler;
module.exports.summarize = summarize;
