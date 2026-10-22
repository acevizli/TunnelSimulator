"""Simulated accelerometer and gyroscope, derived from ground truth.

1. What the car feels, in car axes (x forward, y left, z up):
     accelerometer = [forward acceleration + g·sin(slope),  speed × turn rate,  g·cos(slope)]
                     + road vibration
     gyroscope     = [0, 0, turn rate]
   (Changes of slope are treated as instant, so pitch rate is left out.
   The Earth's own rotation, 15 °/h, is also left out.)
2. Turned into the phone's axes by how the phone is mounted; a loose phone
   also adds its own rotation while it slides.
3. Sensor errors added: a bias drawn at power-on that then wanders slowly,
   a scale error per axis, and white noise.
"""

from dataclasses import dataclass

import numpy as np

from tunnelsim.sensors import specs
from tunnelsim.truth import DT_S, Truth


@dataclass
class ImuReadings:
    t_s: np.ndarray
    accel: np.ndarray  # (n, 3) m/s², phone axes
    gyro: np.ndarray  # (n, 3) rad/s, phone axes


def simulate_imu(truth: Truth, mount_matrices: np.ndarray, rng: np.random.Generator) -> ImuReadings:
    """`mount_matrices` holds the car-to-phone matrix at every truth sample, shape (n, 3, 3)."""
    n = len(truth.t_s)
    slope = np.arctan(truth.grade)

    force_car = np.column_stack([
        truth.a_mps2 + specs.G * np.sin(slope),
        truth.v_mps * truth.yaw_rate_rps,
        specs.G * np.cos(slope),
    ])
    force_car += _road_vibration(truth.v_mps, rng)
    rotation_car = np.column_stack([np.zeros(n), np.zeros(n), truth.yaw_rate_rps])

    M = mount_matrices
    force_phone = np.einsum("nij,nj->ni", M, force_car)
    rotation_phone = np.einsum("nij,nj->ni", M, rotation_car) + _phone_own_rotation(M)

    accel = _add_errors(force_phone, rng, specs.ACCEL_TURN_ON_BIAS, specs.ACCEL_BIAS_INSTABILITY,
                        specs.ACCEL_SCALE_ERROR, specs.ACCEL_NOISE_DENSITY)
    gyro = _add_errors(rotation_phone, rng, specs.GYRO_TURN_ON_BIAS, specs.GYRO_BIAS_INSTABILITY,
                       specs.GYRO_SCALE_ERROR, specs.GYRO_NOISE_DENSITY)
    return ImuReadings(t_s=truth.t_s, accel=accel, gyro=gyro)


def _road_vibration(v_mps: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    vertical = specs.VIBRATION_IDLE + specs.VIBRATION_PER_MPS * v_mps
    sigma = np.column_stack([vertical / 2, vertical / 2, vertical])
    return rng.normal(0, 1, sigma.shape) * sigma


def _phone_own_rotation(M: np.ndarray) -> np.ndarray:
    """Rotation rate of the phone relative to the car (non-zero only while a loose phone slides).

    A vector fixed in the car turns the opposite way when seen from a turning
    phone: dM/dt = -[w x] M, so [w x] = -(dM/dt) M^T.
    """
    dM = np.gradient(M, DT_S, axis=0)
    W = -np.einsum("nij,nkj->nik", dM, M)
    return np.column_stack([W[:, 2, 1], W[:, 0, 2], W[:, 1, 0]])


def _add_errors(true_value: np.ndarray, rng: np.random.Generator, turn_on_bias: float,
                bias_instability: float, scale_error: float, noise_density: float) -> np.ndarray:
    n = len(true_value)
    bias = rng.normal(0, turn_on_bias, 3)
    # Random walk sized so the bias has wandered by about `bias_instability` after 100 s.
    wander = np.cumsum(rng.normal(0, bias_instability * np.sqrt(DT_S / 100), (n, 3)), axis=0)
    scale = 1 + rng.normal(0, scale_error, 3)
    noise = rng.normal(0, noise_density * np.sqrt(specs.IMU_HZ / 2), (n, 3))
    return true_value * scale + bias + wander + noise
