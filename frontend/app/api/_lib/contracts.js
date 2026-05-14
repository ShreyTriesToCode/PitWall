import { readFile } from "node:fs/promises";
import path from "node:path";

const PROJECT_PARENT = path.resolve(/*turbopackIgnore: true*/ process.cwd(), "..");
const DATA_CACHE_DIR = path.resolve(PROJECT_PARENT, "data_cache");
const BRIEFINGS_DIR = path.resolve(PROJECT_PARENT, "briefings");
const DATA_BASE =
  process.env.NEXT_PUBLIC_F1_DATA_BASE_URL ||
  "https://raw.githubusercontent.com/ShreyTriesToCode/PitWall/main";

async function readJson(filePath) {
  const text = await readFile(/*turbopackIgnore: true*/ filePath, "utf8");
  return JSON.parse(text);
}

async function fetchRemoteJson(relativePath) {
  const res = await fetch(`${DATA_BASE}/${relativePath}?v=${Date.now()}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Remote ${relativePath} HTTP ${res.status}`);
  return res.json();
}

async function loadJson(relativePath, fallback) {
  const localPath = relativePath.startsWith("briefings/")
    ? path.resolve(BRIEFINGS_DIR, relativePath.slice("briefings/".length))
    : path.resolve(DATA_CACHE_DIR, relativePath.replace(/^data_cache\//, ""));
  try {
    return await readJson(localPath);
  } catch {
    try {
      return await fetchRemoteJson(relativePath);
    } catch {
      return fallback;
    }
  }
}

function asArray(value) {
  return Array.isArray(value) ? value : [];
}

function asObject(value) {
  return value && typeof value === "object" && !Array.isArray(value) ? value : {};
}

function numeric(value, fallback = null) {
  const number = Number(value);
  return Number.isFinite(number) ? number : fallback;
}

function normalizePredictionRows(rows, options = {}) {
  const limit = options.limit === undefined ? 10 : options.limit;
  const seen = new Set();
  const normalized = asArray(rows).map((item, index) => {
    const row = asObject(item);
    const driverId = String(row.driver_id || row.name || `driver-${index + 1}`).trim();
    return {
      ...row,
      driver_id: driverId,
      name: row.name || driverId,
      team: row.team || "Unknown team",
      rank: numeric(row.rank, index + 1),
      previous_rank: numeric(row.previous_rank, row.rank ?? index + 1),
      rank_delta: numeric(row.rank_delta, 0),
      score: numeric(row.score, 0),
      confidence: Math.max(0, Math.min(100, numeric(row.confidence, 0))),
      component_scores: asObject(row.component_scores),
      reason_tags: asArray(row.reason_tags),
      weakness_tags: asArray(row.weakness_tags),
      evidence_status: asObject(row.evidence_status),
      missing_data_penalties: asObject(row.missing_data_penalties),
    };
  }).filter((row) => {
    if (!row.driver_id || seen.has(row.driver_id)) return false;
    seen.add(row.driver_id);
    return true;
  }).sort((a, b) => Number(a.rank || 999) - Number(b.rank || 999));
  return limit ? normalized.slice(0, limit) : normalized;
}

function normalizeLatest(payload) {
  if (!payload || typeof payload !== "object") return null;
  const fullGrid = normalizePredictionRows(
    payload.full_grid || payload.all_predictions || payload.driver_predictions || payload.top10,
    { limit: null },
  );
  const top10 = normalizePredictionRows(payload.top10?.length ? payload.top10 : fullGrid, { limit: 10 });
  return {
    ...payload,
    top10,
    full_grid: fullGrid.length ? fullGrid : top10,
    all_predictions: fullGrid.length ? fullGrid : top10,
    scenarios: asObject(payload.scenarios),
    strategy: asObject(payload.strategy),
    prediction_model: asObject(payload.prediction_model),
    source_health: asObject(payload.source_health || payload.source_status),
    source_status: asObject(payload.source_status || payload.source_health),
    model_metrics: asObject(payload.model_metrics),
    correction_summary: asObject(payload.correction_summary),
  };
}

function normalizeArchive(rows) {
  return asArray(rows).map((row, index) => ({
    ...asObject(row),
    prediction_id: row?.prediction_id || row?.path || `archive-${index}`,
    title: row?.title || row?.race_name || "Untitled briefing",
    stage: row?.stage || row?.prediction_stage || "pending",
  }));
}

function normalizeFrontendContract(contract) {
  const raw = asObject(contract);
  const latest = normalizeLatest(raw.latest);
  return {
    ...raw,
    ok: Boolean(latest?.top10?.length),
    latest,
    briefings: asArray(raw.briefings),
    archive: normalizeArchive(raw.archive),
    schema_version: raw.schema_version || "unavailable",
    prediction_data_version: raw.prediction_data_version || latest?.prediction_data_version || null,
  };
}

function normalizeDebugTarget(payload) {
  if (!payload || !payload.target_type) return null;
  const fullGrid = normalizePredictionRows(
    payload.full_grid || payload.all_predictions || payload.driver_predictions || payload.top10,
    { limit: null },
  );
  return {
    target_type: payload.target_type,
    title: payload.title,
    event: payload.event,
    race: payload.race,
    top10: normalizePredictionRows(payload.top10?.length ? payload.top10 : fullGrid, { limit: 10 }),
    full_grid: fullGrid,
    all_predictions: fullGrid,
    scenarios: payload.prediction_model?.scenarios || {},
    strategy: payload.strategy || null,
    prediction_model: payload.prediction_model || {},
    generated: payload.generated_at || null,
    stage: payload.prediction_model?.prediction_stage || payload.stage || "pending",
    available: Boolean(payload.top10?.length),
  };
}

export async function loadFrontendContract() {
  const fallback = { briefings: [], latest: null, archive: [], schema_version: "unavailable" };
  return normalizeFrontendContract(await loadJson("data_cache/frontend-contract.json", fallback));
}

export async function loadGeneratedTargets() {
  const debug = await loadJson("data_cache/latest-model-debug.json", { payloads: [] });
  const targets = (debug.payloads || []).map(normalizeDebugTarget).filter(Boolean);
  return {
    targets,
    selected_targets: debug.selected_targets || [],
    output_mode: debug.output_mode || null,
  };
}

export async function loadModelStatus() {
  return loadJson("data_cache/model-status.json", {
    readiness_state: { status: "Unavailable" },
    metrics: {},
    source_health: { status: "Missing", sources: [] },
  });
}

export async function loadBacktest() {
  return loadJson("data_cache/backtest-history.json", { history: [] });
}

export async function loadArchive() {
  const contract = await loadFrontendContract();
  return { archive: contract.archive || [], briefings: contract.briefings || [] };
}

export function jsonResponse(payload) {
  return Response.json(payload, {
    headers: {
      "Cache-Control": "no-store",
    },
  });
}
