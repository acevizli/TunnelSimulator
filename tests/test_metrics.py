from conftest import SCENARIOS, scenario_run

from tunnelsim.measure import report
from tunnelsim.metrics import MEANINGS, measure, phase
from tunnelsim.road import Span

MISSED_EXIT = "4 · Fork + missed exit"
TUNNELS = [Span(1000, 3000)]


def metrics(run, estimator):
    found = next(em for em in measure(run) if em.estimator == estimator)
    return {m.name: m for m in found.metrics}


def test_phases_follow_the_car_through_the_tunnel():
    assert phase(500, 20, TUNNELS) == "before the tunnel"
    assert phase(1100, 20, TUNNELS) == "entering"
    assert phase(2000, 20, TUNNELS) == "inside"
    assert phase(2000, 0.0, TUNNELS) == "stopped"
    assert phase(2900, 20, TUNNELS) == "exiting"
    assert phase(3100, 20, TUNNELS) == "exiting"
    assert phase(3300, 20, TUNNELS) == "after the tunnel"
    assert phase(3300, 20, TUNNELS + [Span(4000, 5000)]) == "between tunnels"


def test_largest_error_inside_is_the_largest_error_while_the_car_is_in_a_tunnel():
    run = scenario_run(SCENARIOS[0].name)
    track = next(e for e in run.estimates if e.estimator == "map filter")
    tunnel = run.tunnels[0]
    inside = [abs(err) for err, s in zip(track.error_m, run.truth_s_m)
              if err is not None and tunnel.start_m <= s < tunnel.end_m]
    found = metrics(run, "map filter")["largest error inside"]
    assert found.value == max(inside)
    assert found.at.phase in ("entering", "inside", "stopped", "exiting")


def test_honesty_is_only_measured_for_estimators_with_a_band():
    run = scenario_run(SCENARIOS[0].name)
    assert "honesty" not in metrics(run, "baseline")
    assert 0 <= metrics(run, "map filter")["honesty"].value <= 100


def test_callout_lateness_is_where_the_car_really_was_against_what_was_announced():
    run = scenario_run(MISSED_EXIT)
    track = next(e for e in run.estimates if e.estimator == "map filter")
    found = metrics(run, "map filter")
    for c in track.callouts:
        assert found[f"callout {c.distance_m:g} m, late by"].value == c.distance_m - c.truth_to_exit_m


def test_on_the_missed_exit_the_map_filter_decides_within_metres_and_the_baseline_only_after_the_tunnel():
    run = scenario_run(MISSED_EXIT)
    split = next(e.at_m for e in run.exits if e.planned)
    mf, baseline = metrics(run, "map filter"), metrics(run, "baseline")
    assert mf["branch decided"].value < 20 and mf["missed exit called"].value < 20
    assert mf["on the wrong branch"].value < 1
    assert baseline["missed exit called"].value > run.tunnels[-1].end_m - split
    assert baseline["largest jump"].value > 1000  # it snaps back to the car when GPS returns
    assert "false missed exit" not in mf


def test_the_map_filter_recovers_at_the_exit_and_never_jumps_far():
    for scenario in SCENARIOS:
        mf = metrics(scenario_run(scenario.name), "map filter")
        assert mf["recovery after the exit"].value is not None
        assert mf["largest jump"].value < 30


def test_the_report_has_a_summary_row_and_a_detail_table_per_scenario():
    runs = [scenario_run(s.name) for s in SCENARIOS[:2]]
    text = report([(r.scenario, measure(r)) for r in runs], seeds=1)
    assert "## Summary: largest error inside" in text
    for r in runs:
        assert f"| {r.scenario.name} |" in text and f"## {r.scenario.name}" in text
    assert all(f"**{name}**" in text for name in MEANINGS)
    assert all("never" not in line for line in text.splitlines() if line.startswith("| largest error inside |"))
