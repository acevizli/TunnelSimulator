import { useEffect, useRef } from "react";
import type { Run } from "./api";
import { GPS_COLOR, TRUTH_COLOR, estimatorColor } from "./colors";

type Props = { run: Run; frame: number; fromM: number; toM: number; label: string };

// Draws the stretch of road [fromM, toM] with the tunnel, the true car and every estimate.
export default function RoadStrip({ run, frame, fromM, toM, label }: Props) {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = ref.current!;
    const width = canvas.clientWidth;
    const height = 90;
    const dpr = window.devicePixelRatio || 1;
    canvas.width = width * dpr;
    canvas.height = height * dpr;
    const ctx = canvas.getContext("2d")!;
    ctx.scale(dpr, dpr);
    ctx.clearRect(0, 0, width, height);

    const pad = 12;
    const x = (s: number) => pad + ((s - fromM) / (toM - fromM)) * (width - 2 * pad);
    const roadY = 58;

    // Tunnel
    const { tunnel_start_m, tunnel_end_m } = run.road;
    ctx.fillStyle = "#d1d5db";
    ctx.fillRect(x(tunnel_start_m), roadY - 14, x(tunnel_end_m) - x(tunnel_start_m), 28);
    // Road
    ctx.strokeStyle = "#6b7280";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(x(Math.max(0, fromM)), roadY);
    ctx.lineTo(x(Math.min(run.road.length_m, toM)), roadY);
    ctx.stroke();

    // GPS fixes from the last 5 s
    const t = run.t_s[frame];
    ctx.fillStyle = GPS_COLOR;
    for (const p of run.gps) {
      if (p.t_s <= t && p.t_s > t - 5) dot(ctx, x(p.s_m), roadY, 2.5);
    }

    // Estimates: a marker above the road, with a stem down to it
    run.estimates.forEach((track, i) => {
      const s = track.s_m[frame];
      if (s == null) return;
      const top = 14 + i * 12;
      ctx.strokeStyle = ctx.fillStyle = estimatorColor(track.estimator);
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.moveTo(x(s), top);
      ctx.lineTo(x(s), roadY);
      ctx.stroke();
      dot(ctx, x(s), top, 4);
    });

    // The true car, on the road
    ctx.fillStyle = TRUTH_COLOR;
    dot(ctx, x(run.truth_s_m[frame]), roadY, 6);

    ctx.fillStyle = "#6b7280";
    ctx.font = "11px system-ui";
    ctx.fillText(label, pad, height - 4);
  }, [run, frame, fromM, toM, label]);

  return <canvas ref={ref} className="strip" style={{ height: 90 }} />;
}

function dot(ctx: CanvasRenderingContext2D, x: number, y: number, r: number) {
  ctx.beginPath();
  ctx.arc(x, y, r, 0, 2 * Math.PI);
  ctx.fill();
}
