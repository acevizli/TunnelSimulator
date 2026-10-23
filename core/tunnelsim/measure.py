"""The measurement command: every test scenario over many seeds, written to Markdown.

    uv run tunnelsim-measure                          # 8 test scenarios x 20 seeds -> results/measurements.md
    uv run tunnelsim-measure --seeds 5 --out quick.md

Seed k of a scenario is the scenario's own seed + k, so the first one is the
seed its file fixes. Like a test suite it shows nothing on screen; unlike one
it grades nothing. It reports what happened, and names the worst seed of every
metric so that run can be opened in the replay.
"""

import argparse
import sys
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

from tunnelsim.metrics import MEANINGS, EstimatorMetrics, Metric, measure
from tunnelsim.run import run_scenario
from tunnelsim.scenario import Scenario, load_scenarios

REPO = Path(__file__).parents[2]
HEADLINE = "largest error inside"

Measured = tuple[Scenario, list[EstimatorMetrics]]  # one run: the scenario with its seed, and what was measured


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--seeds", type=int, default=20, help="seeds per scenario (default 20)")
    parser.add_argument("--scenarios", type=Path, default=REPO / "scenarios", help="folder of scenario files")
    parser.add_argument("--out", type=Path, default=REPO / "results" / "measurements.md")
    args = parser.parse_args(argv)

    runs = [s.model_copy(update={"seed": s.seed + k}) for s in load_scenarios(args.scenarios) for k in range(args.seeds)]
    measured = []
    with ProcessPoolExecutor() as pool:
        for n, result in enumerate(pool.map(_measure_one, runs), 1):
            measured.append(result)
            print(f"\rmeasured {n}/{len(runs)} runs", end="", file=sys.stderr)
    print(file=sys.stderr)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(report(measured, args.seeds))
    print(f"wrote {args.out}", file=sys.stderr)


def _measure_one(scenario: Scenario) -> Measured:
    return scenario, measure(run_scenario(scenario))


def report(measured: list[Measured], seeds: int) -> str:
    """The Markdown report: what the metrics mean, a summary table, then one detail table per scenario."""
    # scenario -> metric -> estimator -> every seed's value
    table: dict[str, dict[str, dict[str, list[tuple[int, Metric]]]]] = defaultdict(lambda: defaultdict(dict))
    descriptions = {}
    for scenario, per_estimator in measured:
        descriptions[scenario.name] = scenario.description
        for em in per_estimator:
            for m in em.metrics:
                table[scenario.name][m.name].setdefault(em.estimator, []).append((scenario.seed, m))
    estimators = list(dict.fromkeys(em.estimator for _, per in measured for em in per))

    lines = [
        "# Measurements",
        "",
        f"{len(table)} scenarios × {seeds} seeds (seed k is the scenario's own seed + k), every estimator fed the "
        "same sensor data. Nothing here is graded: these are measurements, not pass/fail.",
        "",
        "Each cell is the median over the seeds, then the 95th percentile: 1 run in 20 is worse than that. For "
        "honesty, where lower is worse, it is the 5th percentile instead. \"never\" means it never happened "
        "(no recovery, no callout, no decision). Worst runs name their seed, to open in the replay.",
        "",
        "Phases: before the tunnel, entering (its first 200 m), inside, stopped, exiting (200 m either side of "
        "the end), between tunnels, after the tunnel.",
        "",
        "## What each metric means",
        "",
        *[f"- **{name}**: {meaning}" for name, meaning in MEANINGS.items()],
        "",
        f"## Summary: {HEADLINE}",
        "",
        "| Scenario | " + " | ".join(estimators) + " |",
        "|---|" + "---|" * len(estimators),
    ]
    for name, metrics in table.items():
        cells = []
        for est in estimators:
            values = metrics[HEADLINE].get(est)
            if values is None:
                cells.append("–")
                continue
            median, tail, (seed, worst) = _spread(values)
            cells.append(f"{median} / {tail} (worst {_fmt(worst.value, worst.unit)}, seed {seed})")
        lines.append(f"| {name} | " + " | ".join(cells) + " |")

    for name, metrics in table.items():
        lines += ["", f"## {name}", "", descriptions[name], "",
                  "| Metric | Estimator | Median | 95th percentile | Worst | Worst run |",
                  "|---|---|---|---|---|---|"]
        for metric in sorted(metrics, key=_meaning_order):
            for est, values in metrics[metric].items():
                lines.append(f"| {metric} | {est} | " + " | ".join(_row(values)) + " |")
    return "\n".join(lines) + "\n"


def _meaning_order(metric: str) -> int:
    """Metrics in the order MEANINGS lists them; the callouts share one entry there."""
    return next(i for i, name in enumerate(MEANINGS)
                if name == metric or (name.startswith("callout") and metric.startswith("callout")))


def _row(values: list[tuple[int, Metric]]) -> list[str]:
    median, tail, (seed, worst) = _spread(values)
    if worst.unit == "runs":
        happened = sum(1 for _, m in values if m.value)
        return ["", "", f"{happened} of {len(values)} runs", _where(seed, worst) if happened else ""]
    return [median, tail, _fmt(worst.value, worst.unit), _where(seed, worst)]


def _spread(values: list[tuple[int, Metric]]) -> tuple[str, str, tuple[int, Metric]]:
    """Median, the bad-end percentile and the worst run, formatted."""
    unit, worse = values[0][1].unit, values[0][1].worse
    badness = np.array([_badness(m) for _, m in values])
    median, tail = np.percentile(badness, [50, 95], method="nearest")

    def shown(b: float) -> str:
        return _fmt(None if b == np.inf else (b if worse == "higher" else -b), unit)

    return shown(median), shown(tail), max(values, key=lambda v: _badness(v[1]))


def _badness(m: Metric) -> float:
    """Bigger is worse, whichever way the metric points; never happening is the worst."""
    if m.value is None:
        return np.inf
    return m.value if m.worse == "higher" else -m.value


def _fmt(value: float | None, unit: str) -> str:
    if value is None:
        return "never"
    digits = 1 if unit == "s" or abs(value) < 10 else 0
    return f"{value:.{digits}f} {unit}"


def _where(seed: int, m: Metric) -> str:
    if m.at is None:
        return f"seed {seed}"
    note = f"{m.note}, " if m.note else ""
    return f"seed {seed}: {note}{m.at.s_m:.0f} m along, t = {m.at.t_s:.1f} s, {m.at.phase}"


if __name__ == "__main__":
    main()
