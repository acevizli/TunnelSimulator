import { useEffect, useRef } from "react";
import Plotly from "plotly.js-dist-min";
import type { Run } from "./api";
import { ROUTE_COLOR, TRUTH_COLOR, estimatorColor } from "./colors";

type Props = { run: Run; frame: number; aroundCarM?: number; height?: number };

// The road from above, with every branch: shows which branch the car and each estimate are on.
// An estimate on a branch the car isn't driving is drawn as a hollow ring.
export default function MapView({ run, frame, aroundCarM, height = 320 }: Props) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const traces = [...roadTraces(run), ...movingTraces(run, frame)];
    Plotly.newPlot(ref.current!, traces, {
      height,
      margin: { l: 8, r: 80, t: 8, b: 8 },  // room on the right for branch names
      xaxis: { visible: false },
      yaxis: { visible: false, scaleanchor: "x", scaleratio: 1 },
      legend: { orientation: "h", y: -0.02 },
      showlegend: aroundCarM == null,
    }, { displayModeBar: false, responsive: true });
  }, [run, height]);

  useEffect(() => {
    const div = ref.current!;
    const moving = movingTraces(run, frame);
    const first = roadTraces(run).length;
    Plotly.restyle(div, {
      x: moving.map((t) => t.x), y: moving.map((t) => t.y), "marker.symbol": moving.map((t) => t.marker.symbol),
    }, moving.map((_, k) => first + k));
    if (aroundCarM != null) {
      const [cx, cy] = [run.truth_x_m[frame], run.truth_y_m[frame]];
      Plotly.relayout(div, { "xaxis.range": [cx - aroundCarM, cx + aroundCarM], "yaxis.range": [cy - aroundCarM, cy + aroundCarM] });
    }
  }, [run, frame, aroundCarM]);

  return <div ref={ref} />;
}

// Tunnels (wide grey), every path (the driven one darker), the route (green dots) and branch names.
function roadTraces(run: Run) {
  const route = run.scenario.route.planned_exit ?? "main";
  const tunnels = run.shapes.map((p) => ({
    x: p.x_m.map((x, i) => (p.tunnel[i] ? x : null)), y: p.y_m.map((y, i) => (p.tunnel[i] ? y : null)),
    mode: "lines" as const, line: { color: "#e5e7eb", width: 12 }, showlegend: false, hoverinfo: "skip" as const,
  }));
  const roads = run.shapes.map((p) => ({
    x: p.x_m, y: p.y_m, mode: "lines+text" as const, showlegend: false, hoverinfo: "skip" as const, cliponaxis: false,
    line: { color: p.name === run.path ? "#4b5563" : "#9ca3af", width: 2 },
    text: p.x_m.map((_, i) => (i === p.x_m.length - 1 ? p.name : "")), textposition: "middle right" as const,
  }));
  const shape = run.shapes.find((p) => p.name === route)!;
  const routeLine = {
    x: shape.x_m, y: shape.y_m, mode: "lines" as const, name: `route (${route})`, hoverinfo: "skip" as const,
    line: { color: ROUTE_COLOR, width: 2, dash: "dot" as const },
  };
  return [...tunnels, ...roads, routeLine];
}

// The true car and every estimate at this frame
function movingTraces(run: Run, frame: number) {
  const truth = {
    x: [run.truth_x_m[frame]], y: [run.truth_y_m[frame]], mode: "markers" as const, name: "ground truth",
    marker: { color: TRUTH_COLOR, size: 12, symbol: "circle" },
  };
  const estimates = run.estimates.map((e) => ({
    x: [e.x_m[frame]], y: [e.y_m[frame]], mode: "markers" as const, name: e.estimator,
    marker: {
      color: estimatorColor(e.estimator), size: 11, line: { width: 3, color: estimatorColor(e.estimator) },
      symbol: e.wrong_branch[frame] ? "circle-open" : "circle",
    },
  }));
  return [truth, ...estimates];
}
