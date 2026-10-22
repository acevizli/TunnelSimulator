import type { Run } from "./api";
import { TRUTH_COLOR, estimatorColor } from "./colors";

type Props = { run: Run; frame: number };
type Row = { t: number; who: string; said: string; really: string };

// What the driver hears from each estimator (exit callouts, missed exit), next to where the car really was.
// Rows still ahead of the replay are greyed out.
export default function Events({ run, frame }: Props) {
  const exit = run.scenario.route.planned_exit;
  if (!exit) return null;
  const now = run.t_s[frame];

  const rows: Row[] = [];
  if (run.missed_exit_t_s != null) {
    rows.push({ t: run.missed_exit_t_s, who: "ground truth", said: "", really: `the car passes ${exit} without taking it` });
  }
  for (const e of run.estimates) {
    for (const c of e.callouts) {
      rows.push({ t: c.t_s, who: e.estimator, said: `"${exit} in ${c.distance_m} m"`, really: calloutTruth(c.distance_m, c.truth_to_exit_m) });
    }
    const m = e.missed_exit_call;
    if (m) {
      const really = run.missed_exit_t_s == null
        ? "false alarm: the car took the exit"
        : `the car was ${m.truth_past_split_m.toFixed(0)} m past the split, ${(m.t_s - run.missed_exit_t_s).toFixed(1)} s after it got there`;
      rows.push({ t: m.t_s, who: e.estimator, said: `"You missed ${exit}"`, really });
    }
  }
  rows.sort((a, b) => a.t - b.t);

  return (
    <section className="panel">
      <h2>What the driver hears</h2>
      <table>
        <thead><tr><th>time</th><th>from</th><th>says</th><th>where the car really was</th></tr></thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i} className={r.t > now ? "future" : ""}>
              <td>{r.t.toFixed(1)} s</td>
              <td><i className="dot" style={{ background: r.who === "ground truth" ? TRUTH_COLOR : estimatorColor(r.who) }} /> {r.who}</td>
              <td>{r.said}</td>
              <td>{r.really}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

function calloutTruth(announced: number, truthToExit: number): string {
  if (truthToExit < 0) return `already ${(-truthToExit).toFixed(0)} m past the exit`;
  const off = truthToExit - announced;
  const timing = Math.abs(off) < 0.5 ? "on time" : off > 0 ? `${off.toFixed(0)} m early` : `${(-off).toFixed(0)} m late`;
  return `${truthToExit.toFixed(0)} m from the exit (${timing})`;
}
