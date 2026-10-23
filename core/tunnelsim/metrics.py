"""Measuring one run: how well each estimator did, and where it did worst.

Every metric is reported and none is graded: no thresholds, no pass/fail.
Each is one number per estimator per run. Most also keep the moment it was
worst (where the car really was, when, and in which phase), so it can be found
again in the replay. MEANINGS below says what each one measures.

A value of None means the thing never happened: the estimate never recovered,
a callout was never made, the branch was never settled. A metric that doesn't
apply to a run (callouts on a route without an exit) is left out.
"""

from typing import Literal

import numpy as np
from pydantic import BaseModel

from tunnelsim.callouts import BAND_SIGMAS
from tunnelsim.road import MAIN, Span
from tunnelsim.run import OUTPUT_HZ, EstimateTrack, Run

RECOVERED_M = 10  # within this of the truth counts as a good position again
EDGE_M = 200  # the first and last stretch of a tunnel count as entering and exiting
STOPPED_MPS = 0.5

MEANINGS = {
    "largest error inside": "the largest along-track error while the car is in a tunnel",
    "largest error inside, % of tunnel": "the same, as a share of the total tunnel length",
    "error at the exit": "the along-track error as the car leaves the last tunnel",
    "honesty": "share of the time in the tunnel that the car is inside the uncertainty band; about 95% is honest, "
               "lower means the band is too narrow, 100% can mean it is wider than it needs to be",
    "recovery after the exit": f"seconds after the last tunnel until the estimate is within {RECOVERED_M} m "
                               "of the car and stays there",
    "largest jump": "the largest sudden move of the shown position in one tick, beyond the car's own motion",
    "callout <d> m, late by": "how far past the announced point the car already was when \"exit in <d> m\" "
                              "was said; negative = early",
    "branch decided": "how far past a split the car was when the estimate settled on the branch the car took; "
                      "negative = before the car got there (the estimate was ahead)",
    "on the wrong branch": "seconds the estimate was shown on a branch the car isn't driving",
    "missed exit called": "how far past the split the car was when the app said the exit was missed",
    "false missed exit": "runs where the app said the exit was missed although the car took it",
}


class Moment(BaseModel):
    """Where the car really was when something happened."""

    t_s: float
    s_m: float
    phase: str


class Metric(BaseModel):
    name: str
    unit: str  # "runs" for an event that either happened in a run or didn't
    value: float | None  # None: it never happened
    worse: Literal["higher", "lower"] = "higher"
    at: Moment | None = None  # when it was worst in this run
    note: str = ""


class EstimatorMetrics(BaseModel):
    estimator: str
    metrics: list[Metric]


def measure(run: Run) -> list[EstimatorMetrics]:
    """Every metric for every estimator in the run."""
    return [EstimatorMetrics(estimator=e.estimator, metrics=_measure(run, e)) for e in run.estimates]


def phase(s_m: float, v_mps: float, tunnels: list[Span]) -> str:
    """Which part of the drive the car is in, from its real position and speed."""
    if v_mps < STOPPED_MPS:
        return "stopped"
    for t in tunnels:
        if t.start_m <= s_m < t.start_m + EDGE_M:
            return "entering"
        if t.end_m - EDGE_M <= s_m < t.end_m + EDGE_M:
            return "exiting"
        if t.start_m <= s_m < t.end_m:
            return "inside"
    if s_m < tunnels[0].start_m:
        return "before the tunnel"
    if s_m >= tunnels[-1].end_m:
        return "after the tunnel"
    return "between tunnels"


def _measure(run: Run, e: EstimateTrack) -> list[Metric]:
    err = np.array([np.nan if v is None else v for v in e.error_m])
    truth = np.array(run.truth_s_m)
    inside = np.any([(t.start_m <= truth) & (truth < t.end_m) for t in run.tunnels], axis=0)
    exit_i = min(int(np.searchsorted(truth, run.tunnels[-1].end_m)), len(truth) - 1)
    return [
        *_along_track(run, err, inside, exit_i),
        *_honesty(run, e, err, inside),
        _recovery(run, err, exit_i),
        *_largest_jump(run, err),
        *_callouts(run, e),
        *_branches(run, e),
        *_missed_exit(run, e),
    ]


def _along_track(run: Run, err: np.ndarray, inside: np.ndarray, exit_i: int) -> list[Metric]:
    i = _argmax(np.where(inside, np.abs(err), np.nan))
    if i is None:
        return []
    largest = float(abs(err[i]))
    tunnel_m = sum(t.end_m - t.start_m for t in run.tunnels)
    return [
        Metric(name="largest error inside", unit="m", value=largest, at=_moment(run, i), note=_side(err[i])),
        Metric(name="largest error inside, % of tunnel", unit="%", value=100 * largest / tunnel_m, at=_moment(run, i)),
        Metric(name="error at the exit", unit="m", value=float(abs(err[exit_i])), at=_moment(run, exit_i),
               note=_side(err[exit_i])),
    ]


