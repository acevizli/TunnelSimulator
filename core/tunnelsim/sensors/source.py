"""What the phone records, and where estimators read it from.

Estimators only ever see samples through a `SensorSource`. Today the source
is our own simulation; later it can be a recorded trace from a real phone,
an emulator, or a live device, without the estimators changing.

All values are in SI units, times in seconds since the start of the drive.
Motion sensors report in the *phone's* own axes: x to the right of the
screen, y to the top of the screen, z out of the screen. How those axes sit
in the car is unknown to the estimator.
"""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class AccelSample:
    """Specific force: acceleration minus gravity, so a phone at rest reads +9.8 m/s² upward."""

    t_s: float
    x: float  # m/s²
    y: float
    z: float


@dataclass(frozen=True)
class GyroSample:
    """Rotation rate about each phone axis."""

    t_s: float
    x: float  # rad/s
    y: float
    z: float


@dataclass(frozen=True)
class MagSample:
    """Magnetic field along each phone axis."""

    t_s: float
    x: float  # µT
    y: float
    z: float


@dataclass(frozen=True)
class BaroSample:
    t_s: float
    pressure_pa: float


@dataclass(frozen=True)
class GnssFix:
    """One GPS position fix, as the phone's location service reports it."""

    t_s: float
    x_m: float  # map coordinates
    y_m: float
    speed_mps: float
    bearing_rad: float  # direction of travel in map axes (0 = east, counter-clockwise)
    accuracy_m: float  # the phone's own 1-sigma accuracy claim (not always honest)


@dataclass(frozen=True)
class VehicleSpeedSample:
    """The car's own speed reading (add-on), with the car's own error in it."""

    t_s: float
    speed_mps: float


@dataclass(frozen=True)
class BeaconSample:
    """A tunnel beacon was heard (add-on). Its id is looked up on the map for its position."""

    t_s: float
    beacon_id: str


Sample = AccelSample | GyroSample | MagSample | BaroSample | GnssFix | VehicleSpeedSample | BeaconSample


class SensorSource(Protocol):
    def read(self, until_t_s: float) -> list[Sample]:
        """Every sample with time <= until_t_s not returned before, in time order."""
        ...
