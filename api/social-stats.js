// Vercel serverless function: live Instagram- en Facebook-cijfers voor het Drivenn Agency dashboard.
// Vereiste environment variables (Vercel -> Settings -> Environment Variables):
//   META_PAGE_ACCESS_TOKEN  - Page Access Token (niet-verlopend, via System User)
//   META_IG_BUSINESS_ID     - Instagram Business Account ID (gekoppeld aan de Facebook-pagina)
//   META_PAGE_ID            - Facebook Pagina ID
//
// TikTok volgt later (eigen token/app), zodra het account bestaat.
// Let op: "reach7d" is om historische redenen zo genoemd, maar bevat het bereik van de
// meest recente dag zoals de Graph API die met period=day teruggeeft.

const { sendJson, handleMethod } = require("./_lib/google");

const GRAPH = "https://graph.facebook.com/v21.0";
const CACHE_SECONDS = 900;

async function graph(path, fields, token) {
  const url = `${GRAPH}/${path}?${fields}&access_token=${encodeURIComponent(token)}`;
  const res = await fetch(url);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error((data.error && data.error.message) || `Graph API fout (${res.status})`);
  return data;
}

function empty(extra) {
  return Object.assign({ instagram: null, facebook: null, tiktok: null, updatedAt: new Date().toISOString() }, extra);
}

module.exports = async function handler(req, res) {
  if (handleMethod(req, res)) return;

  const token = process.env.META_PAGE_ACCESS_TOKEN;
  const igId = process.env.META_IG_BUSINESS_ID;
  const pageId = process.env.META_PAGE_ID;

  if (!token || !igId || !pageId) {
    sendJson(req, res, 200, empty({
      configured: false,
      message: "Meta-koppeling nog niet ingesteld. Voeg META_PAGE_ACCESS_TOKEN, META_IG_BUSINESS_ID en META_PAGE_ID toe in Vercel.",
    }), 0);
    return;
  }

  try {
    const [igProfile, igInsights, pageProfile] = await Promise.all([
      graph(encodeURIComponent(igId), "fields=followers_count,media_count,username", token),
      graph(`${encodeURIComponent(igId)}/insights`, "metric=reach&period=day&metric_type=total_value", token).catch(() => null),
      graph(encodeURIComponent(pageId), "fields=fan_count,name", token),
    ]);

    const reach = igInsights && igInsights.data && igInsights.data[0] && igInsights.data[0].total_value
      ? igInsights.data[0].total_value.value
      : null;

    sendJson(req, res, 200, {
      configured: true,
      instagram: {
        username: igProfile.username,
        followers: igProfile.followers_count,
        posts: igProfile.media_count,
        reach7d: reach,
      },
      facebook: { name: pageProfile.name, likes: pageProfile.fan_count },
      tiktok: null,
      updatedAt: new Date().toISOString(),
    }, CACHE_SECONDS);
  } catch (err) {
    sendJson(req, res, 200, empty({ configured: true, error: err.message }), 0);
  }
};
