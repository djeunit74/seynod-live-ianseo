// Compatibility endpoint. No hardcoded competition, club or athlete exceptions.
export default async request => {
  const source = new URL(request.url).searchParams.get('url');
  let url;
  try { url = new URL(source); } catch (_) { return new Response('URL IANSEO requise', {status: 400}); }
  if (url.protocol !== 'https:' || url.hostname !== 'www.ianseo.net' || url.port || url.username || url.password || !/^\/TourData\/\d{4}\/\d+\/[A-Z0-9]+\.php$/.test(url.pathname) || url.search) return new Response('URL IANSEO non autorisée', {status: 400});
  try {
    const response = await fetch(url, {redirect: 'manual', signal: AbortSignal.timeout(15000), headers: {'Cache-Control': 'no-cache'}});
    if (!response.ok) return new Response('Lecture IANSEO impossible', {status: 502});
    return new Response(await response.text(), {headers: {'content-type': 'text/html; charset=utf-8', 'cache-control': 'public, max-age=15', 'x-arclive-fetched-at': new Date().toISOString()}});
  } catch (_) { return new Response('Lecture IANSEO instable', {status: 502}); }
};
