import { loadBacktest, loadModelStatus, loadPredictionsPayload } from "../api/_lib/contracts";
import ModelCenterClient from "./ModelCenterClient";

export const revalidate = 300;

export default async function ModelCenterPage() {
  const [initialPredictions, initialStatus, initialBacktest] = await Promise.all([
    loadPredictionsPayload(),
    loadModelStatus(),
    loadBacktest(),
  ]);
  return (
    <ModelCenterClient
      initialPredictions={initialPredictions}
      initialStatus={initialStatus}
      initialBacktest={initialBacktest}
    />
  );
}
