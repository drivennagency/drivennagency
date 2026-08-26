// Start van de GitHub-login voor Sveltia CMS (stuurt door naar GitHub).
module.exports = (req, res) => {
  const clientId = process.env.GITHUB_CLIENT_ID;
  if (!clientId) {
    res.statusCode = 500;
    res.end('GITHUB_CLIENT_ID ontbreekt in de omgevingsvariabelen.');
    return;
  }
  const host = req.headers.host;
  const redirectUri = `https://${host}/api/callback`;
  const state = Math.random().toString(36).slice(2) + Math.random().toString(36).slice(2);
  const url =
    'https://github.com/login/oauth/authorize' +
    `?client_id=${encodeURIComponent(clientId)}` +
    `&redirect_uri=${encodeURIComponent(redirectUri)}` +
    '&scope=repo' +
    `&state=${encodeURIComponent(state)}`;
  res.writeHead(302, { Location: url });
  res.end();
};
