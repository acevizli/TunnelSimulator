import { useEffect, useRef } from "react";
import Plotly from "plotly.js-dist-min";
import type { Run } from "./api";
import { estimatorColor } from "./colors";

type Props = { run: Run; frame: number };

// Along-track error of every estimate over time; the shaded area is the time spent in the tunnel.
export default function ErrorPlot({ run, frame }: Props) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const inTunnel = run.t_s.filter((_, i) => {
      const s = run.truth_s_m[i];
      return s >= run.road.tunnel_start_m && s <= run.road.tunnel_end_m;
    });
    const traces = run.estimates.map((track) => ({
      x: run.t_s,
      y: track.error_m,
      name: track.estimator,
      mode: "lines" as const,
      line: { color: estimatorColor(track.estimator), width: 2 },
    }));
    const tunnel = {
      type: "rect" as const, xref: "x" as const, yref: "paper" as const,
      x0: inTunnel[0], x1: inTunnel[inTunnel.length - 1], y0: 0, y1: 1,
      fillcolor: "#e5e7eb", line: { width: 0 }, layer: "below" as const,
    };
    Plotly.newPlot(ref.current!, traces, {
      height: 280,
      margin: { l: 56, r: 16, t: 16, b: 40 },
      xaxis: { title: { text: "time (s)" } },
      yaxis: { title: { text: "along-track error (m)" }, zeroline: true },
      shapes: [tunnel, cursor(run.t_s[0])],
      legend: { orientation: "h", y: 1.12 },
    }, { displayModeBar: false, responsive: true });
  }, [run]);

  useEffect(() => {
    const div = ref.current!;
    const shapes = (div as unknown as { layout?: { shapes?: object[] } }).layout?.shapes;
    if (shapes) Plotly.relayout(div, { shapes: [shapes[0], cursor(run.t_s[frame])] });
  }, [run, frame]);

  return <div ref={ref} />;
}

function cursor(t: number) {
  return {
    type: "line" as const, xref: "x" as const, yref: "paper" as const,
    x0: t, x1: t, y0: 0, y1: 1, line: { color: "#111827", width: 1, dash: "dot" as const },
  };
}
