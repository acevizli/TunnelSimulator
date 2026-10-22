import { useEffect, useMemo, useState } from "react";
import { fetchSensorAssumptions, type Run, type SensorAssumption } from "./api";
import { AXIS_COLORS, GPS_PHASE_COLORS, TRUTH_COLOR } from "./colors";
import TimePlot, { type Line } from "./TimePlot";

const AXES = ["x (right)", "y (top)", "z (screen)"];

// What the phone recorded, in its own axes, next to the fixed sensor assumptions.
export default function SensorPanel({ run, frame }: { run: Run; frame: number }) {
  const accel = useMemo(() => axisLines(run.sensors.accel_mps2), [run]);
  const gyro = useMemo(() => axisLines(run.sensors.gyro_dps), [run]);
  const height = useMemo<Line[]>(() => [
    { name: "barometer", y: run.sensors.baro_height_m, color: "#0891b2" },
    { name: "ground truth", y: run.truth_height_m, color: TRUTH_COLOR, dash: "dot" },
  ], [run]);

  return (
    <>
      <section className="panel">
        <h2>Accelerometer (m/s², phone axes, 0.1 s averages)</h2>
        <TimePlot run={run} frame={frame} lines={accel} yTitle="m/s²" />
        <h2>Gyroscope (°/s, phone axes)</h2>
        <TimePlot run={run} frame={frame} lines={gyro} yTitle="°/s" />
        <h2>Barometer height (m, relative to the start)</h2>
        <TimePlot run={run} frame={frame} lines={height} yTitle="m" />
        <GpsLegend />
      </section>
      <AssumptionsTable />
    </>
  );
}

function axisLines(series: number[][]): Line[] {
  return series.map((y, k) => ({ name: AXES[k], y, color: AXIS_COLORS[k] }));
}

function GpsLegend() {
  const labels: Record<string, string> = {
    open: "normal", fade: "fading / converging", multipath: "bounced or biased",
    coast: "fake (extrapolated by the phone)",
  };
  return (
    <div className="legend">
      <span>GPS fixes on the road:</span>
      {Object.entries(labels).map(([phase, label]) => (
        <span key={phase}><i style={{ background: GPS_PHASE_COLORS[phase] }} /> {label}</span>
      ))}
    </div>
  );
}

function AssumptionsTable() {
  const [rows, setRows] = useState<SensorAssumption[]>([]);
  useEffect(() => { fetchSensorAssumptions().then(setRows).catch(() => setRows([])); }, []);
  return (
    <section className="panel">
      <h2>Sensor assumptions (one "typical" phone, fixed)</h2>
      <table>
        <thead><tr><th>Sensor</th><th>Quantity</th><th>Value</th><th>Source</th></tr></thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.sensor + r.quantity}><td>{r.sensor}</td><td>{r.quantity}</td><td>{r.value}</td><td>{r.source}</td></tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
