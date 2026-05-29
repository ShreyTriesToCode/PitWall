import { readFile } from "node:fs/promises";
import path from "node:path";

const PROJECT_PARENT = path.resolve(/*turbopackIgnore: true*/ process.cwd(), "..");
const DATA_CACHE_DIR = path.resolve(PROJECT_PARENT, "data_cache");
const BRIEFINGS_DIR = path.resolve(PROJECT_PARENT, "briefings");
const DATA_BASE =
  process.env.NEXT_PUBLIC_F1_DATA_BASE_URL ||
  "https://raw.githubusercontent.com/ShreyTriesToCode/PitWall/main";
const GITHUB_RAW_DATA_FALLBACK = String(process.env.GITHUB_RAW_DATA_FALLBACK || process.env.NEXT_PUBLIC_GITHUB_RAW_DATA_FALLBACK || "true").toLowerCase() !== "false";
const USE_LAST_VALID_CONTRACT_ON_ERROR = String(process.env.USE_LAST_VALID_CONTRACT_ON_ERROR || "true").toLowerCase() !== "false";

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
    if (!GITHUB_RAW_DATA_FALLBACK) return fallback;
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
      prediction_trust_score: Math.max(0, Math.min(100, numeric(row.prediction_trust_score, row.confidence ?? 0))),
      prediction_trust_label: row.prediction_trust_label || row.trust_label || "Trust pending",
      model_disagreement_level: row.model_disagreement_level || "low",
      model_disagreement_reasons: asArray(row.model_disagreement_reasons || row.disagreement_flags),
      component_scores: asObject(row.component_scores),
      reason_tags: asArray(row.reason_tags),
      weakness_tags: asArray(row.weakness_tags),
      evidence_status: asObject(row.evidence_status),
      available_feature_groups: asArray(row.available_feature_groups || row.evidence_status?.available),
      missing_feature_groups: asArray(row.missing_feature_groups || row.evidence_status?.missing),
      missing_data_penalty_total: numeric(row.missing_data_penalty_total || row.evidence_status?.penalty_total, 0),
      stage_limitations: asArray(row.stage_limitations),
      source_warnings: asArray(row.source_warnings || row.source_notes?.warnings),
      stale_source_warnings: asArray(row.stale_source_warnings),
      missing_data_penalties: asObject(row.missing_data_penalties),
      data_completeness_score: numeric(row.data_completeness_score, numeric(row.trust_components?.data_completeness, null)),
      trust_components: asObject(row.trust_components),
      trust_explanation: row.trust_explanation || "",
      model_agreement_score: numeric(row.model_agreement_score, null),
      ai_explanation: asObject(row.ai_explanation),
      position_range: Array.isArray(row.position_range)
        ? row.position_range
        : [row.best_case_finish ?? row.finish_interval_low ?? row.rank, row.worst_case_finish ?? row.finish_interval_high ?? row.rank],
      points_probability: numeric(row.points_probability, numeric(row.top10_probability, null)),
      fastest_lap_probability: numeric(row.fastest_lap_probability, null),
      dnf_probability: numeric(row.dnf_probability, null),
      expected_strategy: asObject(row.expected_strategy),
      explanation: asObject(row.explanation),
      data_freshness: asObject(row.data_freshness),
      source_notes: asObject(row.source_notes),
      strategy_annotations: asArray(row.strategy_annotations),
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
    top_10: top10,
    full_grid: fullGrid.length ? fullGrid : top10,
    all_predictions: fullGrid.length ? fullGrid : top10,
    race_factors: asObject(payload.race_factors),
    warnings: asArray(payload.warnings),
    scenarios: asObject(payload.scenarios),
    strategy: asObject(payload.strategy),
    prediction_model: asObject(payload.prediction_model),
    source_health: asObject(payload.source_health || payload.source_status),
    source_status: asObject(payload.source_status || payload.source_health),
    race_intelligence_summary: asObject(payload.race_intelligence_summary),
    changed_since_last_run: asObject(payload.changed_since_last_run || payload.change_summary),
    change_summary: asObject(payload.change_summary || payload.changed_since_last_run),
    ai_features: asObject(payload.ai_features),
    source_conflicts: asArray(payload.source_conflicts),
    event_trust_score: numeric(payload.event_trust_score || payload.prediction_trust_score, null),
    event_trust_label: payload.event_trust_label || payload.prediction_trust_label || "",
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
    race_intelligence_summary: asObject(raw.race_intelligence_summary || latest?.race_intelligence_summary),
    changed_since_last_run: asObject(raw.changed_since_last_run || raw.what_changed_since_last_run || latest?.changed_since_last_run || latest?.change_summary),
    event_trust_score: numeric(raw.event_trust_score || latest?.event_trust_score || latest?.prediction_trust_score, null),
    event_trust_label: raw.event_trust_label || latest?.event_trust_label || latest?.prediction_trust_label || "",
    ai_features: asObject(raw.ai_features || latest?.ai_features),
    source_conflicts: asArray(raw.source_conflicts || latest?.source_conflicts),
  };
}

