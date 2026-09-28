export const dynamic = "force-dynamic";
import { jsonResponse, loadPredictionsPayload } from "../_lib/contracts";
export async function GET() {
  const data = await loadPredictionsPayload();
  return jsonResponse({
    ok: true,
    sources: data.sources,
    warnings: data.warnings,
  });
}
