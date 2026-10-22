"""Play one scenario from start to finish and collect everything the UI shows.

    scenario -> road -> ground truth -> sensor samples -> every estimator -> Run

All estimators read the same samples from one sensor source, so any
difference between them comes from the method, not from the noise.
"""

import numpy as np
from pydantic import BaseModel

from tunnelsim.estimators.baseline import Baseline
from tunnelsim.estimators.estimate import Estimate, Estimator
from tunnelsim.evaluation import along_track_error
from tunnelsim.road import Road
from tunnelsim.scenario import Scenario, build_road
from tunnelsim.sensors.gnss import simulate_gnss
from tunnelsim.sensors.simulated import SimulatedSource
from tunnelsim.truth import DT_S, simulate_truth

OUTPUT_HZ = 10  # how often the result records the state; sensors run faster


class GpsPoint(BaseModel):
    t_s: float
    s_m: float  # the fix projected onto the road


class EstimateTrack(BaseModel):
    estimator: str
    s_m: list[float | None]
    v_mps: list[float | None]
    sigma_m: list[float | None]
    error_m: list[float | None]


class Run(BaseModel):
    scenario: Scenario
    road: Road
    t_s: list[float]
    truth_s_m: list[float]
    truth_v_mps: list[float]
    gps: list[GpsPoint]
    estimates: list[EstimateTrack]


def run_scenario(scenario: Scenario) -> Run:
    rng = np.random.default_rng(scenario.seed)
    road = build_road(scenario)
    truth = simulate_truth(scenario, road, rng)
    fixes = simulate_gnss(truth, road, scenario.gps, rng)

    source = SimulatedSource(fixes)
    estimators: list[Estimator] = [Baseline(road)]
    history: dict[str, list[Estimate | None]] = {e.name: [] for e in estimators}

    ticks = range(0, len(truth.t_s), round(1 / (OUTPUT_HZ * DT_S)))
    for i in ticks:
        t = float(truth.t_s[i])
        for sample in source.read(t):
            for estimator in estimators:
                estimator.update(sample)
        for estimator in estimators:
            history[estimator.name].append(estimator.estimate(t))

    truth_s = [float(truth.s_m[i]) for i in ticks]
    return Run(
        scenario=scenario,
        road=road,
        t_s=[float(truth.t_s[i]) for i in ticks],
        truth_s_m=truth_s,
        truth_v_mps=[float(truth.v_mps[i]) for i in ticks],
        gps=[GpsPoint(t_s=f.t_s, s_m=road.project(f.x_m, f.y_m)) for f in fixes],
        estimates=[_track(name, estimates, truth_s) for name, estimates in history.items()],
    )


def _track(name: str, estimates: list[Estimate | None], truth_s_m: list[float]) -> EstimateTrack:
    return EstimateTrack(
        estimator=name,
        s_m=[None if e is None else e.s_m for e in estimates],
        v_mps=[None if e is None else e.v_mps for e in estimates],
        sigma_m=[None if e is None else e.sigma_m for e in estimates],
        error_m=along_track_error(estimates, truth_s_m),
    )