function recoverContractFromDebug(debug, base = {}) {
  const targets = asArray(debug?.payloads).map(normalizeDebugTarget).filter((target) => target?.top10?.length);
  const latest = normalizeLatest(targets.find((target) => target.target_type === "race") || targets[0]);
  if (!latest?.top10?.length) return null;
  const warning = "Recovered prediction contract from data_cache/latest-model-debug.json because frontend-contract.json was missing, blank, or invalid.";
  const warnings = [...asArray(latest.warnings), warning];
  return normalizeFrontendContract({
    ...asObject(base),
    schema_version: base?.schema_version || "recovered-from-debug",
    prediction_data_version: base?.prediction_data_version || latest.prediction_data_version || "debug-recovery",
    generated_at: base?.generated_at || debug?.generated_at || latest.generated || latest.generated_at || null,
    target_event: base?.target_event || latest.race_name || latest.title || latest.event?.title || null,
    prediction_stage: base?.prediction_stage || latest.prediction_stage || latest.stage || "pending",
    contract_recovered_from_debug: true,
    contract_recovery_warning: warning,
    latest: {
      ...latest,
      warnings,
      contract_recovered_from_debug: true,
      contract_recovery_warning: warning,
    },
    briefings: asArray(base?.briefings),
    archive: normalizeArchive(base?.archive),
  });
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
    top_10: normalizePredictionRows(payload.top_10?.length ? payload.top_10 : payload.top10?.length ? payload.top10 : fullGrid, { limit: 10 }),
    full_grid: fullGrid,
    all_predictions: fullGrid,
    race_factors: asObject(payload.race_factors),
    warnings: asArray(payload.warnings),
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
  const raw = await loadJson("data_cache/frontend-contract.json", fallback);
  let normalized = normalizeFrontendContract(raw);
  if (USE_LAST_VALID_CONTRACT_ON_ERROR && !normalized.latest?.top10?.length) {
    const debug = await loadJson("data_cache/latest-model-debug.json", { payloads: [] });
    const recovered = recoverContractFromDebug(debug, raw);
    if (recovered) normalized = recovered;
  }
  if (!normalized.latest?.top10?.length) {
    const previous = await loadJson("data_cache/frontend-contract.previous.json", fallback);
    const recoveredPrevious = normalizeFrontendContract({
      ...previous,
      contract_recovered_from_previous: true,
      latest: previous?.latest ? {
        ...previous.latest,
        contract_recovered_from_previous: true,
        warnings: [...asArray(previous.latest.warnings), "Recovered from frontend-contract.previous.json because the latest contract was unusable."],
      } : null,
    });
    if (recoveredPrevious.latest?.top10?.length) normalized = recoveredPrevious;
  }
  return normalized;
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
