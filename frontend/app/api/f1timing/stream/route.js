export const dynamic = "force-dynamic";
export const runtime = "nodejs";

import { GET as getTiming } from "../route";

const encoder = new TextEncoder();

function sse(event, data) {
  return encoder.encode(`event: ${event}\ndata: ${JSON.stringify(data)}\n\n`);
}

function wait(ms, signal) {
  return new Promise((resolve) => {
    const timer = setTimeout(resolve, ms);
    signal?.addEventListener("abort", () => {
      clearTimeout(timer);
      resolve();
    }, { once: true });
  });
}

function timingRequestUrl(requestUrl) {
  const url = new URL(requestUrl);
  url.pathname = "/api/f1timing";
  url.searchParams.set("fast", "1");
  return url;
}

function payloadFingerprint(payload) {
  return JSON.stringify({
    source: payload?.source,
    state: payload?.session_state,
    session: payload?.normalized?.session,
    leaderboard: payload?.normalized?.leaderboard,
    raceControl: payload?.normalized?.raceControl?.slice?.(0, 5),
    weather: payload?.normalized?.weather,
    trackStatus: payload?.normalized?.trackStatus,
    lapCount: payload?.normalized?.lapCount,
  });
}

export async function GET(request) {
  const signal = request.signal;

  const stream = new ReadableStream({
    async start(controller) {
      let lastFingerprint = "";
      let closed = false;

      function close() {
        if (closed) return;
        closed = true;
        try { controller.close(); } catch {}
      }

      signal?.addEventListener("abort", close, { once: true });
      controller.enqueue(sse("ready", { ok: true, server_time: new Date().toISOString() }));

      while (!closed && !signal?.aborted) {
        try {
          const response = await getTiming(new Request(timingRequestUrl(request.url), { signal }));
          const payload = await response.json();
          const fingerprint = payloadFingerprint(payload);
          if (fingerprint !== lastFingerprint) {
            controller.enqueue(sse("message", payload));
            lastFingerprint = fingerprint;
          } else {
            controller.enqueue(sse("heartbeat", { server_time: new Date().toISOString(), session_state: payload?.session_state || "pending" }));
          }

          const delay = Math.max(1500, Math.min(10000, Number(payload?.refresh_after_ms || 5000)));
          await wait(delay, signal);
        } catch (error) {
          if (closed || signal?.aborted) break;
          controller.enqueue(sse("error", { message: "Live stream retrying", detail: String(error?.message || error) }));
          await wait(5000, signal);
        }
      }

      close();
    },
    cancel() {
      signal?.throwIfAborted?.();
    }
  });

  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream; charset=utf-8",
      "Cache-Control": "no-store, no-transform",
      "Connection": "keep-alive",
      "X-Accel-Buffering": "no",
    }
  });
}
