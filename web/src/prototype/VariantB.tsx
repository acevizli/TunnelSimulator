// PROTOTYPE variant B, "Report": one column read top to bottom like the write-up. The verdict
// (headline metrics) comes first, then the replay that explains it, then the evidence.
// A slim bar with the scenario, seed and playback stays pinned; the editor folds open under it.
import { useState } from "react";
import Events from "../Events";
import MapView from "../MapView";
import RoadStrip from "../RoadStrip";
import TimePlot from "../TimePlot";
import { AssumptionsTable, MetricsTable, MiniLegend, PlayControls, type Replay, ScenarioEditor, ScenarioPicker, sensorLines } from "./shared";

export const name = "Report: one column, verdict first";
const HEADLINE = ["largest error inside", "error at the exit", "honesty", "recovery after the exit", "missed exit called"];

export default function VariantB({ r }: { r: Replay }) {
  const [editing, setEditing] = useState(false);
  const run = r.run!;
  const truthS = run.truth_s_m[r.frame];
  const sensors = sensorLines(run);
  return (
    <div className={`pb ${r.computing ? "busy" : ""}`}>
      <div className="pb-bar">
        <ScenarioPicker r={r} />
        <button onClick={() => setEditing(!editing)}>{editing ? "Close editor" : "Edit scenario…"}</button>
        <PlayControls r={r} />
      </div>
      {editing && <section className="panel"><ScenarioEditor r={r} /></section>}

      <p className="description">{r.scenario!.description}</p>

      <h3 className="pb-h">1 · How each estimator did (this seed)</h3>
      <section className="panel"><MetricsTable r={r} only={HEADLINE} /></section>

      <h3 className="pb-h">2 · Replay</h3>
      <section className="panel">
        <RoadStrip run={run} frame={r.frame} fromM={0} toM={run.path_length_m} label="whole road" />
        <RoadStrip run={run} frame={r.frame} fromM={truthS - 150} toM={truthS + 150} label="close-up, ±150 m" />
        <MiniLegend run={run} />
      </section>
      <section className="panel maps">
        <MapView run={run} frame={r.frame} />
        <MapView run={run} frame={r.frame} aroundCarM={300} />
      </section>

      <h3 className="pb-h">3 · Where the error came from</h3>
      <section className="panel">
        <h2>Along-track error (band = ±2σ)</h2>
        <TimePlot run={run} frame={r.frame} lines={r.errorLines} yTitle="error (m)" />
        <h2>Speed</h2>
        <TimePlot run={run} frame={r.frame} lines={r.speedLines} yTitle="km/h" />
      </section>
      <Events run={run} frame={r.frame} />

      <h3 className="pb-h">4 · Every metric</h3>
      <section className="panel"><MetricsTable r={r} /></section>

      <h3 className="pb-h">5 · What the phone recorded, and what we assumed about it</h3>
      <section className="panel">
        <h2>Accelerometer (m/s²)</h2><TimePlot run={run} frame={r.frame} lines={sensors.accel} yTitle="m/s²" />
        <h2>Gyroscope (°/s)</h2><TimePlot run={run} frame={r.frame} lines={sensors.gyro} yTitle="°/s" />
        <h2>Barometer height (m)</h2><TimePlot run={run} frame={r.frame} lines={sensors.height} yTitle="m" />
      </section>
      <section className="panel"><AssumptionsTable /></section>
    </div>
  );
}
