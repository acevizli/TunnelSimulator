import { useEffect, useMemo, useRef, useState } from "react";
import { computeRun, fetchScenarios, type Run, type Scenario } from "./api";
import { TRUTH_COLOR, estimatorColor } from "./colors";
import RoadStrip from "./RoadStrip";
import TimePlot, { type Line } from "./TimePlot";

const OUTPUT_HZ = 10; // matches the core's recording rate
const SPEEDS = [1, 5, 10, 25];
const CLOSE_UP_M = 150;

export default function App() {
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [scenario, setScenario] = useState<Scenario | null>(null);
  const [run, setRun] = useState<Run | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [frame, setFrame] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(10);

  useEffect(() => {
    fetchScenarios().then((list) => { setScenarios(list); setScenario(list[0]); }).catch((e) => setError(String(e)));
  }, []);

  useEffect(() => {
    if (!scenario) return;
    setPlaying(false);
    computeRun(scenario)
      .then((r) => { setRun(r); setFrame(0); })
      .catch((e) => setError(String(e)));
  }, [scenario]);

  usePlayback(playing, speed, run, setFrame, () => setPlaying(false));
  const errorLines = useMemo<Line[]>(() => run ? run.estimates.map((e) =>
    ({ name: e.estimator, y: e.error_m, color: estimatorColor(e.estimator) })) : [], [run]);
  const speedLines = useMemo<Line[]>(() => run ? [
    { name: "ground truth", y: run.truth_v_mps.map((v) => v * 3.6), color: TRUTH_COLOR },
    ...run.estimates.map((e) => ({ name: e.estimator, y: e.v_mps.map((v) => v == null ? null : v * 3.6),
      color: estimatorColor(e.estimator), dash: "dot" as const })),
  ] : [], [run]);

  if (error) return <main><p className="error">{error}</p></main>;
  if (!scenario || !run) return <main><p>Computing run…</p></main>;

  const t = run.t_s[frame];
  const truthS = run.truth_s_m[frame];
  const newSeed = () => setScenario({ ...scenario, seed: Math.floor(Math.random() * 1_000_000) });

  return (
    <main>
      <header>
        <select value={scenarios.findIndex((s) => s.name === scenario.name)}
          onChange={(e) => setScenario(scenarios[Number(e.target.value)])}>
          {scenarios.map((s, i) => <option key={s.name} value={i}>{s.name}</option>)}
        </select>
        <span className="seed">seed {scenario.seed}</span>
        <button onClick={newSeed}>New seed</button>
      </header>
      <p className="description">{scenario.description}</p>

      <section className="panel">
        <RoadStrip run={run} frame={frame} fromM={0} toM={run.path_length_m} label="whole road" />
        <RoadStrip run={run} frame={frame} fromM={truthS - CLOSE_UP_M} toM={truthS + CLOSE_UP_M}
          label={`close-up, ±${CLOSE_UP_M} m around the true car`} />
        <Legend run={run} />
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
            const onPath = e.path[frame];
            const wrong = onPath != null && onPath !== run.path ? ` (thinks: ${onPath})` : "";
            return <span key={e.estimator}> · {e.estimator} error {err == null ? "–" : `${err.toFixed(1)} m`}{wrong}</span>;
          })}
        </span>
      </section>

      <section className="panel">
        <h2>Along-track error</h2>
        <TimePlot run={run} frame={frame} lines={errorLines} yTitle="error (m)" />
      </section>
      <section className="panel">
        <h2>Speed</h2>
        <TimePlot run={run} frame={frame} lines={speedLines} yTitle="km/h" />
      </section>
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
      <span><i style={{ background: "#2563eb" }} /> GPS fixes (last 5 s)</span>
      <span><i style={{ background: "#d1d5db" }} /> tunnel</span>
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
