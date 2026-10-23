import { useEffect, useMemo, useRef, useState } from "react";
import { computeRun, fetchScenarios, type Run, type Scenario } from "./api";
import { TRUTH_COLOR, bandColor, estimatorColor } from "./colors";
import Events from "./Events";
import MapView from "./MapView";
import RealMap from "./RealMap";
import RoadStrip from "./RoadStrip";
import SensorPanel from "./SensorPanel";
import TimePlot, { type Line } from "./TimePlot";

const OUTPUT_HZ = 10; // matches the core's recording rate
const SPEEDS = [1, 5, 10, 25];
const CLOSE_UP_M = 150;

export default function App() {
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [scenario, setScenario] = useState<Scenario | null>(null);
  const [run, setRun] = useState<Run | null>(null);
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
    let latest = true; // a slower, older run must not replace the one asked for last
    setPlaying(false);
    setComputing(true);
    computeRun(scenario)
      .then((r) => { if (latest) { setRun(r); setFrame(0); } })
      .catch((e) => latest && setError(String(e)))
      .finally(() => latest && setComputing(false));
    return () => { latest = false; };
  }, [scenario]);

  usePlayback(playing, speed, run, setFrame, () => setPlaying(false));
  // Each estimator's error, over its uncertainty band (±2σ around zero): inside the band = honest
  const errorLines = useMemo<Line[]>(() => run ? [
    ...run.estimates.filter((e) => e.sigma_m.some((s) => s != null)).flatMap((e): Line[] => [
      { name: `${e.estimator} band`, y: e.sigma_m.map((s) => s == null ? null : -2 * s), color: bandColor(e.estimator), band: "lower" },
      { name: `${e.estimator} band (±2σ)`, y: e.sigma_m.map((s) => s == null ? null : 2 * s), color: bandColor(e.estimator), band: "upper" },
    ]),
    ...run.estimates.map((e) => ({ name: e.estimator, y: e.error_m, color: estimatorColor(e.estimator) })),
    // Thick dots over the stretches an estimator spends on a branch the car isn't driving
    ...run.estimates.filter((e) => e.wrong_branch.some(Boolean)).map((e): Line => ({
      name: `${e.estimator} on the wrong branch`, y: e.error_m.map((v, i) => (e.wrong_branch[i] ? v : null)),
      color: estimatorColor(e.estimator), dash: "dot", width: 6,
    })),
  ] : [], [run]);
  const speedLines = useMemo<Line[]>(() => run ? [
    { name: "ground truth", y: run.truth_v_mps.map((v) => v * 3.6), color: TRUTH_COLOR },
    ...run.estimates.map((e) => ({ name: e.estimator, y: e.v_mps.map((v) => v == null ? null : v * 3.6),
      color: estimatorColor(e.estimator), dash: "dot" as const })),
  ] : [], [run]);

  if (error) return <main><p className="error">{error}</p></main>;
  if (!scenario || !run) return <main><p className="computing"><span className="spinner" /> Computing run…</p></main>;

  const t = run.t_s[frame];
  const truthS = run.truth_s_m[frame];
  const newSeed = () => setScenario({ ...scenario, seed: Math.floor(Math.random() * 1_000_000) });

  return (
    <main className={computing ? "busy" : ""}>
      <header>
        <select value={scenarios.findIndex((s) => s.name === scenario.name)}
          onChange={(e) => setScenario(scenarios[Number(e.target.value)])}>
          {scenarios.map((s, i) => <option key={s.name} value={i}>{s.name}</option>)}
        </select>
        <span className="seed">seed {scenario.seed}</span>
        <button onClick={newSeed} disabled={computing}>New seed</button>
        {computing && <span className="computing"><span className="spinner" /> Computing run…</span>}
      </header>
      <p className="description">{scenario.description}</p>

      <section className="panel">
        <RoadStrip run={run} frame={frame} fromM={0} toM={run.path_length_m} label="whole road" />
        <RoadStrip run={run} frame={frame} fromM={truthS - CLOSE_UP_M} toM={truthS + CLOSE_UP_M}
          label={`close-up, ±${CLOSE_UP_M} m around the true car`} />
        <Legend run={run} />
      </section>

      <section className="panel maps">
        <div><h2>Map, from above</h2><MapView run={run} frame={frame} /></div>
        <div><h2>The real tunnel this road is based on</h2><RealMap run={run} /></div>
        <div><h2>Close-up, ±300 m around the true car</h2><MapView run={run} frame={frame} aroundCarM={300} /></div>
      </section>

      <section className="controls">
        <button onClick={() => setPlaying(!playing)}>{playing ? "Pause" : "Play"}</button>
        <input type="range" min={0} max={run.t_s.length - 1} value={frame}
          onChange={(e) => setFrame(Number(e.target.value))} />
        <select value={speed} onChange={(e) => setSpeed(Number(e.target.value))}>
          {SPEEDS.map((s) => <option key={s} value={s}>{s}×</option>)}
        </select>
        <span className="readout">
          t = {t.toFixed(1)} s · truth {truthS.toFixed(0)} m on {run.path} at {(run.truth_v_mps[frame] * 3.6).toFixed(0)} km/h
          {run.estimates.map((e) => {
            const err = e.error_m[frame];
            const sigma = e.sigma_m[frame];
            const onPath = e.path[frame];
            const wrong = e.wrong_branch[frame] ? ` — on the wrong branch (${onPath})` : "";
            const band = sigma == null ? "" : ` (band ±${(2 * sigma).toFixed(0)} m)`;
            const odds = e.branches[frame];
            const unsure = odds ? ` — unsure which branch: ${Object.entries(odds)
              .map(([path, p]) => `${path} ${(100 * p).toFixed(0)}%`).join(", ")}` : "";
            return <span key={e.estimator}> · {e.estimator} error {err == null ? "–" : `${err.toFixed(1)} m`}{band}{wrong}{unsure}</span>;
          })}
        </span>
      </section>

      <Events run={run} frame={frame} />

      <section className="panel">
        <h2>Along-track error</h2>
        <TimePlot run={run} frame={frame} lines={errorLines} yTitle="error (m)" />
      </section>
      <section className="panel">
        <h2>Speed</h2>
        <TimePlot run={run} frame={frame} lines={speedLines} yTitle="km/h" />
      </section>
      <SensorPanel run={run} frame={frame} />
    </main>
  );
}

function Legend({ run }: { run: Run }) {
  return (
    <div className="legend">
      <span><i style={{ background: TRUTH_COLOR }} /> ground truth</span>
      {run.estimates.map((e) => (
        <span key={e.estimator}><i style={{ background: estimatorColor(e.estimator) }} /> {e.estimator}</span>
      ))}
      <span><i style={{ background: "#2563eb" }} /> GPS fixes (last 5 s; colours below)</span>
      <span><i style={{ background: "#d1d5db" }} /> tunnel</span>
      <span className="note">Baseline: a GPS-only app that keeps going at the last GPS speed along the planned route once GPS is lost.</span>
      <span className="note">Map filter: moves the car along the mapped road using the phone's forward acceleration, and keeps correcting it by matching the gyroscope's turn rate and the barometer's climb rate to the curves and slopes on the map (and to GPS while it's good). At a fork it follows both branches and drops the one the sensors don't fit.</span>
    </div>
  );
}

// Advances the frame in real time × speed while playing.
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
