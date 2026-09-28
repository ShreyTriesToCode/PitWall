import Link from "next/link";
import { AppShell } from "./components/PitWallComponents";
export default function NotFound() {
  return (
    <AppShell>
      <h1>Page not found</h1>
      <p>This address does not match a PitWall page.</p>
      <Link className="text-link" href="/">
        Return to race overview →
      </Link>
    </AppShell>
  );
}
