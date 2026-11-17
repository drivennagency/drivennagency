// Start van de GitHub-login voor Sveltia CMS (stuurt door naar GitHub).
// Er wordt een willekeurige "state" meegegeven én in een kortlevend cookie bewaard;
// /api/callback accepteert de terugkeer van GitHub alleen als die twee overeenkomen (CSRF-bescherming).
const crypto = require("crypto");

const STATE_COOKIE = "drivenn_oauth_state";

module.exports = (req, res) => {
  const clientId = process.env.GITHUB_CLIENT_ID;
  if (!clientId) {
    res.statusCode = 500;
    res.setHeader("Content-Type", "text/plain; charset=utf-8");
    res.end("GITHUB_CLIENT_ID ontbreekt in de omgevingsvariabelen.");
    return;
  }

  const host = req.headers.host;
  const redirectUri = `https://${host}/api/callback`;
  const state = crypto.randomBytes(24).toString("hex");
  const url =
    "https://github.com/login/oauth/authorize" +
    `?client_id=${encodeURIComponent(clientId)}` +
    `&redirect_uri=${encodeURIComponent(redirectUri)}` +
    "&scope=repo" +
    `&state=${encodeURIComponent(state)}`;

  res.setHeader("Set-Cookie", `${STATE_COOKIE}=${state}; Path=/api; Max-Age=600; HttpOnly; Secure; SameSite=Lax`);
  res.setHeader("Cache-Control", "no-store");
  res.writeHead(302, { Location: url });
  res.end();
};

module.exports.STATE_COOKIE = STATE_COOKIE;
