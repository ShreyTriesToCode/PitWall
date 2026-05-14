export const dynamic = "force-dynamic";
export const runtime = "nodejs";

import { jsonResponse, loadFrontendContract, loadGeneratedTargets } from "../_lib/contracts";

export async function GET() {
  const contract = await loadFrontendContract();
  const generated = await loadGeneratedTargets();
  const hasLatest = Boolean(contract.latest?.top10?.length);
  return jsonResponse({
    ok: hasLatest,
    error: hasLatest ? "" : "No generated prediction contract is available yet.",
    latest: contract.latest,
    top10: contract.latest?.top10 || [],
    full_grid: contract.latest?.full_grid || contract.latest?.all_predictions || contract.latest?.top10 || [],
    all_predictions: contract.latest?.all_predictions || contract.latest?.full_grid || contract.latest?.top10 || [],
    scenarios: contract.latest?.scenarios || {},
    strategy: contract.latest?.strategy || {},
    generated_targets: generated.targets,
    selected_targets: generated.selected_targets,
    output_mode: generated.output_mode,
    archive: contract.archive || [],
    schema_version: contract.schema_version,
    prediction_data_version: contract.prediction_data_version,
  });
}
