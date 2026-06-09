export const dynamic = "force-dynamic";
export const runtime = "nodejs";

import { jsonResponse, loadFrontendContract, loadGeneratedTargets } from "../_lib/contracts";

function currentTargetOnly(target, latest) {
  if (!target || !latest) return false;
  const latestRaceId = latest.race_id || latest.prediction_id?.split("-race-")?.[0] || "";
  const targetRaceId = target.race_id || target.prediction_id?.split("-race-")?.[0] || "";
  if (latestRaceId && targetRaceId && latestRaceId !== targetRaceId) return false;
  if (latest.season && target.season && Number(latest.season) !== Number(target.season)) return false;
  if (latest.round && target.round && Number(latest.round) !== Number(target.round)) return false;
  return true;
}

export async function GET() {
  const contract = await loadFrontendContract();
  const generated = await loadGeneratedTargets();
  const hasLatest = Boolean(contract.latest?.top10?.length);
  const generatedTargets = [
    contract.latest?.target_type ? {
      ...contract.latest,
      target_type: contract.latest.target_type,
      top10: contract.latest.top10 || [],
      full_grid: contract.latest.full_grid || contract.latest.all_predictions || contract.latest.top10 || [],
      all_predictions: contract.latest.all_predictions || contract.latest.full_grid || contract.latest.top10 || [],
    } : null,
    ...(generated.targets || []).filter((target) => currentTargetOnly(target, contract.latest)),
  ].filter(Boolean);
  return jsonResponse({
    ok: hasLatest,
    error: hasLatest ? "" : "No generated prediction contract is available yet.",
    latest: contract.latest,
    top10: contract.latest?.top10 || [],
    top_10: contract.latest?.top_10 || contract.latest?.top10 || [],
    full_grid: contract.latest?.full_grid || contract.latest?.all_predictions || contract.latest?.top10 || [],
    all_predictions: contract.latest?.all_predictions || contract.latest?.full_grid || contract.latest?.top10 || [],
    race_factors: contract.latest?.race_factors || {},
    race_intelligence_summary: contract.race_intelligence_summary || contract.latest?.race_intelligence_summary || {},
    model_comparison: contract.model_comparison || contract.latest?.model_comparison || {},
    actual_result_comparison: contract.actual_result_comparison || contract.latest?.actual_result_comparison || {},
    changed_since_last_run: contract.changed_since_last_run || contract.latest?.changed_since_last_run || contract.latest?.change_summary || {},
    event_trust_score: contract.event_trust_score ?? contract.latest?.event_trust_score ?? contract.latest?.prediction_trust_score,
    event_trust_label: contract.event_trust_label || contract.latest?.event_trust_label || contract.latest?.prediction_trust_label || "",
    ai_features: contract.ai_features || contract.latest?.ai_features || {},
    warnings: contract.latest?.warnings || [],
    scenarios: contract.latest?.scenarios || {},
    strategy: contract.latest?.strategy || {},
    generated_targets: generatedTargets,
    selected_targets: generated.selected_targets,
    output_mode: generated.output_mode,
    archive: contract.archive || [],
    contract_recovered_from_debug: Boolean(contract.contract_recovered_from_debug || contract.latest?.contract_recovered_from_debug),
    contract_recovered_from_previous: Boolean(contract.contract_recovered_from_previous || contract.latest?.contract_recovered_from_previous),
    contract_recovery_warning: contract.contract_recovery_warning || contract.latest?.contract_recovery_warning || "",
    schema_version: contract.schema_version,
    prediction_data_version: contract.prediction_data_version,
    season: contract.season,
    target_event: contract.target_event,
    prediction_stage: contract.prediction_stage,
    previous_prediction_stage: contract.previous_prediction_stage,
    session_timeline: contract.session_timeline || [],
    last_ingested_session: contract.last_ingested_session,
    next_session_to_ingest: contract.next_session_to_ingest,
    pending_session_checks: contract.pending_session_checks || [],
    session_data_delay_status: contract.session_data_delay_status,
    session_official_status: contract.session_official_status,
    effective_model_weights: contract.effective_model_weights || {},
    source_registry: contract.source_registry,
    source_health: contract.source_health,
    source_conflicts: contract.source_conflicts || [],
    model_limitations: contract.model_limitations || [],
    live_timing_status: contract.live_timing_status,
    timing_mode: contract.timing_mode,
    timing_source: contract.timing_source,
    timing_last_updated_at: contract.timing_last_updated_at,
    timing_freshness_seconds: contract.timing_freshness_seconds,
    is_genuinely_live: contract.is_genuinely_live,
    live_fallback_reason: contract.live_fallback_reason,
    fia_documents_enabled: contract.fia_documents_enabled,
    fia_season_url: contract.fia_season_url,
    fia_source_discovery_status: contract.fia_source_discovery_status,
    fia_documents_available: contract.fia_documents_available,
    fia_latest_document: contract.fia_latest_document,
    fia_document_count: contract.fia_document_count,
    fia_documents_by_type: contract.fia_documents_by_type,
    fia_session_timetable: contract.fia_session_timetable,
    fia_upgrade_summary: contract.fia_upgrade_summary,
    fia_pu_summary: contract.fia_pu_summary,
    fia_infringement_summary: contract.fia_infringement_summary,
    latest_fia_ingested_at: contract.latest_fia_ingested_at,
    fia_parse_errors: contract.fia_parse_errors,
    fia_cache_hits: contract.fia_cache_hits,
    fia_cache_misses: contract.fia_cache_misses,
  });
}
