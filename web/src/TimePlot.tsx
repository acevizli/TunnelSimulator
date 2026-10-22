import { useEffect, useRef } from "react";
import Plotly from "plotly.js-dist-min";
import type { Run } from "./api";

// A band is drawn as two lines: its "lower" edge (invisible) and its "upper" edge, shaded down to the lower one.
export type Line = {
  name: string; y: (number | null)[]; color: string; dash?: "dot" | "solid"; width?: number; band?: "lower" | "upper";
};
type Props = { run: Run; frame: number; lines: Line[]; yTitle: string };

// Quantities over time; shaded areas are the times the true car is inside a tunnel.
export default function TimePlot({ run, frame, lines, yTitle }: Props) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const traces = lines.map((line) => ({
      x: run.t_s, y: line.y, name: line.name, mode: "lines" as const,
      line: { color: line.color, width: line.band ? 0 : line.width ?? 2, dash: line.dash ?? "solid" },
      ...(line.band && { hoverinfo: "skip" as const, showlegend: line.band === "upper" }),
      ...(line.band === "upper" && { fill: "tonexty" as const, fillcolor: line.color }),
    }));
    Plotly.newPlot(ref.current!, traces, {
      height: 240,
      margin: { l: 56, r: 16, t: 8, b: 36 },
      xaxis: { title: { text: "time (s)" } },
      yaxis: { title: { text: yTitle }, zeroline: true },
      shapes: [...tunnelTimes(run).map(shade), cursor(run.t_s[0])],
      legend: { orientation: "h", y: 1.15 },
    }, { displayModeBar: false, responsive: true });
  }, [run, lines, yTitle]);

  useEffect(() => {
    const div = ref.current!;
    const shapes = (div as unknown as { layout?: { shapes?: object[] } }).layout?.shapes;
    if (shapes) Plotly.relayout(div, { shapes: [...shapes.slice(0, -1), cursor(run.t_s[frame])] });
  }, [run, frame]);

  return <div ref={ref} />;
}

// [start, end] times of each stretch the true car spends inside a tunnel
function tunnelTimes(run: Run): [number, number][] {
  return run.tunnels.map((span) => {
    const inside = run.t_s.filter((_, i) => run.truth_s_m[i] >= span.start_m && run.truth_s_m[i] <= span.end_m);
    return [inside[0], inside[inside.length - 1]];
  });
}

function shade([t0, t1]: [number, number]) {
  return {
    type: "rect" as const, xref: "x" as const, yref: "paper" as const,
    x0: t0, x1: t1, y0: 0, y1: 1, fillcolor: "#e5e7eb", line: { width: 0 }, layer: "below" as const,
  };
}

function cursor(t: number) {
  return {
    type: "line" as const, xref: "x" as const, yref: "paper" as const,
    x0: t, x1: t, y0: 0, y1: 1, line: { color: "#111827", width: 1, dash: "dot" as const },
  };
}
