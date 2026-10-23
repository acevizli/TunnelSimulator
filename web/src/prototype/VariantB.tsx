// PROTOTYPE variant B, "Report": one column read top to bottom like the write-up: the replay,
// then where the error came from, every metric, and the sensor evidence.
// A slim bar with the scenario, seed and playback stays pinned; the editor folds open under it.
// The real tunnel the road is based on sits small next to the description.
import { useState } from "react";
import { Legend } from "../App";
import Events from "../Events";
import MapView from "../MapView";
import RoadStrip from "../RoadStrip";
import TimePlot from "../TimePlot";
import type { Run } from "../api";
import { AssumptionsTable, MetricsTable, PlayControls, type Replay, ScenarioEditor, ScenarioPicker, sensorLines } from "./shared";

export const name = "Report: one column";

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

      <div className="pb-intro">
        <p className="description">{r.scenario!.description}</p>
        <SmallRealMap run={run} />
      </div>

      <h3 className="pb-h">1 · Replay</h3>
      <section className="panel">
        <RoadStrip run={run} frame={r.frame} fromM={0} toM={run.path_length_m} label="whole road" />
        <RoadStrip run={run} frame={r.frame} fromM={truthS - 150} toM={truthS + 150} label="close-up, ±150 m" />
        <Legend run={run} />
      </section>
      <section className="panel maps">
        <MapView run={run} frame={r.frame} />
        <MapView run={run} frame={r.frame} aroundCarM={300} />
      </section>

      <h3 className="pb-h">2 · Where the error came from</h3>
      <section className="panel">
        <h2>Along-track error (band = ±2σ)</h2>
        <TimePlot run={run} frame={r.frame} lines={r.errorLines} yTitle="error (m)" />
        <h2>Speed</h2>
        <TimePlot run={run} frame={r.frame} lines={r.speedLines} yTitle="km/h" />
      </section>
      <Events run={run} frame={r.frame} />

      <h3 className="pb-h">3 · Every metric</h3>
      <section className="panel"><MetricsTable r={r} /></section>

      <h3 className="pb-h">4 · What the phone recorded, and what we assumed about it</h3>
      <section className="panel">
        <h2>Accelerometer (m/s²)</h2><TimePlot run={run} frame={r.frame} lines={sensors.accel} yTitle="m/s²" />
        <h2>Gyroscope (°/s)</h2><TimePlot run={run} frame={r.frame} lines={sensors.gyro} yTitle="°/s" />
        <h2>Barometer height (m)</h2><TimePlot run={run} frame={r.frame} lines={sensors.height} yTitle="m" />
      </section>
      <section className="panel"><AssumptionsTable /></section>
    </div>
  );
}

// The real tunnel this road is simplified from, small: OpenStreetMap around it and its name.
function SmallRealMap({ run }: { run: Run }) {
  const { name, west, south, east, north } = run.scenario.road.based_on;
  const marker = `${(south + north) / 2},${(west + east) / 2}`;
  const embed = `https://www.openstreetmap.org/export/embed.html?bbox=${[west, south, east, north].join(",")}&layer=mapnik&marker=${marker}`;
  const full = `https://www.openstreetmap.org/?minlon=${west}&minlat=${south}&maxlon=${east}&maxlat=${north}`;
  return (
    <figure className="pb-realmap">
      <iframe title={name} src={embed} loading="lazy" />
      <figcaption>Based on <b>{name}</b> · <a href={full} target="_blank" rel="noreferrer">open map</a></figcaption>
    </figure>
  );
}
