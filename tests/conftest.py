from functools import cache
from pathlib import Path

from tunnelsim.run import Run, run_scenario
from tunnelsim.scenario import load_scenarios

SCENARIOS = load_scenarios(Path(__file__).parents[1] / "scenarios")


@cache
def scenario_run(name: str) -> Run:
    """Each test scenario's run, computed once per test session."""
    return run_scenario(next(s for s in SCENARIOS if s.name == name))
