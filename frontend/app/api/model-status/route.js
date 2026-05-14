export const dynamic = "force-dynamic";
export const runtime = "nodejs";

import { jsonResponse, loadModelStatus } from "../_lib/contracts";

export async function GET() {
  return jsonResponse(await loadModelStatus());
}
