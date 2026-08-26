// Afronding van de GitHub-login: wisselt de code om voor een token en geeft
// dat terug aan Sveltia CMS via postMessage (Decap-compatibel formaat).
module.exports = async (req, res) => {
  const clientId = process.env.GITHUB_CLIENT_ID;
  const clientSecret = process.env.GITHUB_CLIENT_SECRET;
  if (!clientId || !clientSecret) {
    res.statusCode = 500;
    res.end('GitHub OAuth-omgevingsvariabelen ontbreken.');
    return;
  }

  const url = new URL(req.url, `https://${req.headers.host}`);
  const code = url.searchParams.get('code');
  if (!code) {
    res.statusCode = 400;
    res.end('Geen code ontvangen van GitHub.');
    return;
  }

  let status = 'error';
  let content = { error: 'unknown' };
  try {
    const tokenRes = await fetch('https://github.com/login/oauth/access_token', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify({ client_id: clientId, client_secret: clientSecret, code }),
    });
    const data = await tokenRes.json();
    if (data && data.access_token) {
      status = 'success';
      content = { token: data.access_token, provider: 'github' };
    } else {
      content = { error: (data && data.error) || 'no_token' };
    }
  } catch (e) {
    content = { error: 'request_failed' };
  }

  const message = 'authorization:github:' + status + ':' + JSON.stringify(content);
  const html =
    '<!doctype html><html><head><meta charset="utf-8"></head><body><script>' +
    '(function(){' +
    'var message=' + JSON.stringify(message) + ';' +
    'function receive(e){window.opener&&window.opener.postMessage(message,e.origin);window.removeEventListener("message",receive,false);}' +
    'window.addEventListener("message",receive,false);' +
    'window.opener&&window.opener.postMessage("authorizing:github","*");' +
    '})();' +
    '</script><p>Inloggen afgerond, je kunt dit venster sluiten.</p></body></html>';

  res.setHeader('Content-Type', 'text/html; charset=utf-8');
  res.end(html);
};
