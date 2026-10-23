import numpy as np
from conftest import SCENARIOS, scenario_run

from tunnelsim.metrics import measure
from tunnelsim.road import MAIN
from tunnelsim.roads import ForkRoad
from tunnelsim.run import run_scenario
from tunnelsim.scenario import Scenario, build_road
from tunnelsim.sensors.addons import BeaconSpec, VehicleSpeedSpec, place_beacons, simulate_beacons, simulate_vehicle_speed
from tunnelsim.truth import simulate_truth

STOP_AND_GO = "2 · Straight 5 km + stop-and-go"
BEACONS = "8 · Straight 5 km + stop-and-go + beacons"
VEHICLE_SPEED = "7 · Long grade + speed change + vehicle speed"
MISSED_EXIT = "4 · Fork + missed exit"


def scenario(name, **add_ons):
    s = next(s for s in SCENARIOS if s.name == name)
    return Scenario.model_validate({**s.model_dump(), "add_ons": add_ons}) if add_ons else s


def drive(name):
    s = scenario(name)
    road = build_road(s)
    return road, simulate_truth(s.speed, road.path(s.driven_exit), np.random.default_rng(s.seed))


def metrics(run, estimator):
    found = next(em for em in measure(run) if em.estimator == estimator)
    return {m.name: m.value for m in found.metrics}


def test_the_car_reports_k_times_its_speed_plus_b_and_zero_when_standing():
    _, truth = drive(STOP_AND_GO)
    readings = simulate_vehicle_speed(truth, VehicleSpeedSpec(noise_mps=0), np.random.default_rng(0))
    true_v = np.interp([r.t_s for r in readings], truth.t_s, truth.v_mps)
    reported = np.array([r.speed_mps for r in readings])
    moving = true_v >= 0.5
    assert np.allclose(reported[moving], 1.03 * true_v[moving] + 0.3)
    assert np.all(reported[~moving] == 0) and (~moving).sum() > 100  # the stops


def test_beacons_run_every_35_m_through_the_tunnel_and_a_branch_has_its_own_past_the_split():
    road = ForkRoad().build(before_m=1000, after_m=500)
    beacons = place_beacons(road, 35)
    for tunnel in road.path(MAIN).tunnel_spans():  # this road has two tunnels
        inside = [b.s_m for b in beacons if b.path == MAIN and tunnel.start_m <= b.s_m < tunnel.end_m]
        assert inside[0] == tunnel.start_m and np.allclose(np.diff(inside), 35) and inside[-1] > tunnel.end_m - 35
    branch = road.exits[0]
    assert all(b.s_m > branch.at_m for b in beacons if b.path == branch.name)


def test_dead_beacons_never_answer_and_about_one_pass_in_twenty_goes_unheard():
    road, truth = drive(STOP_AND_GO)
    spec = BeaconSpec(dead=[{"start_m": 1000, "end_m": 2000}])
    beacons = place_beacons(road, spec.spacing_m)
    heard = simulate_beacons(truth, beacons, spec, road, np.random.default_rng(1))
    where = {b.id: b.s_m - truth.path.tunnel_spans()[0].start_m for b in beacons}
    assert not any(1000 <= where[h.beacon_id] < 2000 for h in heard)
    alive = sum(1 for s in where.values() if not 1000 <= s < 2000)
    assert 0.85 < len(heard) / alive < 1.0


def test_switching_an_add_on_on_changes_nothing_for_the_other_estimators():
    plain = scenario_run(STOP_AND_GO)
    with_both = run_scenario(scenario(STOP_AND_GO, vehicle_speed={}, beacons={}))
    assert [e.estimator for e in with_both.estimates] == [
        "baseline", "map filter", "map filter + vehicle speed", "map filter + beacons"]
    assert with_both.estimates[:2] == plain.estimates


def test_beacons_keep_the_long_stop_and_go_tunnel_within_metres():
    run = scenario_run(BEACONS)
    found = metrics(run, "map filter + beacons")
    assert found["largest error inside"] < 15 and found["error at the exit"] < 5
    assert found["largest error inside"] < metrics(run, "map filter")["largest error inside"]
    assert len(run.beacons) > 100 and sum(b.heard_t_s is not None for b in run.beacons) > 0.9 * len(run.beacons)


def test_vehicle_speed_learned_at_one_speed_still_helps_and_its_band_stays_honest():
    run = scenario_run(VEHICLE_SPEED)
    found = metrics(run, "map filter + vehicle speed")
    assert found["largest error inside"] < metrics(run, "map filter")["largest error inside"]
    assert found["honesty"] > 90
    assert run.sensors.vehicle_speed_mps and max(run.sensors.vehicle_speed_mps) > 100 / 3.6


def test_a_beacon_past_the_split_settles_the_branch():
    run = run_scenario(scenario(MISSED_EXIT, beacons={}))
    found = metrics(run, "map filter + beacons")
    assert found["branch decided"] < 50 and found["missed exit called"] < 50
    assert found["on the wrong branch"] < 1
