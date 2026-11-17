// Vercel serverless function: live Google Search Console-cijfers voor het Drivenn Agency dashboard.
// Geeft de top zoekwoorden (clicks/vertoningen/CTR/positie) van de laatste 28 dagen terug,
// zodat nieuwe blogs beter kunnen aansluiten op waar mensen al naar zoeken.
//
// Vereiste environment variables (Vercel -> Settings -> Environment Variables):
//   GOOGLE_SC_CLIENT_EMAIL  - het "client_email" veld uit het service-account JSON-keybestand
//   GOOGLE_SC_PRIVATE_KEY   - de private key, bij voorkeur als EEN REGEL base64 van het hele PEM-bestand
//                             (normale PEM met echte of \n-regeleinden wordt ook herkend)
//   GOOGLE_SC_SITE_URL      - de property-naam exact zoals in Search Console,
//                             bv. "https://drivennagency.nl/" (URL-prefix) of "sc-domain:drivennagency.nl"
//
// Het service-account moet als gebruiker zijn toegevoegd aan de Search Console-property
// (Instellingen -> Gebruikers en API-toegang -> Gebruiker toevoegen, "Beperkt" volstaat).
//
// Let op: de vorm van het antwoord wordt gebruikt door de wekelijkse blogroutine. Velden niet hernoemen.

const { getAccessToken, sendJson, handleMethod } = require("./_lib/google");

const PERIOD_DAYS = 28;
const CACHE_SECONDS = 3600;

module.exports = async function handler(req, res) {
  if (handleMethod(req, res)) return;

  const clientEmail = process.env.GOOGLE_SC_CLIENT_EMAIL;
  const privateKey = process.env.GOOGLE_SC_PRIVATE_KEY;
  const siteUrl = process.env.GOOGLE_SC_SITE_URL;

  if (!clientEmail || !privateKey || !siteUrl) {
    sendJson(req, res, 200, {
      configured: false,
      message:
        "Search Console-koppeling nog niet ingesteld. Voeg GOOGLE_SC_CLIENT_EMAIL, GOOGLE_SC_PRIVATE_KEY en GOOGLE_SC_SITE_URL toe in Vercel.",
      topQueries: [],
      updatedAt: new Date().toISOString(),
    }, 0);
    return;
  }

  try {
    const accessToken = await getAccessToken({
      clientEmail,
      privateKey,
      scope: "https://www.googleapis.com/auth/webmasters.readonly",
      varName: "GOOGLE_SC_PRIVATE_KEY",
    });

    const end = new Date();
    const start = new Date(end.getTime() - PERIOD_DAYS * 24 * 60 * 60 * 1000);
    const day = (d) => d.toISOString().slice(0, 10);

    const queryRes = await fetch(
      `https://searchconsole.googleapis.com/webmasters/v3/sites/${encodeURIComponent(siteUrl)}/searchAnalytics/query`,
      {
        method: "POST",
        headers: { Authorization: `Bearer ${accessToken}`, "Content-Type": "application/json" },
        body: JSON.stringify({ startDate: day(start), endDate: day(end), dimensions: ["query"], rowLimit: 25 }),
      }
    );
    const queryData = await queryRes.json().catch(() => ({}));
    if (!queryRes.ok) {
      throw new Error((queryData.error && queryData.error.message) || `Search Console-query mislukt (${queryRes.status})`);
    }

    const topQueries = (queryData.rows || []).map((row) => ({
      query: row.keys[0],
      clicks: row.clicks,
      impressions: row.impressions,
      ctr: Math.round(row.ctr * 1000) / 10, // percentage, 1 decimaal
      position: Math.round(row.position * 10) / 10,
    }));

    sendJson(req, res, 200, {
      configured: true,
      periodDays: PERIOD_DAYS,
      topQueries,
      updatedAt: new Date().toISOString(),
    }, CACHE_SECONDS);
  } catch (err) {
    sendJson(req, res, 200, {
      configured: true,
      error: err.message,
      topQueries: [],
      updatedAt: new Date().toISOString(),
    }, 0);
  }
};
