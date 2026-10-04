// Cloudflare Worker: public IANSEO HTML proxy and authenticated GitHub dispatch.
const ACTIONS = {
  find_next: 'find-next-competition.yml', update_live: 'update-live.yml',
  reset_live: 'reset-live.yml', start_competition: 'start-competition.yml',
  save_admin_state: 'save-admin-state.yml'
};
const MAX_BODY = 250000;
function json(data, status = 200) {
  return new Response(JSON.stringify(data), {status, headers: {'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store'}});
}
function allowedSource(raw) {
  try {
    const u = new URL(raw);
    if (u.protocol !== 'https:' || u.hostname !== 'www.ianseo.net' || u.port || u.username || u.password) return false;
    if (!/^\/(?:TourList\.php|Details\.php|TourData\/\d{4}\/\d+\/[A-Z0-9]+\.php)$/.test(u.pathname)) return false;
    return [...u.searchParams.keys()].every(k => ['Year', 'countryid', 'toId', 'lang'].includes(k));
  } catch (_) { return false; }
}
async function authorized(request, env) {
  if (!env.ADMIN_TOKEN) return false;
  const actual = request.headers.get('Authorization') || '';
  const hash = async s => new Uint8Array(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(s)));
  const [a, b] = await Promise.all([hash(actual), hash(`Bearer ${env.ADMIN_TOKEN}`)]);
  let difference = 0;
  for (let i = 0; i < a.length; i++) difference |= a[i] ^ b[i];
  return difference === 0;
}
async function proxy(request, url, env) {
  const source = url.searchParams.get('url') || '';
  if (!allowedSource(source)) return json({error: 'Unsupported IANSEO URL'}, 400);
  const key = new Request(`${url.origin}/ianseo?url=${encodeURIComponent(source)}`);
  const cache = globalThis.caches?.default;
  const cached = cache && await cache.match(key);
  if (cached) return cached;
  try {
    const upstream = await fetch(source, {redirect: 'manual', signal: AbortSignal.timeout(15000), headers: {'User-Agent': 'ArcLive/1.0 (public competition viewer)', 'Accept': 'text/html', 'Cache-Control': 'no-cache'}});
    if (!upstream.ok) return json({error: `IANSEO HTTP ${upstream.status}`}, 502);
    const body = await upstream.text();
    if (/file not found\./i.test(body)) return json({error: 'IANSEO page not published'}, 404);
    if (body.length > 2000000) return json({error: 'IANSEO response too large'}, 502);
    const response = new Response(body, {headers: {
      'content-type': 'text/html; charset=utf-8', 'cache-control': 'public, max-age=15',
      'x-arclive-fetched-at': new Date().toISOString(), 'x-content-type-options': 'nosniff'
    }});
    if (cache) await cache.put(key, response.clone());
    return response;
  } catch (_) { return json({error: 'IANSEO temporarily unavailable'}, 502); }
}
export default {
  async fetch(request, env) {
    const origin = request.headers.get('Origin');
    const allowed = (env.ALLOWED_ORIGINS || 'https://djeunit74.github.io').split(',').map(s => s.trim());
    if (origin && !allowed.includes(origin)) return json({error: 'Origin not allowed'}, 403);
    const wrap = response => {
      const headers = new Headers(response.headers);
      if (origin) headers.set('Access-Control-Allow-Origin', origin);
      headers.set('Vary', 'Origin');
      headers.set('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
      headers.set('Access-Control-Allow-Headers', 'Content-Type, Authorization');
      headers.set('Access-Control-Expose-Headers', 'X-ArcLive-Fetched-At');
      return new Response(response.body, {status: response.status, headers});
    };
    const url = new URL(request.url);
    if (request.method === 'OPTIONS') return wrap(new Response(null, {status: 204}));
    if (request.method === 'GET' && url.pathname === '/ianseo') return wrap(await proxy(request, url, env));
    if (request.method !== 'POST') return wrap(json({error: 'Method not allowed'}, 405));
    if (!await authorized(request, env)) return wrap(json({error: 'Administrator authentication required'}, 401));
    if (url.pathname === '/auth') return wrap(json({ok: true}));
    if (url.pathname !== '/' && url.pathname !== '/dispatch') return wrap(json({error: 'Not found'}, 404));
    if (!env.GITHUB_OWNER || !env.GITHUB_REPO || !env.GITHUB_TOKEN) return wrap(json({error: 'GitHub bridge not configured'}, 503));
    const raw = await request.text();
    if (raw.length > MAX_BODY) return wrap(json({error: 'Payload too large'}, 413));
    let body;
    try { body = JSON.parse(raw); } catch (_) { return wrap(json({error: 'Invalid JSON'}, 400)); }
    const workflowFile = Object.hasOwn(ACTIONS, body.action) ? ACTIONS[body.action] : null;
    if (!workflowFile) return wrap(json({error: 'Unsupported action'}, 400));
    const inputs = {};
    if (['find_next', 'start_competition', 'update_live'].includes(body.action) && body.club_keywords) {
      if (typeof body.club_keywords !== 'string' || body.club_keywords.length > 500) return wrap(json({error: 'Invalid clubs'}, 400));
      inputs.club_keywords = body.club_keywords;
    }
    if (['find_next', 'start_competition'].includes(body.action) && body.country) {
      if (!/^[A-Z]{3}$/.test(body.country)) return wrap(json({error: 'Invalid country'}, 400));
      inputs.country = body.country;
    }
    if (body.action === 'save_admin_state') {
      if (typeof body.state_b64 !== 'string' || !/^[A-Za-z0-9_-]+$/.test(body.state_b64)) return wrap(json({error: 'Invalid shared state'}, 400));
      inputs.state_b64 = body.state_b64;
    }
    try {
      const ghRes = await fetch(`https://api.github.com/repos/${env.GITHUB_OWNER}/${env.GITHUB_REPO}/actions/workflows/${workflowFile}/dispatches`, {
        method: 'POST', headers: {'Authorization': `Bearer ${env.GITHUB_TOKEN}`, 'Accept': 'application/vnd.github+json', 'Content-Type': 'application/json', 'User-Agent': 'arclive-admin-bridge'},
        body: JSON.stringify({ref: env.GITHUB_REF || 'main', inputs})
      });
      return wrap(ghRes.ok ? json({ok: true, workflow: workflowFile}) : json({error: `GitHub dispatch failed (${ghRes.status})`}, 502));
    } catch (_) { return wrap(json({error: 'GitHub temporarily unavailable'}, 502)); }
  }
};
