export default {
  async fetch(request) {
    const corsHeaders = {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "GET, HEAD, POST, OPTIONS",
      "Access-Control-Allow-Headers": "Range", 
      "Access-Control-Expose-Headers": "Content-Length, Content-Range",
    };

    // Preflight check (Browser ki inquiry)
    if (request.method === "OPTIONS") {
      return new Response(null, { headers: corsHeaders });
    }

    const url = new URL(request.url);
    const targetUrl = url.searchParams.get("url");

    if (!targetUrl) return new Response("URL parameter missing", { status: 400 });

    let target;
    try {
      target = new URL(targetUrl);
    } catch (e) {
      return new Response("Malformed URL", { status: 400 });
    }

    if (target.protocol !== "https:") {
      return new Response("Forbidden protocol", { status: 403 });
    }

    if (target.username || target.password) {
      return new Response("Forbidden credentials", { status: 403 });
    }

    const hostname = target.hostname;

    const isAllowedHost =
      hostname === "media.vibeaudio.com" ||
      hostname === "archive.org" ||
      hostname.endsWith(".archive.org") ||
      hostname.endsWith(".r2.cloudflarestorage.com");

    if (!isAllowedHost) {
      return new Response("Forbidden hostname", { status: 403 });
    }

    const allowedHeaders = [
      "range",
      "if-range",
      "if-none-match",
      "if-modified-since",
      "accept"
    ];

    const proxyHeaders = new Headers();
    for (const [key, value] of request.headers) {
      if (allowedHeaders.includes(key.toLowerCase())) {
        proxyHeaders.set(key, value);
      }
    }

    // Asli file fetch karo
    const response = await fetch(target.toString(), {
      headers: proxyHeaders, // Range headers pass karo seeking ke liye
      redirect: 'manual'
    });

    // Naya response banao headers ke sath
    return new Response(response.body, {
      status: response.status,
      statusText: response.statusText,
      headers: {
        ...Object.fromEntries(response.headers),
        ...corsHeaders
      }
    });
  }
};