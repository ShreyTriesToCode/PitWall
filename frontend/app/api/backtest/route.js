export const dynamic = "force-dynamic";
export const runtime = "nodejs";

import { jsonResponse, loadBacktest } from "../_lib/contracts";

export async function GET() {
  return jsonResponse(await loadBacktest());
}
