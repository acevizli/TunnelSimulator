import numpy as np
import pytest
from conftest import SCENARIOS, scenario_run

from tunnelsim.estimators.alignment import align
from tunnelsim.estimators.kalman import Kalman
from tunnelsim.estimators.landmarks import find_landmarks
from tunnelsim.road import MAIN
from tunnelsim.roads import SpiralRoad
from tunnelsim.scenario import build_road
from tunnelsim.sensors.mounting import car_to_phone
from tunnelsim.sensors.simulated import record_drive
from tunnelsim.truth import simulate_truth

MISSED_EXIT = "4 · Fork + missed exit"


def map_filter(run):
    return next(e for e in run.estimates if e.estimator == "map filter")


def in_tunnel(run) -> np.ndarray:
    truth = np.array(run.truth_s_m)
    return (truth >= run.tunnels[0].start_m) & (truth <= run.tunnels[-1].end_m)


def test_update_moves_the_belief_by_relative_trust_and_the_gate_drops_outliers():
    kf = Kalman(np.array([0.0]), np.array([[4.0]]))
    assert kf.update(10.0, 0.0, np.array([1.0]), r=4.0, gate=None)
    assert kf.x[0] == pytest.approx(5.0) and kf.P[0, 0] == pytest.approx(2.0)  # equal trust: halfway
    assert not kf.update(100.0, 5.0, np.array([1.0]), r=1.0, gate=3.0)
    assert kf.x[0] == pytest.approx(5.0)


def approach(name):
    """Phone readings and GPS fixes before the tunnel, and the true car forward in phone axes."""
    scenario = next(s for s in SCENARIOS if s.name == name)
    road = build_road(scenario)
    path = road.path(scenario.driven_exit)
    truth = simulate_truth(scenario.speed, path, np.random.default_rng(scenario.seed))
    rec = record_drive(truth, scenario.mounting, scenario.gps, scenario.seed)
    entered = float(np.interp(path.tunnel_spans()[0].start_m, truth.s_m, truth.t_s))
    before = rec.imu.t_s < entered
    fixes = [f for f in rec.gnss.fixes if f.t_s < entered]
    forward = car_to_phone(rec.mount_angles_deg[0])[:, 0]
    return rec.imu.t_s[before], rec.imu.accel[before], fixes, path, forward


def test_alignment_finds_forward_from_a_slowdown_and_assumes_the_screen_on_a_steady_drive():
    *data, path, forward = approach("3 · Two exits + slowdown")
    fitted = align(*data, path)
    assert fitted.from_motion
    assert np.degrees(np.arccos(fitted.matrix[0] @ forward)) < 3  # mostly the tilt the bias puts into "up"

    *data, path, forward = approach("1 · Straight + free flow")
    assumed = align(*data, path)
    assert not assumed.from_motion
    assert np.degrees(np.arccos(assumed.matrix[0] @ forward)) < 10  # the mount is turned 5°


def test_the_spiral_has_curve_and_grade_landmarks_where_it_starts():
    path = SpiralRoad().build(before_m=1000, after_m=500).path(MAIN)
    starts = [lm for lm in find_landmarks(path) if abs(lm.s_m - 1150) < 1]
    assert {lm.kind for lm in starts} == {"curve", "grade"}
    curve = next(lm for lm in starts if lm.kind == "curve")
    assert (curve.before, curve.after) == (0, pytest.approx(1 / 35))


@pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda s: s.name)
def test_map_filter_stays_close_and_its_band_mostly_covers_the_truth(scenario):
    run = scenario_run(scenario.name)
    mf, inside = map_filter(run), in_tunnel(run)
    error = np.abs(np.array(mf.error_m, dtype=float))[inside]
    band = 2 * np.array(mf.sigma_m, dtype=float)[inside]
    assert error.max() < 60
    assert np.mean(error <= band) > 0.75


@pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda s: s.name)
def test_map_filter_is_back_on_gps_soon_after_the_exit(scenario):
    run = scenario_run(scenario.name)
    left_at = next(t for t, s in zip(run.t_s, run.truth_s_m) if s > run.tunnels[-1].end_m)
    after = [abs(e) for t, e in zip(run.t_s, map_filter(run).error_m) if t > left_at + 10]
    assert max(after) < 10
    assert map_filter(run).path[-1] == run.path


def test_stop_detection_holds_the_speed_at_zero_while_stopped():
    run = scenario_run("2 · Straight 5 km + stop-and-go")
    stopped = (np.array(run.truth_v_mps) == 0) & in_tunnel(run)
    assert stopped.sum() > 100
    assert np.mean(np.array(map_filter(run).v_mps, dtype=float)[stopped] < 0.3) > 0.9


def test_an_estimate_on_the_wrong_branch_counts_its_distance_along_the_road():
    run = scenario_run(MISSED_EXIT)
    split = next(e.at_m for e in run.exits if e.planned)
    baseline = run.estimates[0]
    i = next(i for i, wrong in enumerate(baseline.wrong_branch) if wrong and run.truth_s_m[i] > split + 1000)
    # Baseline believes the route: it is on "Fork right" while the car stays on main.
    assert baseline.path[i] == "Fork right"
    expected = (baseline.s_m[i] - split) + (run.truth_s_m[i] - split)
    assert baseline.error_m[i] == pytest.approx(expected) and expected > 1500
