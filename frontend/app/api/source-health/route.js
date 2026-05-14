export const dynamic = "force-dynamic";
export const runtime = "nodejs";

import { jsonResponse, loadFrontendContract } from "../_lib/contracts";

export async function GET() {
  const contract = await loadFrontendContract();
  const health = contract.latest?.source_health || contract.latest?.source_status || { status: "Missing", sources: [] };
  return jsonResponse({ ok: Boolean(health.sources?.length), ...health });
}
