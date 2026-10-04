// Vercel serverless function: live Instagram & Facebook cijfers voor het Drivenn Agency dashboard.
// Vereiste environment variables (Vercel -> Settings -> Environment Variables):
//   META_PAGE_ACCESS_TOKEN  - Page Access Token (niet-verlopend, via System User)
//   META_IG_BUSINESS_ID     - Instagram Business Account ID (gekoppeld aan de Facebook-pagina)
//   META_PAGE_ID            - Facebook Pagina ID
//
// TikTok volgt later (eigen token/app), zodra het account bestaat.

const GRAPH_VERSION = "v21.0";

async function fetchJson(url) {
  const res = await fetch(url);
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data?.error?.message || `Graph API fout (${res.status})`);
  }
  return data;
}

module.exports = async function handler(req, res) {
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "GET, OPTIONS");
  if (req.method === "OPTIONS") {
    res.status(204).end();
    return;
  }

  const token = process.env.META_PAGE_ACCESS_TOKEN;
  const igId = process.env.META_IG_BUSINESS_ID;
  const pageId = process.env.META_PAGE_ID;

  if (!token || !igId || !pageId) {
    res.status(200).json({
      configured: false,
      message: "Meta-koppeling nog niet ingesteld. Voeg META_PAGE_ACCESS_TOKEN, META_IG_BUSINESS_ID en META_PAGE_ID toe in Vercel.",
      instagram: null,
      facebook: null,
      tiktok: null,
      updatedAt: new Date().toISOString(),
    });
    return;
  }

  try {
    const [igProfile, igInsights, pageProfile] = await Promise.all([
      fetchJson(
        `https://graph.facebook.com/${GRAPH_VERSION}/${igId}?fields=followers_count,media_count,username&access_token=${token}`
      ),
      fetchJson(
        `https://graph.facebook.com/${GRAPH_VERSION}/${igId}/insights?metric=reach&period=day&metric_type=total_value&access_token=${token}`
      ).catch(() => null),
      fetchJson(
        `https://graph.facebook.com/${GRAPH_VERSION}/${pageId}?fields=fan_count,name&access_token=${token}`
      ),
    ]);

    const reachValue =
      igInsights?.data?.[0]?.total_value?.value ?? null;

    res.status(200).json({
      configured: true,
      instagram: {
        username: igProfile.username,
        followers: igProfile.followers_count,
        posts: igProfile.media_count,
        reach7d: reachValue,
      },
      facebook: {
        name: pageProfile.name,
        likes: pageProfile.fan_count,
      },
      tiktok: null,
      updatedAt: new Date().toISOString(),
    });
  } catch (err) {
    res.status(200).json({
      configured: true,
      error: err.message,
      instagram: null,
      facebook: null,
      tiktok: null,
      updatedAt: new Date().toISOString(),
    });
  }
}
