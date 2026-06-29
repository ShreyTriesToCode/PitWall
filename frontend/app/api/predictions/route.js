export const dynamic = "force-dynamic";
export const runtime = "nodejs";

import { jsonResponse, loadPredictionsPayload } from "../_lib/contracts";

export async function GET() {
  return jsonResponse(await loadPredictionsPayload());
}
