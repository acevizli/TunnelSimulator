import numpy as np
import pytest
from conftest import SCENARIOS, scenario_run

from tunnelsim.callouts import callouts, missed_exit_call
from tunnelsim.estimators.estimate import Estimate
from tunnelsim.road import MAIN, Exit, Road, Segment

MISSED_EXIT = "4 · Fork + missed exit"
WITH_EXITS = [s for s in SCENARIOS if s.road.exit_names()]
WITH_ROUTE_EXIT = [s for s in SCENARIOS if s.route.planned_exit]


def track(run, name):
    return next(e for e in run.estimates if e.estimator == name)


def at(run, t_s):
    return int(np.searchsorted(run.t_s, t_s))


def test_the_map_filter_notices_the_missed_exit_within_a_second_and_the_baseline_only_after_the_tunnel():
    run = scenario_run(MISSED_EXIT)
    split = next(e.at_m for e in run.exits if e.planned)
    mf, baseline = track(run, "map filter"), track(run, "baseline")
    assert mf.missed_exit_call.path == MAIN
    assert mf.missed_exit_call.t_s - run.missed_exit_t_s < 1.0
    assert sum(mf.wrong_branch) / 10 < 1.0  # seconds shown on the route's branch while the car is on main
    assert baseline.missed_exit_call.truth_past_split_m > run.tunnels[-1].end_m - split


def test_before_the_split_the_map_filter_shows_the_route_and_keeps_both_branches_open():
    run = scenario_run(MISSED_EXIT)
    mf = track(run, "map filter")
    i = at(run, run.missed_exit_t_s - 1.0)
    assert mf.branches[i] is not None and set(mf.branches[i]) == {MAIN, "Fork right"}
    assert mf.path[i] == "Fork right" and mf.branches[i]["Fork right"] > 0.5


@pytest.mark.parametrize("scenario", WITH_EXITS, ids=lambda s: s.name)
def test_the_map_filter_settles_on_the_branch_the_car_took_and_raises_no_false_alarm(scenario):
    run = scenario_run(scenario.name)
    mf = track(run, "map filter")
    inside = [i for i, s in enumerate(run.truth_s_m) if s <= run.tunnels[-1].end_m]
    assert mf.branches[inside[-1]] is None  # decided before the end of the tunnel
    assert mf.path[inside[-1]] == run.path
    if not scenario.route.missed_exit:
        assert mf.missed_exit_call is None


@pytest.mark.parametrize("scenario", WITH_ROUTE_EXIT, ids=lambda s: s.name)
def test_map_filter_callouts_come_on_time_or_a_little_early(scenario):
    made = track(scenario_run(scenario.name), "map filter").callouts
    assert [c.distance_m for c in made] == sorted(scenario.route.callouts_m, reverse=True)
    for c in made:
        assert c.distance_m - 5 <= c.truth_to_exit_m <= c.distance_m + 100  # 5 m: one output tick at speed


def test_the_baseline_calls_the_exit_after_the_car_has_passed_it_when_traffic_slows():
    made = track(scenario_run("3 · Two exits + slowdown"), "baseline").callouts
    assert all(c.truth_to_exit_m < 0 for c in made)


def test_a_callout_fires_on_the_cautious_edge_of_the_band():
    road = Road(main=[Segment(length_m=2000)], exits=[Exit(name="Exit", at_m=1000, branch=[Segment(length_m=500)])])
    t = [0.0, 1.0, 2.0]
    truth = [500.0, 550.0, 600.0]
    unsure = [Estimate(path="Exit", s_m=s, v_mps=20, sigma_m=25) for s in (500, 550, 600)]
    sure = [Estimate(path="Exit", s_m=s, v_mps=20, sigma_m=None) for s in (500, 550, 600)]
    # Exit in 400 m means s reaches 600; the unsure estimate's edge (s + 50) gets there a second sooner.
    assert [c.t_s for c in callouts(unsure, t, truth, road, "Exit", [400])] == [1.0]
    assert [c.t_s for c in callouts(sure, t, truth, road, "Exit", [400])] == [2.0]


def test_a_missed_exit_is_called_only_once_the_routes_branch_is_ruled_out():
    road = Road(main=[Segment(length_m=2000)], exits=[Exit(name="Exit", at_m=1000, branch=[Segment(length_m=500)])])
    unsure = Estimate(path=MAIN, s_m=1050, v_mps=20, sigma_m=5, branches={MAIN: 0.9, "Exit": 0.1})
    sure = Estimate(path=MAIN, s_m=1070, v_mps=20, sigma_m=5)
    call = missed_exit_call([unsure, sure], [0.0, 1.0], [1050.0, 1070.0], road, "Exit")
    assert call.t_s == 1.0 and call.truth_past_split_m == 70
