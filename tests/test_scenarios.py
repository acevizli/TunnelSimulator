from pathlib import Path

import pytest
from pydantic import ValidationError

from tunnelsim.run import run_scenario
from tunnelsim.scenario import Scenario, load_scenarios

SCENARIOS = load_scenarios(Path(__file__).parents[1] / "scenarios")


def test_there_are_eight_test_scenarios_with_distinct_seeds():
    assert len(SCENARIOS) == 8
    assert len({s.seed for s in SCENARIOS}) == 8


@pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda s: s.name)
def test_every_test_scenario_runs_and_baseline_recovers_after_the_tunnel(scenario):
    run = run_scenario(scenario)
    baseline = run.estimates[0]
    last_exit = run.tunnels[-1].end_m
    after = [abs(e) for s, e in zip(run.truth_s_m, baseline.error_m) if e is not None and s > last_exit + 30]
    assert max(after) < 20
    assert baseline.path[-1] == run.path


def test_same_seed_same_run_and_new_seed_new_run():
    a = SCENARIOS[0]
    assert run_scenario(a) == run_scenario(a)
    assert run_scenario(a).truth_s_m != run_scenario(a.model_copy(update={"seed": 99})).truth_s_m


def test_route_must_name_an_exit_on_the_road():
    with pytest.raises(ValidationError):
        Scenario.model_validate({"name": "t", "seed": 1, "route": {"planned_exit": "Exit A"}})
