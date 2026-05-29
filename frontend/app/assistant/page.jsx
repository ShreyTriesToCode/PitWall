"use client";

import { useMemo, useState } from "react";
import { AppShell, EmptyState, InlineNotice, LoadingSkeleton, PageHeader, SearchBox, SectionTitle, usePitWallData } from "../components/PitWallComponents";

export default function AssistantPage() {
  const predictions = usePitWallData("/api/predictions");
  const model = usePitWallData("/api/model-status");
  const archive = usePitWallData("/api/archive");
  const [query, setQuery] = useState("");
  const answer = useMemo(() => answerFromLocalSources(query, predictions.data, model.data, archive.data), [query, predictions.data, model.data, archive.data]);
  return (
    <AppShell active="/assistant">
      <PageHeader eyebrow="Local Assistant" title="PitWall Assistant" description="A disabled-by-default, no-paid-API assistant surface. It answers only from committed PitWall JSON and generated docs." />
      {(predictions.loading || model.loading || archive.loading) && <LoadingSkeleton />}
      <InlineNotice title="Free deterministic mode" body="This page does not browse, call paid APIs, or alter rankings. If the local contract does not support an answer, it says so." tone="info" />
      <section className="panel reveal">
        <SectionTitle title="Ask Local PitWall Data" />
        <SearchBox value={query} onChange={setQuery} placeholder="Ask about trust, sources, model status, or archive" />
        {query ? <p className="panel-note">{answer}</p> : <EmptyState title="Ask a local-data question" body="Try: source warnings, model version, top prediction, trust score, or archive corrections." />}
      </section>
    </AppShell>
  );
}

function answerFromLocalSources(query, predictions, model, archive) {
  const text = String(query || "").toLowerCase();
  if (!text.trim()) return "";
  const latest = predictions?.latest || {};
  if (text.includes("top") || text.includes("winner") || text.includes("prediction")) {
    const top = latest.top10?.[0];
    return top ? `Current top PitWall row is ${top.name} for ${top.team}, ranked P${top.rank}. Source: data_cache/frontend-contract.json latest.top10.` : "Not enough data in local PitWall sources.";
  }
  if (text.includes("trust")) {
    return latest.prediction_trust_score || predictions?.event_trust_score
      ? `Event trust is ${predictions?.event_trust_score ?? latest.prediction_trust_score}. Source: frontend contract event trust fields.`
      : "Not enough data in local PitWall sources.";
  }
  if (text.includes("source") || text.includes("warning")) {
    const conflicts = predictions?.source_conflicts || latest.source_conflicts || [];
    return conflicts.length ? `${conflicts.length} source conflicts are reported. First: ${conflicts[0].reason}` : "No source conflicts are reported in the current local contract.";
  }
  if (text.includes("model")) {
    return model?.model_version ? `Model version is ${model.model_version}. Source: data_cache/model-status.json.` : "Not enough data in local PitWall sources.";
  }
  if (text.includes("archive") || text.includes("correction")) {
    const count = archive?.archive?.length ?? 0;
    return count ? `Archive contains ${count} briefing rows. Source: briefings/index.json via /api/archive.` : "Not enough data in local PitWall sources.";
  }
  return "Not enough data in local PitWall sources.";
}
