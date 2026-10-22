import numpy as np

from tunnelsim.run import run_scenario
from tunnelsim.scenario import Scenario, build_road
from tunnelsim.truth import MAX_LATERAL_MPS2, simulate_truth


def drive(**pieces):
    scenario = Scenario.model_validate({"name": "test", "seed": 1, **pieces})
    road = build_road(scenario)
    return simulate_truth(scenario.speed, road.path(scenario.driven_exit), np.random.default_rng(1)), road


def stopped_spells(truth, min_s=3.0):
    """Number of times the car stands still for at least min_s seconds."""
    still = truth.v_mps < 0.05
    edges = np.flatnonzero(np.diff(still.astype(int)) == 1)
    return sum(1 for i in edges if still[i + 1 : i + 1 + int(min_s / 0.01)].all())


def test_car_reaches_the_end_of_the_road():
    truth, road = drive()
    assert truth.s_m[-1] >= road.path().length_m - 1


def test_car_slows_for_the_spiral():
    truth, _ = drive(road={"kind": "spiral"}, speed={"kind": "free_flow", "speed_kmh": 80})
    lateral = truth.v_mps * np.abs(truth.yaw_rate_rps)
    assert lateral.max() <= MAX_LATERAL_MPS2 * 1.05


def test_stop_and_go_stops_repeatedly_inside_the_tunnel():
    truth, _ = drive(speed={"kind": "stop_and_go"})
    assert stopped_spells(truth) >= 5
    assert not (truth.v_mps[~truth.in_tunnel] < 1).any()


def test_full_stop_stands_still_for_the_set_time_mid_tunnel():
    truth, road = drive(speed={"kind": "full_stop", "stop_s": 60})
    still = truth.v_mps < 0.05
    assert 59 <= still.sum() * 0.01 <= 62
    [span] = road.path().tunnel_spans()
    mid = (span.start_m + span.end_m) / 2
    assert abs(truth.s_m[still].mean() - mid) < 20


def test_missed_exit_keeps_the_car_on_the_main_road():
    run = run_scenario(Scenario.model_validate({
        "name": "t", "seed": 1, "road": {"kind": "fork"},
        "route": {"planned_exit": "Fork right", "missed_exit": True},
    }))
    assert run.path == "main"
    assert [e.planned for e in run.exits] == [True]
