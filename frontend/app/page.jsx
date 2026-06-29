import { loadPredictionsPayload } from "./api/_lib/contracts";
import HomeClient from "./HomeClient";

export const revalidate = 300;

export default async function HomePage() {
  const initialData = await loadPredictionsPayload();
  return <HomeClient initialData={initialData} />;
}
