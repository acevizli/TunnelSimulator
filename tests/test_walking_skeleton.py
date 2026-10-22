from tunnelsim.run import run_scenario
from tunnelsim.scenario import Scenario, build_road


def straight(seed=1, **road):
    return Scenario.model_validate({"name": "test", "seed": seed, "road": road})


def test_car_drives_the_whole_road():
    run = run_scenario(straight())
    assert run.truth_s_m[0] == 0
    assert run.truth_s_m[-1] >= run.road.length_m - 30  # last 10 Hz tick before the end


def test_tunnel_starts_after_the_open_road_before_it():
    road = build_road(straight(tunnel_length_m=1500, open_before_s=60))
    assert road.tunnel_start_m == 60 * 80 / 3.6
    assert abs(road.tunnel_length_m - 1500) < 1e-6


def test_no_gps_inside_the_tunnel():
    run = run_scenario(straight())
    inside = [p for p in run.gps if run.road.tunnel_start_m + 10 < p.s_m < run.road.tunnel_end_m - 10]
    assert inside == []


def test_baseline_follows_gps_outside_and_drifts_inside():
    run = run_scenario(straight())
    baseline = run.estimates[0]
    errors = [(s, e) for s, e in zip(run.truth_s_m, baseline.error_m) if e is not None]
    before = [abs(e) for s, e in errors if s < run.road.tunnel_start_m]
    inside = [abs(e) for s, e in errors if run.road.in_tunnel(s)]
    assert max(before) < 30
    assert max(inside) > max(before)


def test_same_seed_same_run_and_new_seed_new_run():
    assert run_scenario(straight(seed=7)) == run_scenario(straight(seed=7))
    assert run_scenario(straight(seed=7)).truth_s_m != run_scenario(straight(seed=8)).truth_s_m