def _honesty(run: Run, e: EstimateTrack, err: np.ndarray, inside: np.ndarray) -> list[Metric]:
    """Only for estimators that report an uncertainty band."""
    band = BAND_SIGMAS * np.array([np.nan if s is None else s for s in e.sigma_m])
    ticks = inside & ~np.isnan(band) & ~np.isnan(err)
    if not ticks.any():
        return []
    times_band = np.abs(err) / band
    i = _argmax(np.where(ticks, times_band, np.nan))
    return [Metric(name="honesty", unit="%", value=100 * float(np.mean(times_band[ticks] <= 1)), worse="lower",
                   at=_moment(run, i), note=f"furthest out: error {times_band[i]:.1f}× the band")]


def _recovery(run: Run, err: np.ndarray, exit_i: int) -> Metric:
    off = ~(np.abs(err[exit_i:]) <= RECOVERED_M)  # no estimate counts as off
    if off[-1]:
        return Metric(name="recovery after the exit", unit="s", value=None)
    j = exit_i + (int(np.flatnonzero(off)[-1]) + 1 if off.any() else 0)
    return Metric(name="recovery after the exit", unit="s", value=run.t_s[j] - run.t_s[exit_i], at=_moment(run, j))


def _largest_jump(run: Run, err: np.ndarray) -> list[Metric]:
    jump = np.abs(np.diff(err))
    i = _argmax(jump)
    if i is None:
        return []
    return [Metric(name="largest jump", unit="m", value=float(jump[i]), at=_moment(run, i + 1))]


def _callouts(run: Run, e: EstimateTrack) -> list[Metric]:
    if run.scenario.route.planned_exit is None:
        return []
    made = {c.distance_m: c for c in e.callouts}
    found = []
    for d in sorted(run.scenario.route.callouts_m, reverse=True):
        name = f"callout {d:g} m, late by"
        c = made.get(d)
        if c is None:
            found.append(Metric(name=name, unit="m", value=None))
        else:
            found.append(Metric(name=name, unit="m", value=d - c.truth_to_exit_m, at=_moment(run, _tick(run, c.t_s))))
    return found


def _branches(run: Run, e: EstimateTrack) -> list[Metric]:
    """At every split the car drives past: when the estimator settled on the right side of it."""
    road = run.road
    others = [p for p in [MAIN] + [x.name for x in road.exits] if p != run.path]
    splits = sorted({road.split_m(p, run.path) for p in others} - {None})
    splits = [m for m in splits if run.truth_s_m[-1] > m]
    if not splits:
        return []

    decided = [_decided(run, e, m) for m in splits]
    worst = max(decided, key=lambda d: np.inf if d[0] is None else d[0])
    past_m, i, split = worst
    exit_name = next(x.name for x in road.exits if x.at_m == split)
    wrong = [j for j, w in enumerate(e.wrong_branch) if w]
    return [
        Metric(name="branch decided", unit="m", value=past_m, at=None if i is None else _moment(run, i),
               note=f"at the {exit_name} split"),
        Metric(name="on the wrong branch", unit="s", value=len(wrong) / OUTPUT_HZ,
               at=_moment(run, wrong[0]) if wrong else None, note="from its first moment there" if wrong else ""),
    ]


def _decided(run: Run, e: EstimateTrack, split: float) -> tuple[float | None, int | None, float]:
    """Metres past `split` the car was when the estimate got past it on the car's side and stayed there."""
    def agrees(path: str) -> bool:  # doesn't part from the car's path at this split
        return run.road.split_m(path, run.path) != split

    settled = [s is not None and s > split and agrees(p) and all(map(agrees, odds or {}))
               for s, p, odds in zip(e.s_m, e.path, e.branches)]
    if not settled[-1]:
        return None, None, split
    i = len(settled) - 1
    while i > 0 and settled[i - 1]:
        i -= 1
    return run.truth_s_m[i] - split, i, split


def _missed_exit(run: Run, e: EstimateTrack) -> list[Metric]:
    route = run.scenario.route
    if route.planned_exit is None:
        return []
    call = e.missed_exit_call
    at = None if call is None else _moment(run, _tick(run, call.t_s))
    if route.missed_exit:
        return [Metric(name="missed exit called", unit="m", value=None if call is None else call.truth_past_split_m,
                       at=at)]
    return [Metric(name="false missed exit", unit="runs", value=float(call is not None), at=at)]


def _moment(run: Run, i: int) -> Moment:
    return Moment(t_s=run.t_s[i], s_m=round(run.truth_s_m[i], 1),
                  phase=phase(run.truth_s_m[i], run.truth_v_mps[i], run.tunnels))


def _tick(run: Run, t_s: float) -> int:
    return min(int(np.searchsorted(run.t_s, t_s)), len(run.t_s) - 1)


def _argmax(values: np.ndarray) -> int | None:
    """Index of the largest value, ignoring gaps; None if there is nothing to compare."""
    return None if np.all(np.isnan(values)) else int(np.nanargmax(values))


def _side(error_m: float) -> str:
    return "ahead" if error_m > 0 else "behind"
