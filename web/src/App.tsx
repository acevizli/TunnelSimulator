import { useEffect, useMemo, useRef, useState } from "react";
import {
  computeRun, fetchPieceChoices, fetchScenarios, saveScenario,
  type EstimatorMetrics, type PieceChoices, type Run, type Scenario,
} from "./api";
import { BEACON_COLORS, TRUTH_COLOR, bandColor, estimatorColor } from "./colors";
import Events from "./Events";
import MapView from "./MapView";
import MetricsTable from "./MetricsTable";
import RealMap from "./RealMap";
import RoadStrip from "./RoadStrip";
import ScenarioEditor from "./ScenarioEditor";
import SensorPanel from "./SensorPanel";
import TimePlot, { type Line } from "./TimePlot";

const OUTPUT_HZ = 10; // matches the core's recording rate
const SPEEDS = [1, 5, 10, 25];
const CLOSE_UP_M = 150;

// One column, read top to bottom: the replay, where the error came from, every metric, and
// what the phone recorded. The bar with the scenario, seed and playback stays at the top.
export default function App() {
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [choices, setChoices] = useState<PieceChoices | null>(null);
  const [scenario, setScenario] = useState<Scenario | null>(null);
  const [run, setRun] = useState<Run | null>(null);
  const [metrics, setMetrics] = useState<EstimatorMetrics[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [computing, setComputing] = useState(false);
  const [editing, setEditing] = useState(false);
  const [frame, setFrame] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(10);

  useEffect(() => {
    fetchScenarios().then((list) => { setScenarios(list); setScenario(list[0]); }).catch((e) => setError(String(e)));
    fetchPieceChoices().then(setChoices).catch((e) => setError(String(e)));
  }, []);

  useEffect(() => {
    if (!scenario) return;
    let latest = true; // a slower, older run must not replace the one asked for last
    setPlaying(false);
    setComputing(true);
    setError(null);
    computeRun(scenario)
      .then((r) => { if (latest) { setRun(r.run); setMetrics(r.metrics); setFrame(0); } })
      .catch((e) => latest && setError(e.message ?? String(e)))
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
    // What the car itself reported (vehicle-speed add-on), with its own error in it
    ...(run.sensors.vehicle_speed_mps.length ? [{ name: "car's own reading", y: run.sensors.vehicle_speed_mps.map((v) => v * 3.6),
      color: "#9ca3af" }] : []),
  ] : [], [run]);

  if (!scenario || !run || !choices) {
    return <main>{error ? <p className="error">{error}</p> : <p className="computing"><span className="spinner" /> Computing run…</p>}</main>;
  }

  const truthS = run.truth_s_m[frame];
  const setSeed = (seed: number) => { if (Number.isInteger(seed) && seed !== scenario.seed) setScenario({ ...scenario, seed }); };
  const newSeed = () => setSeed(Math.floor(Math.random() * 1_000_000));
  const jumpTo = (t: number) => setFrame(Math.max(0, Math.min(run.t_s.length - 1, Math.round((t - run.t_s[0]) * OUTPUT_HZ))));
  const save = async (s: Scenario) => {
    const saved = await saveScenario(s);
    setScenarios(await fetchScenarios());
    setScenario(saved);
  };
  // The picker shows the listed scenario, marked when it has been edited (a new seed is not an edit)
  const listed = scenarios.findIndex((s) => s.name === scenario.name);
  const edited = listed < 0 || JSON.stringify({ ...scenarios[listed], seed: 0 }) !== JSON.stringify({ ...scenario, seed: 0 });

  return (
    <main className={computing ? "busy" : ""}>
      <header className="bar">
        <select value={listed} onChange={(e) => setScenario(scenarios[Number(e.target.value)])}>
          {listed < 0 && <option value={-1}>{scenario.name} (edited)</option>}
          {scenarios.map((s, i) => <option key={s.name} value={i}>{s.name}{i === listed && edited ? " (edited)" : ""}</option>)}
        </select>
        {/* Typed-in seed (e.g. a worst seed from the measurement report); runs on Enter or leaving the field */}
        <label className="seed">seed <input type="number" key={scenario.seed} defaultValue={scenario.seed}
          disabled={computing} onKeyDown={(e) => { if (e.key === "Enter") e.currentTarget.blur(); }}
          onBlur={(e) => setSeed(Number(e.target.value))} /></label>
        <button onClick={newSeed} disabled={computing}>New seed</button>
        <button onClick={() => setEditing(!editing)}>{editing ? "Close editor" : "Edit scenario…"}</button>
        {computing && <span className="computing"><span className="spinner" /> Computing run…</span>}
        <div className="playback">
          <button onClick={() => setPlaying(!playing)}>{playing ? "Pause" : "Play"}</button>
          <input type="range" min={0} max={run.t_s.length - 1} value={frame} onChange={(e) => setFrame(Number(e.target.value))} />
          <select value={speed} onChange={(e) => setSpeed(Number(e.target.value))}>
            {SPEEDS.map((s) => <option key={s} value={s}>{s}×</option>)}
          </select>
          <span className="readout">
            t = {run.t_s[frame].toFixed(1)} s · truth {truthS.toFixed(0)} m on {run.path} at {(run.truth_v_mps[frame] * 3.6).toFixed(0)} km/h
          </span>
        </div>
      </header>
      {error && <p className="error">{error}</p>}
      {editing && (
        <section className="panel">
          <ScenarioEditor scenario={scenario} choices={choices} computing={computing} run={setScenario} save={save} />
        </section>
      )}

      <div className="intro">
        <p className="description">{scenario.description}</p>
        <RealMap run={run} />
      </div>

      <h3>1 · Replay</h3>
      <section className="panel">
        <RoadStrip run={run} frame={frame} fromM={0} toM={run.path_length_m} label="whole road" />
        <RoadStrip run={run} frame={frame} fromM={truthS - CLOSE_UP_M} toM={truthS + CLOSE_UP_M}
          label={`close-up, ±${CLOSE_UP_M} m around the true car`} />
        <Legend run={run} />
      </section>
      <section className="panel maps">
        <div><h2>Map, from above</h2><MapView run={run} frame={frame} /></div>
        <div><h2>Close-up, ±300 m around the true car</h2><MapView run={run} frame={frame} aroundCarM={300} /></div>
      </section>

      <h3>2 · Where the error came from</h3>
      <section className="panel">
        <h2>Along-track error</h2>
        <TimePlot run={run} frame={frame} lines={errorLines} yTitle="error (m)" />
        <h2>Speed</h2>
        <TimePlot run={run} frame={frame} lines={speedLines} yTitle="km/h" />
      </section>
      <Events run={run} frame={frame} />

      <h3>3 · Every metric</h3>
      <section className="panel"><MetricsTable metrics={metrics} jumpTo={jumpTo} /></section>

      <h3>4 · What the phone recorded, and what we assumed about it</h3>
      <SensorPanel run={run} frame={frame} />
    </main>
  );
}

function Legend({ run }: { run: Run }) {
  const names = new Set(run.estimates.map((e) => e.estimator));
  return (
    <div className="legend">
      <span><i style={{ background: TRUTH_COLOR }} /> ground truth</span>
      {run.estimates.map((e) => (
        <span key={e.estimator}><i style={{ background: estimatorColor(e.estimator) }} /> {e.estimator}</span>
      ))}
      <span><i style={{ background: "#2563eb" }} /> GPS fixes (last 5 s; colours in section 4)</span>
      <span><i style={{ background: "#d1d5db" }} /> tunnel</span>
      {run.beacons.length > 0 && <>
        <span><i style={{ background: BEACON_COLORS.heard }} /> beacon heard</span>
        <span><i style={{ background: BEACON_COLORS.unheard }} /> beacon not (yet) heard</span>
        <span><i style={{ background: BEACON_COLORS.dead }} /> dead beacon</span>
      </>}
      <span className="note">Baseline: a GPS-only app that keeps going at the last GPS speed along the planned route once GPS is lost.</span>
      <span className="note">Map filter: moves the car along the mapped road using the phone's forward acceleration, and keeps correcting it by matching the gyroscope's turn rate and the barometer's climb rate to the curves and slopes on the map (and to GPS while it's good). At a fork it follows both branches and drops the one the sensors don't fit.</span>
      {names.has("map filter + vehicle speed") && <span className="note">Map filter + vehicle speed: the same, plus the speed the car itself reports. The car's reading is a few % off; its scale and offset are learned against GPS before the tunnel and then held.</span>}
      {names.has("map filter + beacons") && <span className="note">Map filter + beacons: the same, plus a position fix each time it hears a tunnel beacon (one every 35 m, some unheard or dead). A beacon on another branch puts the car on that branch.</span>}
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
