"""Play one scenario from start to finish and collect everything the UI shows.

    scenario -> road -> ground truth -> sensor samples -> every estimator -> Run

All estimators read the same samples from one sensor source, so any
difference between them comes from the method, not from the noise.
"""

import numpy as np
from pydantic import BaseModel

from tunnelsim.estimators.baseline import Baseline
from tunnelsim.estimators.estimate import Estimate, Estimator
from tunnelsim.estimators.map_filter import MapFilter
from tunnelsim.evaluation import along_track_error, on_wrong_branch
from tunnelsim.road import Path, Road, Span
from tunnelsim.scenario import Scenario, build_road
from tunnelsim.sensors.baro import pressure_to_height
from tunnelsim.sensors.simulated import Recording, SimulatedSource, record_drive
from tunnelsim.sensors.source import GnssFix
from tunnelsim.truth import DT_S, Truth, simulate_truth

OUTPUT_HZ = 10  # how often the result records the state; sensors run faster


class GpsPoint(BaseModel):
    t_s: float
    s_m: float  # the fix projected onto the driven path
    phase: str  # portal phase it came from (simulator knowledge, for display only)
    accuracy_m: float  # what the phone claimed


class SensorTraces(BaseModel):
    """What the phone recorded, averaged over each output tick so it can be plotted."""

    accel_mps2: list[list[float]]  # x, y, z series in phone axes
    gyro_dps: list[list[float]]  # degrees per second
    baro_height_m: list[float]  # height from the barometer, relative to the start
    mount_deg: list[list[float]]  # true roll, pitch, yaw of the phone in the car


class ExitMark(BaseModel):
    name: str
    at_m: float
    planned: bool  # the route says to take this exit


class EstimateTrack(BaseModel):
    estimator: str
    path: list[str | None]
    s_m: list[float | None]
    v_mps: list[float | None]
    sigma_m: list[float | None]
    error_m: list[float | None]
    wrong_branch: list[bool]  # shown on a branch the car isn't driving
    x_m: list[float | None]  # where the estimate puts the car on the map
    y_m: list[float | None]


class PathShape(BaseModel):
    """One path seen from above, every few metres, for the map view."""

    name: str
    x_m: list[float]
    y_m: list[float]
    tunnel: list[bool]


class Run(BaseModel):
    scenario: Scenario
    road: Road
    path: str  # the path the car really drove
    path_length_m: float
    tunnels: list[Span]  # along the driven path
    shapes: list[PathShape]
    exits: list[ExitMark]
    t_s: list[float]
    truth_s_m: list[float]
    truth_v_mps: list[float]
    truth_height_m: list[float]
    truth_x_m: list[float]
    truth_y_m: list[float]
    gps: list[GpsPoint]
    sensors: SensorTraces
    estimates: list[EstimateTrack]


def run_scenario(scenario: Scenario) -> Run:
    rng = np.random.default_rng(scenario.seed)
    road = build_road(scenario)
    driven = road.path(scenario.driven_exit)
    truth = simulate_truth(scenario.speed, driven, rng)
    recording = record_drive(truth, scenario.mounting, scenario.gps, scenario.seed)

    source = SimulatedSource(recording.samples())
    estimators: list[Estimator] = [Baseline(road, scenario.planned_path), MapFilter(road, scenario.planned_path)]
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
        path=driven.name,
        path_length_m=driven.length_m,
        tunnels=driven.tunnel_spans(),
        shapes=[_shape(p) for p in road.paths()],
        exits=[ExitMark(name=e.name, at_m=e.at_m, planned=e.name == scenario.route.planned_exit) for e in road.exits],
        t_s=[float(truth.t_s[i]) for i in ticks],
        truth_s_m=truth_s,
        truth_v_mps=[float(truth.v_mps[i]) for i in ticks],
        truth_height_m=[float(truth.z_m[i]) for i in ticks],
        truth_x_m=[round(float(truth.x_m[i]), 1) for i in ticks],
        truth_y_m=[round(float(truth.y_m[i]), 1) for i in ticks],
        gps=[
            GpsPoint(t_s=f.t_s, s_m=_on_path(driven, f, truth), phase=phase, accuracy_m=f.accuracy_m)
            for f, phase in zip(recording.gnss.fixes, recording.gnss.phases)
        ],
        sensors=_traces(recording, list(ticks)),
        estimates=[_track(name, estimates, truth_s, road, driven.name) for name, estimates in history.items()],
    )


def _track(name: str, estimates: list[Estimate | None], truth_s_m: list[float], road: Road,
           truth_path: str) -> EstimateTrack:
    paths = {p.name: p for p in road.paths()}

    def on_map(e: Estimate | None, table: str) -> float | None:
        return None if e is None else round(float(paths[e.path].lookup(getattr(paths[e.path], table), e.s_m)), 1)

    return EstimateTrack(
        estimator=name,
        path=[None if e is None else e.path for e in estimates],
        s_m=[None if e is None else e.s_m for e in estimates],
        v_mps=[None if e is None else e.v_mps for e in estimates],
        sigma_m=[None if e is None else e.sigma_m for e in estimates],
        error_m=[None if e is None else along_track_error(e, s, truth_path, road) for e, s in zip(estimates, truth_s_m)],
        wrong_branch=[e is not None and on_wrong_branch(e, truth_path, road) for e in estimates],
        x_m=[on_map(e, "x") for e in estimates],
        y_m=[on_map(e, "y") for e in estimates],
    )


def _shape(path: Path, every_m: int = 5) -> PathShape:
    return PathShape(
        name=path.name,
        x_m=np.round(path.x[::every_m], 1).tolist(),
        y_m=np.round(path.y[::every_m], 1).tolist(),
        tunnel=path.tunnel[::every_m].tolist(),
    )


def _on_path(path: Path, fix: GnssFix, truth: Truth) -> float:
    """Where a GPS fix lands on the driven path, for display."""
    near = float(np.interp(fix.t_s, truth.t_s, truth.s_m))
    return path.project(fix.x_m, fix.y_m, near_s=near)[0]


def _traces(recording: Recording, ticks: list[int]) -> SensorTraces:
    """Average the 100 Hz motion readings over each output tick; sample the barometer at it."""
    edges = ticks + [len(recording.imu.t_s)]

    def averaged(values: np.ndarray) -> list[list[float]]:
        means = np.array([values[a:b].mean(axis=0) for a, b in zip(edges[:-1], edges[1:])])
        return [np.round(means[:, k], 4).tolist() for k in range(values.shape[1])]

    baro = recording.baro
    height = pressure_to_height(baro.pressure_pa, reference_pa=float(baro.pressure_pa[:25].mean()))
    t_ticks = recording.imu.t_s[ticks]
    return SensorTraces(
        accel_mps2=averaged(recording.imu.accel),
        gyro_dps=averaged(np.degrees(recording.imu.gyro)),
        baro_height_m=np.round(np.interp(t_ticks, baro.t_s, height), 3).tolist(),
        mount_deg=[np.round(recording.mount_angles_deg[ticks, k], 2).tolist() for k in range(3)],
    )
