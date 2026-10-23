import pytest
from conftest import SCENARIOS, scenario_run
from pydantic import ValidationError

from tunnelsim.run import run_scenario
from tunnelsim.scenario import Scenario, load_scenarios, piece_choices, save_scenario


def test_there_are_eight_test_scenarios_with_distinct_seeds():
    assert len(SCENARIOS) == 8
    assert len({s.seed for s in SCENARIOS}) == 8


@pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda s: s.name)
def test_every_test_scenario_runs_and_baseline_recovers_once_gps_settles(scenario):
    run = scenario_run(scenario.name)
    baseline = run.estimates[0]
    left_at = next(t for t, s in zip(run.t_s, run.truth_s_m) if s > run.tunnels[-1].end_m)
    # Once GPS has settled (first fix, biased fixes, converging), the baseline is back on the car.
    settled = [abs(e) for t, e in zip(run.t_s, baseline.error_m) if e is not None and t > left_at + 10]
    assert max(settled) < 20
    assert baseline.path[-1] == run.path


def test_same_seed_same_run_and_new_seed_new_run():
    a = SCENARIOS[0]
    assert run_scenario(a) == run_scenario(a)
    assert run_scenario(a).truth_s_m != run_scenario(a.model_copy(update={"seed": 99})).truth_s_m


def test_route_must_name_an_exit_on_the_road():
    with pytest.raises(ValidationError):
        Scenario.model_validate({"name": "t", "seed": 1, "route": {"planned_exit": "Exit A"}})


def test_a_saved_scenario_loads_back_the_same(tmp_path):
    edited = SCENARIOS[3].model_copy(update={"name": "Fork, but stop-and-go!", "seed": 42})
    path = save_scenario(edited, tmp_path)
    assert path.name == "fork-but-stop-and-go.json"
    assert load_scenarios(tmp_path) == [edited]
    save_scenario(edited.model_copy(update={"seed": 43}), tmp_path)  # same name: replaced
    assert [s.seed for s in load_scenarios(tmp_path)] == [43]


def test_the_editor_can_switch_every_piece_to_any_kind_with_its_defaults():
    choices = piece_choices()
    for road in choices.road.values():
        for speed in choices.speed.values():
            Scenario.model_validate({"name": "t", "seed": 1, "road": road, "speed": speed,
                                     "mounting": choices.mounting["loose"], "add_ons": choices.add_ons})
    assert choices.exits["fork"] == ["Fork right"] and choices.exits["straight"] == []
