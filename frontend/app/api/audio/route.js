export const dynamic = "force-dynamic";
export const runtime = "nodejs";

function isAllowedAudioUrl(url) {
  try {
    const parsed = new URL(url);
    const host = parsed.hostname.toLowerCase();
    const path = parsed.pathname.toLowerCase();
    const trustedHost =
      host === "livetiming.formula1.com" ||
      host.endsWith(".formula1.com") ||
      host.endsWith(".formula1.com.s3.amazonaws.com") ||
      (host.endsWith(".cloudfront.net") && path.includes("teamradio"));
    const trustedPath =
      path.includes("/static/") ||
      path.includes("teamradio") ||
      path.includes("team-radio") ||
      path.endsWith(".mp3") ||
      path.endsWith(".aac") ||
      path.endsWith(".m4a") ||
      path.endsWith(".wav") ||
      path.endsWith(".ogg");
    return parsed.protocol === "https:" && trustedHost && trustedPath;
  } catch {
    return false;
  }
}

export async function GET(request) {
  const { searchParams } = new URL(request.url);
  const url = searchParams.get("url");

  if (!url || !isAllowedAudioUrl(url)) {
    return Response.json(
      { ok: false, error: "Invalid or unsupported audio URL." },
      { status: 400 }
    );
  }

  const headers = {};
  const range = request.headers.get("range");
  if (range) headers.Range = range;

  try {
    const res = await fetch(url, {
      headers: {
        ...headers,
        "User-Agent": "pitwall-audio-proxy/1.0"
      },
      cache: "no-store"
    });

    const outHeaders = new Headers();
    const contentType = res.headers.get("content-type") || "audio/mpeg";
    outHeaders.set("Content-Type", contentType);
    outHeaders.set("Cache-Control", "no-store");
    outHeaders.set("Accept-Ranges", "bytes");

    const contentLength = res.headers.get("content-length");
    const contentRange = res.headers.get("content-range");
    if (contentLength) outHeaders.set("Content-Length", contentLength);
    if (contentRange) outHeaders.set("Content-Range", contentRange);

    return new Response(res.body, {
      status: res.status,
      headers: outHeaders
    });
  } catch (error) {
    return Response.json(
      { ok: false, error: String(error?.message || error) },
      { status: 502 }
    );
  }
}
