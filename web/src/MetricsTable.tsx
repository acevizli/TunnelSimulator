import type { EstimatorMetrics } from "./api";
import { estimatorColor } from "./colors";

type Props = { metrics: EstimatorMetrics[]; jumpTo: (t_s: number) => void };

// Every metric of this run, one column per estimator. A worst value links to that moment in the replay.
export default function MetricsTable({ metrics, jumpTo }: Props) {
  const names = [...new Set(metrics.flatMap((em) => em.metrics.map((m) => m.name)))];
  return (
    <table className="metrics">
      <thead>
        <tr>
          <th>metric (this seed)</th>
          {metrics.map((em) => (
            <th key={em.estimator}><i className="dot" style={{ background: estimatorColor(em.estimator) }} /> {em.estimator}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {names.map((name) => (
          <tr key={name}>
            <td>{name}</td>
            {metrics.map((em) => {
              const m = em.metrics.find((x) => x.name === name);
              if (!m) return <td key={em.estimator} className="na">–</td>;
              return (
                <td key={em.estimator}>
                  {m.value == null ? "never" : `${m.value.toFixed(1)} ${m.unit}`}
                  {m.at && (
                    <button className="jump" title={`${m.at.phase}, ${m.at.s_m.toFixed(0)} m along the road`}
                      onClick={() => jumpTo(m.at!.t_s)}>at {m.at.t_s.toFixed(0)} s ↗</button>
                  )}
                </td>
              );
            })}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
