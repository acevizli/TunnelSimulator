// PROTOTYPE (replay layout, throwaway): pieces every layout variant uses. Not production code.
import { useEffect, useMemo, useRef, useState } from "react";
import { fetchScenarios, fetchSensorAssumptions, type Run, type Scenario, type SensorAssumption } from "../api";
import { AXIS_COLORS, TRUTH_COLOR, bandColor, estimatorColor } from "../colors";
import type { Line } from "../TimePlot";

const OUTPUT_HZ = 10;
export const SPEEDS = [1, 5, 10, 25];

// Hand-typed here because the prototype endpoint isn't in the generated types
export type Metric = {
  name: string; unit: string; value: number | null; worse: "higher" | "lower";
  at: { t_s: number; s_m: number; phase: string } | null; note: string;
};
export type EstimatorMetrics = { estimator: string; metrics: Metric[] };

async function computeMeasuredRun(scenario: Scenario): Promise<{ run: Run; metrics: EstimatorMetrics[] }> {
  const res = await fetch("/api/prototype/runs", {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(scenario),
  });
  if (!res.ok) throw new Error(`POST /api/prototype/runs: ${res.status} ${await res.text()}`);
  return res.json();
}

// Everything a variant needs: scenarios, the current run and its metrics, playback.
export function useReplay() {
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [scenario, setScenario] = useState<Scenario | null>(null);
  const [run, setRun] = useState<Run | null>(null);
  const [metrics, setMetrics] = useState<EstimatorMetrics[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [computing, setComputing] = useState(false);
  const [frame, setFrame] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(10);

  useEffect(() => {
    fetchScenarios().then((list) => { setScenarios(list); setScenario(list[0]); }).catch((e) => setError(String(e)));
  }, []);

  useEffect(() => {
    if (!scenario) return;
    let latest = true;
    setPlaying(false);
    setComputing(true);
    setError(null);
    computeMeasuredRun(scenario)
      .then((r) => { if (latest) { setRun(r.run); setMetrics(r.metrics); setFrame(0); } })
      .catch((e) => latest && setError(String(e)))
      .finally(() => latest && setComputing(false));
    return () => { latest = false; };
  }, [scenario]);

  usePlayback(playing, speed, run, setFrame, () => setPlaying(false));

  const errorLines = useMemo<Line[]>(() => run ? [
    ...run.estimates.filter((e) => e.sigma_m.some((s) => s != null)).flatMap((e): Line[] => [
      { name: `${e.estimator} band`, y: e.sigma_m.map((s) => s == null ? null : -2 * s), color: bandColor(e.estimator), band: "lower" },
      { name: `${e.estimator} band (±2σ)`, y: e.sigma_m.map((s) => s == null ? null : 2 * s), color: bandColor(e.estimator), band: "upper" },
    ]),
    ...run.estimates.map((e) => ({ name: e.estimator, y: e.error_m, color: estimatorColor(e.estimator) })),
  ] : [], [run]);
  const speedLines = useMemo<Line[]>(() => run ? [
    { name: "ground truth", y: run.truth_v_mps.map((v) => v * 3.6), color: TRUTH_COLOR },
    ...run.estimates.map((e) => ({ name: e.estimator, y: e.v_mps.map((v) => v == null ? null : v * 3.6),
      color: estimatorColor(e.estimator), dash: "dot" as const })),
  ] : [], [run]);

  const seekT = (t: number) => run && setFrame(Math.max(0, Math.min(run.t_s.length - 1, Math.round((t - run.t_s[0]) * OUTPUT_HZ))));
  const setSeed = (seed: number) => { if (scenario && Number.isInteger(seed) && seed !== scenario.seed) setScenario({ ...scenario, seed }); };
  const newSeed = () => setSeed(Math.floor(Math.random() * 1_000_000));

  return { scenarios, scenario, setScenario, run, metrics, error, computing, frame, setFrame, playing, setPlaying,
    speed, setSpeed, seekT, setSeed, newSeed, errorLines, speedLines };
}
export type Replay = ReturnType<typeof useReplay>;

function usePlayback(playing: boolean, speed: number, run: Run | null,
  setFrame: (f: (prev: number) => number) => void, onEnd: () => void) {
  const last = useRef<number | null>(null);
  useEffect(() => {
    if (!playing || !run) return;
    let id = 0;
    let carry = 0;
    const tick = (now: number) => {
      if (last.current != null) {
        carry += ((now - last.current) / 1000) * speed * OUTPUT_HZ;
        const step = Math.floor(carry);
        carry -= step;
        setFrame((f) => {
          const next = Math.min(f + step, run.t_s.length - 1);
          if (next === run.t_s.length - 1) onEnd();
          return next;
        });
      }
      last.current = now;
      id = requestAnimationFrame(tick);
    };
    id = requestAnimationFrame(tick);
    return () => { cancelAnimationFrame(id); last.current = null; };
  }, [playing, speed, run]);
}

// --- Scenario picker + seed -------------------------------------------------------------

export function ScenarioPicker({ r }: { r: Replay }) {
  const { scenarios, scenario } = r;
  if (!scenario) return null;
  const index = scenarios.findIndex((s) => s.name === scenario.name);
  return (
    <div className="p-picker">
      <select value={index} onChange={(e) => r.setScenario(scenarios[Number(e.target.value)])}>
        {index < 0 && <option value={-1}>{scenario.name} (edited)</option>}
        {scenarios.map((s, i) => <option key={s.name} value={i}>{s.name}</option>)}
      </select>
      <label className="seed">seed <input type="number" key={scenario.seed} defaultValue={scenario.seed}
        disabled={r.computing} onKeyDown={(e) => { if (e.key === "Enter") e.currentTarget.blur(); }}
        onBlur={(e) => r.setSeed(Number(e.target.value))} /></label>
      <button onClick={r.newSeed} disabled={r.computing}>New seed</button>
      {r.computing && <span className="computing"><span className="spinner" /> Computing…</span>}
    </div>
  );
}

// --- Playback controls -----------------------------------------------------------------

export function PlayControls({ r, slider = true }: { r: Replay; slider?: boolean }) {
  const { run } = r;
  if (!run) return null;
  return (
    <div className="p-play">
      <button onClick={() => r.setPlaying(!r.playing)}>{r.playing ? "Pause" : "Play"}</button>
      {slider && <input type="range" min={0} max={run.t_s.length - 1} value={r.frame}
        onChange={(e) => r.setFrame(Number(e.target.value))} />}
      <select value={r.speed} onChange={(e) => r.setSpeed(Number(e.target.value))}>
        {SPEEDS.map((s) => <option key={s} value={s}>{s}×</option>)}
      </select>
      <span className="p-time">t = {run.t_s[r.frame].toFixed(1)} s · {run.truth_s_m[r.frame].toFixed(0)} m · {(run.truth_v_mps[r.frame] * 3.6).toFixed(0)} km/h</span>
    </div>
  );
}

// --- Timeline with events on it ----------------------------------------------------------

type Mark = { t: number; color: string; label: string; kind: "callout" | "missed" | "worst" | "truth" };

function marks(run: Run, metrics: EstimatorMetrics[]): Mark[] {
  const exit = run.scenario.route.planned_exit;
  const out: Mark[] = [];
  if (run.missed_exit_t_s != null) out.push({ t: run.missed_exit_t_s, color: TRUTH_COLOR, kind: "truth", label: `car drives past ${exit}` });
  for (const e of run.estimates) {
    for (const c of e.callouts) out.push({ t: c.t_s, color: estimatorColor(e.estimator), kind: "callout", label: `${e.estimator}: "${exit} in ${c.distance_m} m"` });
    if (e.missed_exit_call) out.push({ t: e.missed_exit_call.t_s, color: estimatorColor(e.estimator), kind: "missed", label: `${e.estimator}: "You missed ${exit}"` });
  }
  for (const em of metrics) {
    const worst = em.metrics.find((m) => m.name === "largest error inside");
    if (worst?.at) out.push({ t: worst.at.t_s, color: estimatorColor(em.estimator), kind: "worst", label: `${em.estimator}: largest error inside, ${worst.value?.toFixed(1)} m` });
  }
  return out;
}

// A scrubber that shows where the tunnels are and when things happened; click a mark to jump to it.
export function EventTimeline({ r }: { r: Replay }) {
  const { run, metrics } = r;
  const bar = useRef<HTMLDivElement>(null);
  if (!run) return null;
  const t0 = run.t_s[0], t1 = run.t_s[run.t_s.length - 1];
  const pct = (t: number) => `${(100 * (t - t0)) / (t1 - t0)}%`;
  const seekAt = (clientX: number) => {
    const box = bar.current!.getBoundingClientRect();
    r.seekT(t0 + ((clientX - box.left) / box.width) * (t1 - t0));
  };
  const tunnelTimes = run.tunnels.map((span) => {
    const inside = run.t_s.filter((_, i) => run.truth_s_m[i] >= span.start_m && run.truth_s_m[i] <= span.end_m);
    return [inside[0], inside[inside.length - 1]];
  });
  const symbol = { callout: "▼", missed: "✕", worst: "▲", truth: "●" };
  return (
    <div className="p-timeline">
      <div ref={bar} className="p-bar" onMouseDown={(e) => seekAt(e.clientX)}
        onMouseMove={(e) => e.buttons === 1 && seekAt(e.clientX)}>
        {tunnelTimes.map(([a, b], i) => <div key={i} className="p-tunnel" style={{ left: pct(a), width: `calc(${pct(b)} - ${pct(a)})` }}>tunnel</div>)}
        <div className="p-cursor" style={{ left: pct(run.t_s[r.frame]) }} />
      </div>
      <div className="p-marks">
        {marks(run, metrics).map((m, i) => (
          <button key={i} className={`p-mark ${m.kind}`} style={{ left: pct(m.t), color: m.color }} title={`${m.t.toFixed(1)} s · ${m.label}`}
            onClick={() => r.seekT(m.t)}>{symbol[m.kind]}</button>
        ))}
      </div>
      <div className="p-mark-legend">▼ exit callout · ✕ "you missed it" · ● car really passes the exit · ▲ largest error inside · click a mark to jump there</div>
    </div>
  );
}

// --- Metrics table ----------------------------------------------------------------------

// One row per metric, one column per estimator; the worst moment of each is a link into the replay.
export function MetricsTable({ r, only }: { r: Replay; only?: string[] }) {
  const { metrics } = r;
  if (!metrics.length) return null;
  const names = [...new Set(metrics.flatMap((em) => em.metrics.map((m) => m.name)))].filter((n) => !only || only.includes(n));
  return (
    <table className="p-metrics">
      <thead><tr><th>metric (this seed)</th>{metrics.map((em) => (
        <th key={em.estimator}><i className="dot" style={{ background: estimatorColor(em.estimator) }} /> {em.estimator}</th>
      ))}</tr></thead>
      <tbody>
        {names.map((name) => (
          <tr key={name}>
            <td>{name}</td>
            {metrics.map((em) => {
              const m = em.metrics.find((x) => x.name === name);
              if (!m) return <td key={em.estimator} className="na">–</td>;
              return (
                <td key={em.estimator}>
                  {m.value == null ? "never" : `${m.value.toFixed(1)} ${m.unit}`}
                  {m.at && <button className="p-jump" title={`${m.at.phase}, at ${m.at.s_m.toFixed(0)} m`}
                    onClick={() => r.seekT(m.at!.t_s)}>@ {m.at.t_s.toFixed(0)} s ↗</button>}
                </td>
              );
            })}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

// --- What each estimator thinks right now -------------------------------------------------

export function NowCards({ r, vertical = false }: { r: Replay; vertical?: boolean }) {
  const { run, frame } = r;
  if (!run) return null;
  const exit = run.scenario.route.planned_exit;
  const now = run.t_s[frame];
  return (
    <div className={`p-cards ${vertical ? "vertical" : ""}`}>
      <div className="p-card" style={{ borderColor: TRUTH_COLOR }}>
        <b>ground truth</b>
        <div className="big">{run.truth_s_m[frame].toFixed(0)} m</div>
        <div>on {run.path} · {(run.truth_v_mps[frame] * 3.6).toFixed(0)} km/h</div>
      </div>
      {run.estimates.map((e) => {
        const err = e.error_m[frame], sigma = e.sigma_m[frame], odds = e.branches[frame];
        const said = [
          ...e.callouts.filter((c) => c.t_s <= now).map((c) => ({ t: c.t_s, text: `"${exit} in ${c.distance_m} m"` })),
          ...(e.missed_exit_call && e.missed_exit_call.t_s <= now ? [{ t: e.missed_exit_call.t_s, text: `"You missed ${exit}"` }] : []),
        ].sort((a, b) => b.t - a.t)[0];
        return (
          <div key={e.estimator} className="p-card" style={{ borderColor: estimatorColor(e.estimator) }}>
            <b style={{ color: estimatorColor(e.estimator) }}>{e.estimator}</b>
            <div className="big">{err == null ? "–" : `${err >= 0 ? "+" : ""}${err.toFixed(1)} m`}</div>
            <div>{sigma == null ? "no band" : `band ±${(2 * sigma).toFixed(0)} m`}{err != null && sigma != null && (Math.abs(err) <= 2 * sigma ? " · inside ✓" : " · outside ✗")}</div>
            {e.wrong_branch[frame] && <div className="warn">on the wrong branch ({e.path[frame]})</div>}
            {odds && <div>unsure: {Object.entries(odds).map(([p, v]) => `${p} ${(100 * v).toFixed(0)}%`).join(", ")}</div>}
            {said && <div className="said">last said {(now - said.t).toFixed(0)} s ago: {said.text}</div>}
          </div>
        );
      })}
    </div>
  );
}

// --- Sensors ------------------------------------------------------------------------------

const AXES = ["x (right)", "y (top)", "z (screen)"];
export function sensorLines(run: Run) {
  const axis = (series: number[][]): Line[] => series.map((y, k) => ({ name: AXES[k], y, color: AXIS_COLORS[k] }));
  return {
    accel: axis(run.sensors.accel_mps2),
    gyro: axis(run.sensors.gyro_dps),
    height: [
      { name: "barometer", y: run.sensors.baro_height_m, color: "#0891b2" },
      { name: "ground truth", y: run.truth_height_m, color: TRUTH_COLOR, dash: "dot" as const },
    ] as Line[],
  };
}

export function AssumptionsTable() {
  const [rows, setRows] = useState<SensorAssumption[]>([]);
  useEffect(() => { fetchSensorAssumptions().then(setRows).catch(() => setRows([])); }, []);
  return (
    <table>
      <thead><tr><th>Sensor</th><th>Quantity</th><th>Value</th><th>Source</th></tr></thead>
      <tbody>{rows.map((x) => <tr key={x.sensor + x.quantity}><td>{x.sensor}</td><td>{x.quantity}</td><td>{x.value}</td><td>{x.source}</td></tr>)}</tbody>
    </table>
  );
}

// --- Scenario editor ----------------------------------------------------------------------

type Json = null | boolean | number | string | Json[] | { [k: string]: Json };
const PIECES = ["road", "speed", "mounting"]; // pieces with a "kind" that picks the model
const HIDDEN = ["description", "based_on"]; // fixed facts about a road, not settings

// Every piece of the scenario as a form. Edits stay a draft until "Run this"; "Save as" is a stub here.
export function ScenarioEditor({ r, compact = false }: { r: Replay; compact?: boolean }) {
  const { scenario, scenarios, run } = r;
  const [draft, setDraft] = useState<Json>(scenario as unknown as Json);
  const [saveName, setSaveName] = useState("");
  const [saved, setSaved] = useState<string | null>(null);
  useEffect(() => { setDraft(scenario as unknown as Json); setSaved(null); }, [scenario]);
  if (!scenario || !draft || typeof draft !== "object" || Array.isArray(draft)) return null;

  // A piece of another kind comes with the numbers of a scenario that already uses that kind
  const kinds: Record<string, Record<string, Json>> = {};
  for (const s of scenarios) for (const p of PIECES) {
    const piece = (s as unknown as Record<string, { kind: string }>)[p];
    (kinds[p] ??= {})[piece.kind] ??= piece as unknown as Json;
  }
  const exits = run ? [...new Set(run.exits.map((e) => e.name))] : [];
  const changed = JSON.stringify(draft) !== JSON.stringify(scenario);
  const set = (path: string[], value: Json) => setDraft((d) => setIn(d, path, value));

  return (
    <div className={`p-editor ${compact ? "compact" : ""}`}>
      {Object.entries(draft).filter(([k]) => !["name", "description", "seed"].includes(k)).map(([key, value]) => (
        <fieldset key={key}>
          <legend>{key.replace("_", " ")}</legend>
          {PIECES.includes(key) && (
            <label>kind <select value={(value as { kind: string }).kind} onChange={(e) => set([key], kinds[key][e.target.value])}>
              {Object.keys(kinds[key] ?? {}).map((k) => <option key={k}>{k}</option>)}
            </select></label>
          )}
          {key === "route" ? (
            <RouteFields value={value as Record<string, Json>} exits={exits} set={(p, v) => set(["route", ...p], v)} />
          ) : key === "add_ons" ? (
            Object.entries(value as Record<string, Json>).map(([name, spec]) => (
              <div key={name}>
                <label><input type="checkbox" checked={spec != null} onChange={(e) => set(["add_ons", name], e.target.checked ? {} : null)} /> {name.replace("_", " ")}</label>
                {spec != null && Object.keys(spec).length > 0 && <Fields value={spec} path={["add_ons", name]} set={set} />}
              </div>
            ))
          ) : (
            <Fields value={value} path={[key]} set={set} skip={["kind"]} />
          )}
        </fieldset>
      ))}
      <div className="p-editor-actions">
        <button disabled={!changed || r.computing} onClick={() => r.setScenario({ ...(draft as unknown as Scenario), name: scenario.name.endsWith(" *") ? scenario.name : `${scenario.name} *` })}>Run this</button>
        <button disabled={!changed} onClick={() => setDraft(scenario as unknown as Json)}>Undo edits</button>
        <input placeholder="new scenario name" value={saveName} onChange={(e) => setSaveName(e.target.value)} />
        <button disabled={!saveName} onClick={() => setSaved(saveName)}>Save as</button>
      </div>
      {r.error && <p className="error">{r.error}</p>}
      {saved && <p className="p-note">PROTOTYPE: this would write <code>scenarios/{slug(saved)}.json</code> (nothing was saved).</p>}
    </div>
  );
}

function RouteFields({ value, exits, set }: { value: Record<string, Json>; exits: string[]; set: (p: string[], v: Json) => void }) {
  return (
    <>
      <label>planned exit <select value={(value.planned_exit as string) ?? ""} onChange={(e) => set(["planned_exit"], e.target.value || null)}>
        <option value="">(stay on the main road)</option>
        {exits.map((x) => <option key={x}>{x}</option>)}
      </select></label>
      <label><input type="checkbox" checked={!!value.missed_exit} onChange={(e) => set(["missed_exit"], e.target.checked)} /> driver misses it</label>
      <NumberList label="callouts (m before)" value={value.callouts_m as number[]} onChange={(v) => set(["callouts_m"], v)} />
    </>
  );
}

function Fields({ value, path, set, skip = [] }: { value: Json; path: string[]; set: (p: string[], v: Json) => void; skip?: string[] }) {
  if (value == null || typeof value !== "object" || Array.isArray(value)) return null;
  return (
    <>
      {Object.entries(value).filter(([k]) => !skip.includes(k) && !HIDDEN.includes(k)).map(([k, v]) => {
        const p = [...path, k];
        const label = k.replace(/_/g, " ");
        if (typeof v === "number") return <label key={k}>{label} <input type="number" value={v} step="any" onChange={(e) => set(p, Number(e.target.value))} /></label>;
        if (typeof v === "boolean") return <label key={k}><input type="checkbox" checked={v} onChange={(e) => set(p, e.target.checked)} /> {label}</label>;
        if (typeof v === "string") return <label key={k}>{label} <input value={v} onChange={(e) => set(p, e.target.value)} /></label>;
        if (Array.isArray(v) && v.every((x) => typeof x === "number")) return <NumberList key={k} label={label} value={v as number[]} onChange={(x) => set(p, x)} />;
        if (Array.isArray(v)) return <label key={k}>{label} <input value={JSON.stringify(v)} onChange={(e) => { try { set(p, JSON.parse(e.target.value)); } catch { /* typing */ } }} /></label>;
        return <div key={k} className="p-sub"><span className="p-sub-name">{label}</span><Fields value={v} path={p} set={set} /></div>;
      })}
    </>
  );
}

function NumberList({ label, value, onChange }: { label: string; value: number[]; onChange: (v: number[]) => void }) {
  return <label>{label} <input defaultValue={value.join(", ")} onBlur={(e) => onChange(e.target.value.split(",").map(Number).filter((x) => !isNaN(x)))} /></label>;
}

function setIn(obj: Json, path: string[], value: Json): Json {
  if (!path.length) return value;
  const [head, ...rest] = path;
  const o = (obj ?? {}) as Record<string, Json>;
  return { ...o, [head]: setIn(o[head], rest, value) };
}

const slug = (s: string) => s.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
