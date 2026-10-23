// Types come from the Python models via OpenAPI (`npm run gen:api`); never edit them by hand.
import type { components } from "./api-types";

export type Scenario = components["schemas"]["Scenario"];
export type Run = components["schemas"]["Run"];
export type MeasuredRun = components["schemas"]["MeasuredRun"];
export type EstimatorMetrics = components["schemas"]["EstimatorMetrics"];
export type EstimateTrack = components["schemas"]["EstimateTrack"];
export type SensorAssumption = components["schemas"]["SensorAssumption"];
export type PieceChoices = components["schemas"]["PieceChoices"];

export const fetchSensorAssumptions = (): Promise<SensorAssumption[]> => get("/api/sensor-assumptions");
export const fetchScenarios = (): Promise<Scenario[]> => get("/api/scenarios");
export const fetchPieceChoices = (): Promise<PieceChoices> => get("/api/scenario-pieces");
export const computeRun = (scenario: Scenario): Promise<MeasuredRun> => post("/api/runs", scenario);
export const saveScenario = (scenario: Scenario): Promise<Scenario> => post("/api/scenarios", scenario);

async function get<T>(url: string): Promise<T> {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`GET ${url}: ${await reason(res)}`);
  return res.json();
}

async function post<T>(url: string, body: unknown): Promise<T> {
  const res = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  if (!res.ok) throw new Error(await reason(res));
  return res.json();
}

// The server's own words: a rejected scenario says which field is wrong and why
async function reason(res: Response): Promise<string> {
  try {
    const { detail } = await res.json();
    if (typeof detail === "string") return detail;
    return detail.map((d: { loc: string[]; msg: string }) => `${d.loc.slice(1).join(" › ")}: ${d.msg}`).join("; ");
  } catch {
    return `${res.status} ${res.statusText}`;
  }
}
