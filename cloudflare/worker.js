// Optional free Cloudflare entry point. Python runs on Render Free.
export default {
  async fetch(request, env) {
    let origin;
    try {
      origin = new URL(env.RENDER_ORIGIN);
      if (origin.protocol !== 'https:' || !origin.hostname.endsWith('.onrender.com') || origin.username || origin.password || origin.port) throw new Error('Invalid origin');
    } catch {
      return new Response('Blackbox setup is not complete. Please try again later.', {status: 503, headers: {'Cache-Control': 'no-store'}});
    }
    const incoming = new URL(request.url);
    const target = new URL(origin.origin);
    target.pathname = incoming.pathname;
    target.search = incoming.search;
    // Preserve method, cookies and body; never use the incoming Host as origin.
    const upstream = new Request(target, request);
    upstream.headers.delete('host');
    const response = await fetch(upstream, {redirect: 'manual'});
    const result = new Response(response.body, response);
    result.headers.set('Cache-Control', 'no-store');
    return result;
  }
};
