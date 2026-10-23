// PROTOTYPE variant C, "Cockpit": built for watching a drive and jumping to what matters.
// The map is big, each estimator has a live card (error, band, branch, last thing said),
// and the timeline carries the events, so you click a callout or the worst moment to go there.
// Plots, metrics, sensors, assumptions and the editor live in a drawer that slides up.
import { useState } from "react";
import Events from "../Events";
import MapView from "../MapView";
import RoadStrip from "../RoadStrip";
import TimePlot from "../TimePlot";
import { AssumptionsTable, EventTimeline, MetricsTable, MiniLegend, NowCards, PlayControls, type Replay, ScenarioEditor, ScenarioPicker, sensorLines } from "./shared";

export const name = "Cockpit: big map, live cards, event timeline, drawer";
const DRAWER = ["Error & speed", "Metrics", "What the driver hears", "Sensors", "Assumptions", "Edit scenario"] as const;

export default function VariantC({ r }: { r: Replay }) {
  const [drawer, setDrawer] = useState<(typeof DRAWER)[number] | null>(null);
  const run = r.run!;
  const truthS = run.truth_s_m[r.frame];
  const sensors = sensorLines(run);
  return (
    <div className={`pc ${r.computing ? "busy" : ""}`}>
      <div className="pc-head">
        <ScenarioPicker r={r} />
        <span className="description">{r.scenario!.description}</span>
      </div>
      <div className="pc-stage">
        <div className="pc-map"><MapView run={run} frame={r.frame} aroundCarM={400} height={440} /></div>
        <NowCards r={r} vertical />
      </div>
      <RoadStrip run={run} frame={r.frame} fromM={truthS - 150} toM={truthS + 150} label="close-up, ±150 m around the true car" />
      <MiniLegend run={run} />
      <div className="pc-timeline">
        <PlayControls r={r} slider={false} />
        <EventTimeline r={r} />
      </div>

      <div className={`pc-drawer ${drawer ? "open" : ""}`}>
        <nav>
          {DRAWER.map((d) => <button key={d} className={d === drawer ? "on" : ""} onClick={() => setDrawer(d === drawer ? null : d)}>{d}</button>)}
          {drawer && <button className="pc-close" onClick={() => setDrawer(null)}>close ✕</button>}
        </nav>
        {drawer && <div className="pc-drawer-body">
          {drawer === "Error & speed" && <>
            <TimePlot run={run} frame={r.frame} lines={r.errorLines} yTitle="error (m)" />
            <TimePlot run={run} frame={r.frame} lines={r.speedLines} yTitle="km/h" />
          </>}
          {drawer === "Metrics" && <MetricsTable r={r} />}
          {drawer === "What the driver hears" && <Events run={run} frame={r.frame} />}
          {drawer === "Sensors" && <>
            <TimePlot run={run} frame={r.frame} lines={sensors.accel} yTitle="accel m/s²" />
            <TimePlot run={run} frame={r.frame} lines={sensors.gyro} yTitle="gyro °/s" />
            <TimePlot run={run} frame={r.frame} lines={sensors.height} yTitle="height m" />
          </>}
          {drawer === "Assumptions" && <AssumptionsTable />}
          {drawer === "Edit scenario" && <ScenarioEditor r={r} />}
        </div>}
      </div>
    </div>
  );
}
