export const dynamic = "force-dynamic";
export const runtime = "nodejs";

import { jsonResponse, loadArchive } from "../_lib/contracts";

export async function GET() {
  const archive = await loadArchive();
  return jsonResponse({ ok: Boolean(archive.archive?.length || archive.briefings?.length), ...archive });
}
