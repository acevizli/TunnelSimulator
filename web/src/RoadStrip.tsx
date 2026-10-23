import { useEffect, useRef } from "react";
import type { Run } from "./api";
import { BEACON_COLORS, GPS_COLOR, GPS_PHASE_COLORS, TRUTH_COLOR, bandColor, estimatorColor } from "./colors";

type Props = { run: Run; frame: number; fromM: number; toM: number; label: string };

// Draws the stretch of road [fromM, toM] with the tunnel, the true car and every estimate.
// An estimate on a branch the car isn't driving is drawn hollow: its distance is along that other branch.
export default function RoadStrip({ run, frame, fromM, toM, label }: Props) {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = ref.current!;
    const width = canvas.clientWidth;
    const height = 96;
    const dpr = window.devicePixelRatio || 1;
    canvas.width = width * dpr;
    canvas.height = height * dpr;
    const ctx = canvas.getContext("2d")!;
    ctx.scale(dpr, dpr);
    ctx.clearRect(0, 0, width, height);

    const pad = 12;
    const x = (s: number) => pad + ((s - fromM) / (toM - fromM)) * (width - 2 * pad);
    const roadY = 58;

    // Tunnels along the driven path
    ctx.fillStyle = "#d1d5db";
    for (const span of run.tunnels) {
      ctx.fillRect(x(span.start_m), roadY - 14, x(span.end_m) - x(span.start_m), 28);
    }
    // Road
    ctx.strokeStyle = "#6b7280";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(x(Math.max(0, fromM)), roadY);
    ctx.lineTo(x(Math.min(run.path_length_m, toM)), roadY);
    ctx.stroke();

    // Beacons (add-on): a tick on the tunnel's top edge, green once heard, red if dead
    const now = run.t_s[frame];
    for (const b of run.beacons) {
      if (b.s_m < fromM || b.s_m > toM) continue;
      const heard = b.heard_t_s != null && b.heard_t_s <= now;
      ctx.fillStyle = b.dead ? BEACON_COLORS.dead : heard ? BEACON_COLORS.heard : BEACON_COLORS.unheard;
      ctx.fillRect(x(b.s_m) - 1, roadY - 14, 2, 6);
    }

    // Exits: a short tick below the road; the planned one is labelled
    ctx.font = "11px system-ui";
    for (const exit of run.exits) {
      ctx.strokeStyle = ctx.fillStyle = exit.planned ? "#059669" : "#9ca3af";
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(x(exit.at_m), roadY);
      ctx.lineTo(x(exit.at_m) + 8, roadY + 20);
      ctx.stroke();
      ctx.fillText(exit.planned ? `${exit.name} (route)` : exit.name, x(exit.at_m) + 10, roadY + 26);
    }

    // GPS fixes from the last 5 s
    for (const p of run.gps) {
      if (p.t_s > now || p.t_s <= now - 5) continue;
      ctx.fillStyle = GPS_PHASE_COLORS[p.phase] ?? GPS_COLOR;
      dot(ctx, x(p.s_m), roadY, 3);
    }

    // Estimates: a marker above the road, with a stem down to it, inside its uncertainty band (±2σ)
    run.estimates.forEach((track, i) => {
      const s = track.s_m[frame];
      if (s == null) return;
      const top = 20 + i * 10;
      const sigma = track.sigma_m[frame];
      if (sigma != null) {
        ctx.fillStyle = bandColor(track.estimator);
        ctx.fillRect(x(s - 2 * sigma), top - 4, x(s + 2 * sigma) - x(s - 2 * sigma), 8);
      }
      ctx.strokeStyle = ctx.fillStyle = estimatorColor(track.estimator);
      ctx.lineWidth = 1.5;
      const wrong = track.wrong_branch[frame];
      ctx.setLineDash(wrong ? [3, 3] : []);
      ctx.beginPath();
      ctx.moveTo(x(s), top);
      ctx.lineTo(x(s), roadY);
      ctx.stroke();
      ctx.setLineDash([]);
      if (wrong) {
        ctx.fillStyle = "#fff";
        dot(ctx, x(s), top, 4);
        ctx.beginPath();
        ctx.arc(x(s), top, 4, 0, 2 * Math.PI);
        ctx.stroke();
      } else {
        dot(ctx, x(s), top, 4);
      }
    });

    // The true car, on the road
    ctx.fillStyle = TRUTH_COLOR;
    dot(ctx, x(run.truth_s_m[frame]), roadY, 6);

    ctx.fillStyle = "#6b7280";
    ctx.fillText(label, pad, 10);
  }, [run, frame, fromM, toM, label]);

  return <canvas ref={ref} className="strip" style={{ height: 96 }} />;
}

function dot(ctx: CanvasRenderingContext2D, x: number, y: number, r: number) {
  ctx.beginPath();
  ctx.arc(x, y, r, 0, 2 * Math.PI);
  ctx.fill();
}
