export const dynamic = "force-dynamic";
export async function GET() {
  return Response.json(
    {
      ok: false,
      error:
        "Legacy raw exports are retired. Use the validated predictions, archive and backtest APIs.",
    },
    { status: 410, headers: { "Cache-Control": "no-store" } },
  );
}
