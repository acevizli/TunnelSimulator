// Types come from the Python models via OpenAPI (`npm run gen:api`); never edit them by hand.
import type { components } from "./api-types";

export type Scenario = components["schemas"]["Scenario"];
export type Run = components["schemas"]["Run"];
export type EstimateTrack = components["schemas"]["EstimateTrack"];

export async function fetchScenarios(): Promise<Scenario[]> {
  const res = await fetch("/api/scenarios");
  if (!res.ok) throw new Error(`GET /api/scenarios: ${res.status}`);
  return res.json();
}

export async function computeRun(scenario: Scenario): Promise<Run> {
  const res = await fetch("/api/runs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(scenario),
  });
  if (!res.ok) throw new Error(`POST /api/runs: ${res.status}`);
  return res.json();
}
