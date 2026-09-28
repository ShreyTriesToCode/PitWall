export const dynamic = "force-dynamic";
export const runtime = "nodejs";
const MAX_BYTES = 12_000_000;

export async function GET(request) {
  let url;
  try {
    url = new URL(new URL(request.url).searchParams.get("url"));
    if (
      url.protocol !== "https:" ||
      url.hostname !== "livetiming.formula1.com" ||
      url.port ||
      url.username ||
      url.password ||
      !/^\/static\/.+\/TeamRadio\/.+\.(mp3|aac|m4a|wav|ogg)$/i.test(
        url.pathname,
      )
    )
      throw new Error("Invalid audio path");
  } catch {
    return Response.json(
      { ok: false, error: "Invalid or unsupported audio URL." },
      { status: 400 },
    );
  }
  const range = request.headers.get("range");
  if (range && !/^bytes=\d*-\d*$/.test(range))
    return Response.json(
      { ok: false, error: "Invalid range." },
      { status: 400 },
    );
  try {
    const response = await fetch(url, {
      headers: range ? { Range: range } : {},
      redirect: "error",
      signal: AbortSignal.timeout(15000),
      cache: "no-store",
    });
    if (!response.ok)
      return Response.json(
        { ok: false, error: "Audio unavailable from source." },
        { status: 502 },
      );
    const length = Number(response.headers.get("content-length"));
    if (length > MAX_BYTES) throw new Error("Audio exceeds limit");
    const type = response.headers.get("content-type") || "";
    if (
      !type.startsWith("audio/") &&
      !type.startsWith("application/octet-stream")
    )
      throw new Error("Invalid audio type");
    const reader = response.body.getReader();
    const chunks = [];
    let size = 0;
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      size += value.length;
      if (size > MAX_BYTES) {
        await reader.cancel();
        throw new Error("Audio exceeds limit");
      }
      chunks.push(value);
    }
    const body = new Uint8Array(size);
    let offset = 0;
    for (const chunk of chunks) {
      body.set(chunk, offset);
      offset += chunk.length;
    }
    const headers = {
      "Content-Type": type,
      "Cache-Control": "private, max-age=3600",
      "X-Content-Type-Options": "nosniff",
      "Content-Length": String(size),
      "Accept-Ranges": "bytes",
    };
    if (response.headers.get("content-range"))
      headers["Content-Range"] = response.headers.get("content-range");
    return new Response(body, { status: response.status, headers });
  } catch (error) {
    console.warn("PitWall audio source failed:", error.name);
    return Response.json(
      { ok: false, error: "Audio could not be retrieved." },
      { status: 502 },
    );
  }
}
