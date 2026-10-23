"""The simulated phone: everything it records on one drive, served as a sensor source."""

from dataclasses import dataclass

import numpy as np

from tunnelsim.road import Road
from tunnelsim.sensors.addons import AddOns, place_beacons, simulate_beacons, simulate_vehicle_speed
from tunnelsim.sensors.baro import BaroReadings, simulate_baro
from tunnelsim.sensors.gnss import GnssReadings, GpsSpec, simulate_gnss
from tunnelsim.sensors.imu import ImuReadings, simulate_imu
from tunnelsim.sensors.mag import MagReadings, simulate_mag
from tunnelsim.sensors.mounting import FixedMount, LooseMount, mount_angles_over_time, mount_matrices
from tunnelsim.sensors.source import (AccelSample, BaroSample, BeaconSample, GyroSample, MagSample, Sample,
                                     VehicleSpeedSample)
from tunnelsim.truth import Truth


@dataclass
class Recording:
    imu: ImuReadings
    baro: BaroReadings
    mag: MagReadings
    gnss: GnssReadings
    mount_angles_deg: np.ndarray  # (n, 3) the phone's true roll, pitch, yaw in the car
    vehicle_speed: list[VehicleSpeedSample]  # add-ons: empty when off
    beacons: list[BeaconSample]

    def samples(self) -> list[Sample]:
        """Every reading as a sample, in time order."""
        imu, baro, mag = self.imu, self.baro, self.mag
        samples: list[Sample] = []
        samples += [AccelSample(t, *a) for t, a in zip(imu.t_s.tolist(), imu.accel.tolist())]
        samples += [GyroSample(t, *w) for t, w in zip(imu.t_s.tolist(), imu.gyro.tolist())]
        samples += [MagSample(t, *f) for t, f in zip(mag.t_s.tolist(), mag.field_ut.tolist())]
        samples += [BaroSample(t, p) for t, p in zip(baro.t_s.tolist(), baro.pressure_pa.tolist())]
        samples += self.gnss.fixes
        samples += self.vehicle_speed + self.beacons
        return sorted(samples, key=lambda sample: sample.t_s)


def record_drive(truth: Truth, mounting: FixedMount | LooseMount, gps: GpsSpec, add_ons: AddOns, road: Road,
                 seed: int) -> Recording:
    """Simulate every sensor. Each sensor draws from its own random stream, so changing
    one sensor's settings, or switching an add-on on, never changes another sensor's noise."""
    streams = np.random.SeedSequence(seed).spawn(6)
    imu_rng, baro_rng, mag_rng, gnss_rng, speed_rng, beacon_rng = (np.random.default_rng(s) for s in streams)
    spans = truth.path.tunnel_spans()
    tunnel_times = (float(np.interp(spans[0].start_m, truth.s_m, truth.t_s)),
                    float(np.interp(spans[-1].end_m, truth.s_m, truth.t_s)))
    angles = mount_angles_over_time(mounting, truth.t_s, tunnel_times)
    matrices = mount_matrices(angles)
    return Recording(
        imu=simulate_imu(truth, matrices, imu_rng),
        baro=simulate_baro(truth, baro_rng),
        mag=simulate_mag(truth, matrices, mag_rng),
        gnss=simulate_gnss(truth, gps, gnss_rng),
        mount_angles_deg=angles,
        vehicle_speed=[] if add_ons.vehicle_speed is None else
        simulate_vehicle_speed(truth, add_ons.vehicle_speed, speed_rng),
        beacons=[] if add_ons.beacons is None else
        simulate_beacons(truth, place_beacons(road, add_ons.beacons.spacing_m), add_ons.beacons, road, beacon_rng),
    )


class SimulatedSource:
    def __init__(self, samples: list[Sample]):
        self._samples = samples
        self._next = 0

    def read(self, until_t_s: float) -> list[Sample]:
        start = self._next
        while self._next < len(self._samples) and self._samples[self._next].t_s <= until_t_s:
            self._next += 1
        return self._samples[start : self._next]
