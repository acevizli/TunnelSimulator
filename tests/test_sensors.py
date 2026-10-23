import numpy as np

from tunnelsim.scenario import Scenario, build_road
from tunnelsim.sensors.baro import pressure_to_height
from tunnelsim.sensors.mounting import car_to_phone
from tunnelsim.sensors.simulated import record_drive
from tunnelsim.sensors.specs import G
from tunnelsim.truth import simulate_truth


def drive(**pieces):
    scenario = Scenario.model_validate({"name": "test", "seed": 3, **pieces})
    road = build_road(scenario)
    truth = simulate_truth(scenario.speed, road.path(scenario.driven_exit), np.random.default_rng(3))
    return truth, record_drive(truth, scenario.mounting, scenario.gps, scenario.add_ons, road, scenario.seed)


def test_mount_angles_turn_gravity_onto_the_expected_phone_axis():
    up = np.array([0, 0, G])
    assert np.allclose(car_to_phone([0, 0, 0]) @ up, [0, 0, G])  # flat, screen up
    assert np.allclose(car_to_phone([0, 90, 0]) @ up, [0, G, 0])  # upright, facing the driver
    forward = np.array([1.0, 0, 0])
    assert np.allclose(car_to_phone([0, 0, 0]) @ forward, [0, 1, 0])  # top of a flat phone points forward


def test_accelerometer_reads_gravity_plus_errors():
    truth, rec = drive()
    magnitude = np.linalg.norm(rec.imu.accel.mean(axis=0))
    assert abs(magnitude - G) < 0.8  # turn-on biases are ~0.2 m/s² per axis


def test_gyroscope_sees_the_spiral_turn_rate():
    truth, rec = drive(road={"kind": "spiral"})
    in_spiral = np.abs(truth.yaw_rate_rps) > 0.1
    measured = np.linalg.norm(rec.imu.gyro[in_spiral].mean(axis=0))
    assert abs(measured - truth.yaw_rate_rps[in_spiral].mean()) < 0.02


def test_loose_phone_shift_shows_as_a_burst_of_rotation():
    truth, rec = drive(mounting={"kind": "loose"})
    rate = np.degrees(np.linalg.norm(rec.imu.gyro, axis=1))
    shifting = np.abs(np.diff(rec.mount_angles_deg, axis=0, prepend=rec.mount_angles_deg[:1])).sum(axis=1) > 0
    assert rate[shifting].mean() > 30
    assert np.median(rate[~shifting]) < 3


def test_road_vibration_almost_vanishes_when_stopped():
    truth, rec = drive(speed={"kind": "full_stop"})
    vertical = rec.imu.accel @ car_to_phone([0, 70, 5])[:, 2]  # back to the car's vertical axis
    stopped, moving = truth.v_mps < 0.05, truth.v_mps > 15
    assert vertical[stopped].std() < vertical[moving].std() / 4


def test_barometer_follows_the_climb():
    truth, rec = drive(road={"kind": "spiral"})
    height = pressure_to_height(rec.baro.pressure_pa, rec.baro.pressure_pa[:25].mean())
    true_height = np.interp(rec.baro.t_s, truth.t_s, truth.z_m)
    assert np.abs(height - true_height).max() < 3


def test_gps_phases_around_a_tunnel():
    truth, rec = drive()
    [span] = truth.path.tunnel_spans()
    fixes, phases = rec.gnss.fixes, rec.gnss.phases
    s_at = [float(np.interp(f.t_s, truth.t_s, truth.s_m)) for f in fixes]
    deep = [p for p, s in zip(phases, s_at) if span.start_m + 150 < s < span.end_m]
    assert deep == []
    assert phases.count("coast") == 3
    assert phases.count("exit_bias") == 2
    first_after = next(f for f, s in zip(fixes, s_at) if s > span.end_m)
    left_at = float(np.interp(span.end_m, truth.s_m, truth.t_s))
    assert first_after.t_s - left_at >= 1.0


def test_exit_bias_pulls_fixes_along_the_road():
    truth, rec = drive()
    for fix, phase in zip(rec.gnss.fixes, rec.gnss.phases):
        if phase == "exit_bias":
            s = truth.path.project(fix.x_m, fix.y_m)[0]
            true_s = float(np.interp(fix.t_s, truth.t_s, truth.s_m))
            assert 15 < abs(s - true_s) < 45


def test_clean_gps_just_cuts_out_in_the_tunnel():
    truth, rec = drive(gps={"clean": True})
    assert set(rec.gnss.phases) == {"open"}
    in_tunnel = [truth.path.in_tunnel(np.interp(f.t_s, truth.t_s, truth.s_m)) for f in rec.gnss.fixes]
    assert not any(in_tunnel)
