export const dynamic = "force-dynamic";
export const runtime = "nodejs";
import { GET as getTiming } from "../route";
const encoder = new TextEncoder();
function event(name, data) {
  return encoder.encode(`event: ${name}\ndata: ${JSON.stringify(data)}\n\n`);
}
function wait(ms, signal) {
  return new Promise((resolve) => {
    const done = () => {
      clearTimeout(timer);
      signal.removeEventListener("abort", done);
      resolve();
    };
    const timer = setTimeout(done, ms);
    signal.addEventListener("abort", done, { once: true });
    if (signal.aborted) done();
  });
}
export async function GET(request) {
  const lifecycle = new AbortController();
  const abort = () => lifecycle.abort();
  request.signal.addEventListener("abort", abort, { once: true });
  if (request.signal.aborted) abort();
  const stream = new ReadableStream({
    async start(controller) {
      let fingerprint = "";
      const started = Date.now();
      try {
        controller.enqueue(
          event("ready", { server_time: new Date().toISOString() }),
        );
        while (!lifecycle.signal.aborted && Date.now() - started < 55_000) {
          try {
            const url = new URL(request.url);
            url.pathname = "/api/f1timing";
            url.searchParams.set("fast", "1");
            const response = await getTiming(
              new Request(url, { signal: lifecycle.signal }),
            );
            const payload = await response.json();
            if (lifecycle.signal.aborted) break;
            const next = JSON.stringify({
              state: payload.session_state,
              mode: payload.timing_mode,
              packet: payload.source_packet_at,
              data: payload.normalized,
            });
            if (next !== fingerprint) {
              controller.enqueue(event("message", payload));
              fingerprint = next;
            } else
              controller.enqueue(
                event("heartbeat", { server_time: new Date().toISOString() }),
              );
            await wait(
              Math.max(
                5000,
                Math.min(15000, Number(payload.refresh_after_ms) || 10000),
              ),
              lifecycle.signal,
            );
          } catch (error) {
            if (lifecycle.signal.aborted) break;
            console.warn("PitWall timing stream failed:", error.name);
            controller.enqueue(
              event("error", {
                message: "Timing temporarily unavailable; retrying.",
              }),
            );
            await wait(5000, lifecycle.signal);
          }
        }
      } finally {
        request.signal.removeEventListener("abort", abort);
        if (!lifecycle.signal.aborted) controller.close();
      }
    },
    cancel() {
      lifecycle.abort();
    },
  });
  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream; charset=utf-8",
      "Cache-Control": "no-store, no-transform",
      "X-Accel-Buffering": "no",
    },
  });
}
