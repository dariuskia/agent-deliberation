import type { Config, DeliberationResult, RunSummary } from "./types";

export async function fetchRuns(): Promise<RunSummary[]> {
  const res = await fetch("/api/runs");
  return res.json();
}

export async function fetchRun(runId: string): Promise<DeliberationResult> {
  const res = await fetch(`/api/runs/${runId}`);
  return res.json();
}

export async function fetchConfig(): Promise<Config> {
  const res = await fetch("/api/config");
  return res.json();
}

export async function startDeliberation(
  question?: string,
  numRounds?: number,
): Promise<{ session_id: string; stream_url: string }> {
  const res = await fetch("/api/deliberate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, num_rounds: numRounds }),
  });
  return res.json();
}
