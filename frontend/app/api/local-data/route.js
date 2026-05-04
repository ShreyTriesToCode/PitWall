export const dynamic = "force-dynamic";
export const runtime = "nodejs";

import { readFile } from "node:fs/promises";
import path from "node:path";

const PROJECT_PARENT = path.resolve(/*turbopackIgnore: true*/ process.cwd(), "..");
const BRIEFINGS_DIR = path.resolve(PROJECT_PARENT, "briefings");
const DATA_CACHE_DIR = path.resolve(PROJECT_PARENT, "data_cache");
const MODEL_STATUS_FILE = path.resolve(PROJECT_PARENT, "MODEL_STATUS.md");

function normalizeRequestPath(value) {
  const normalized = path.posix.normalize(String(value || "").replace(/^\/+/, ""));
  if (!normalized || normalized.startsWith("../") || normalized === ".." || path.isAbsolute(normalized)) {
    return null;
  }
  return normalized;
}

function isAllowedDataPath(value) {
  if (value === "MODEL_STATUS.md") return true;
  if (value === "data_cache/latest-model-debug.json") return true;
  if (value === "briefings/index.json" || value === "briefings/latest-run-status.md") return true;
  return value.startsWith("briefings/") && (value.endsWith(".md") || value.endsWith(".json"));
}

function resolveDataFile(value) {
  if (value === "MODEL_STATUS.md") return MODEL_STATUS_FILE;
  if (value === "data_cache/latest-model-debug.json") {
    return path.resolve(DATA_CACHE_DIR, "latest-model-debug.json");
  }
  if (value.startsWith("briefings/")) {
    const briefingsPath = path.posix.normalize(value.slice("briefings/".length));
    if (!briefingsPath || briefingsPath.startsWith("../") || briefingsPath === "..") return null;
    const filePath = path.resolve(BRIEFINGS_DIR, briefingsPath);
    return filePath.startsWith(BRIEFINGS_DIR + path.sep) ? filePath : null;
  }
  return null;
}

function contentType(value) {
  if (value.endsWith(".json")) return "application/json; charset=utf-8";
  if (value.endsWith(".md")) return "text/markdown; charset=utf-8";
  return "text/plain; charset=utf-8";
}

export async function GET(request) {
  const { searchParams } = new URL(request.url);
  const requestedPath = normalizeRequestPath(searchParams.get("path"));
  if (!requestedPath || !isAllowedDataPath(requestedPath)) {
    return Response.json({ ok: false, error: "Path is not available through local data fallback." }, { status: 404 });
  }

  const filePath = resolveDataFile(requestedPath);
  if (!filePath) return Response.json({ ok: false, error: "Path is outside local data roots." }, { status: 404 });

  try {
    const body = await readFile(/*turbopackIgnore: true*/ filePath, "utf8");
    return new Response(body, {
      headers: {
        "Cache-Control": "no-store",
        "Content-Type": contentType(requestedPath)
      }
    });
  } catch {
    return Response.json({ ok: false, error: "Local data file not found." }, { status: 404 });
  }
}
