export const dynamic = "force-dynamic";
export const runtime = "nodejs";

import { jsonResponse, loadFrontendContract } from "../_lib/contracts";

export async function GET() {
  const contract = await loadFrontendContract();
  const health = contract.latest?.source_health || contract.latest?.source_status || contract.source_health || { status: "Missing", sources: [] };
  return jsonResponse({
    ok: Boolean(health.sources?.length || health.status),
    generated_at: contract.generated_at || health.generated_at,
    fallback_reason: contract.latest?.live_fallback_reason || health.fallback_reason || "",
    ...health
  });
}
