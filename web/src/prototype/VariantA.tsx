// PROTOTYPE variant A, "Workbench": the scenario editor always open on the left; the road and
// controls pinned at the top; everything else in tabs, so the whole page fits one screen.
import { useState } from "react";
import { Legend } from "../App";
import Events from "../Events";
import MapView from "../MapView";
import RoadStrip from "../RoadStrip";
import TimePlot from "../TimePlot";
import { AssumptionsTable, MetricsTable, PlayControls, type Replay, ScenarioEditor, ScenarioPicker, sensorLines } from "./shared";

export const name = "Workbench: editor sidebar + tabs";
const TABS = ["Error & speed", "What the driver hears", "Metrics", "Map", "Sensors", "Assumptions"] as const;

export default function VariantA({ r }: { r: Replay }) {
  const [tab, setTab] = useState<(typeof TABS)[number]>("Error & speed");
  const run = r.run!;
  const truthS = run.truth_s_m[r.frame];
  const sensors = sensorLines(run);
  return (
    <div className={`pa ${r.computing ? "busy" : ""}`}>
      <aside className="pa-side">
        <ScenarioPicker r={r} />
        <p className="description">{r.scenario!.description}</p>
        <h2>Scenario pieces</h2>
        <ScenarioEditor r={r} compact />
      </aside>
      <div className="pa-main">
        <div className="pa-top">
          <RoadStrip run={run} frame={r.frame} fromM={0} toM={run.path_length_m} label="whole road" />
          <RoadStrip run={run} frame={r.frame} fromM={truthS - 150} toM={truthS + 150} label="close-up, ±150 m" />
          <Legend run={run} />
          <PlayControls r={r} />
        </div>
        <nav className="pa-tabs">
          {TABS.map((t) => <button key={t} className={t === tab ? "on" : ""} onClick={() => setTab(t)}>{t}</button>)}
        </nav>
        <div className="pa-body">
          {tab === "Error & speed" && <>
            <h2>Along-track error (band = ±2σ)</h2>
            <TimePlot run={run} frame={r.frame} lines={r.errorLines} yTitle="error (m)" />
            <h2>Speed</h2>
            <TimePlot run={run} frame={r.frame} lines={r.speedLines} yTitle="km/h" />
          </>}
          {tab === "What the driver hears" && <Events run={run} frame={r.frame} />}
          {tab === "Metrics" && <MetricsTable r={r} />}
          {tab === "Map" && <div className="maps">
            <MapView run={run} frame={r.frame} />
            <MapView run={run} frame={r.frame} aroundCarM={300} />
          </div>}
          {tab === "Sensors" && <>
            <h2>Accelerometer (m/s²)</h2><TimePlot run={run} frame={r.frame} lines={sensors.accel} yTitle="m/s²" />
            <h2>Gyroscope (°/s)</h2><TimePlot run={run} frame={r.frame} lines={sensors.gyro} yTitle="°/s" />
            <h2>Barometer height (m)</h2><TimePlot run={run} frame={r.frame} lines={sensors.height} yTitle="m" />
          </>}
          {tab === "Assumptions" && <AssumptionsTable />}
        </div>
      </div>
    </div>
  );
}
