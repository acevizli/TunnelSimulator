"""What the phone records, and where estimators read it from.

Estimators only ever see samples through a `SensorSource`. Today the source
is our own simulation; later it can be a recorded trace from a real phone,
an emulator, or a live device, without the estimators changing.
All values are in SI units, times in seconds since the start of the drive.
"""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class GnssFix:
    """One GPS position fix, as the phone's location service reports it."""

    t_s: float
    x_m: float  # map coordinates
    y_m: float
    speed_mps: float
    accuracy_m: float  # the phone's own 1-sigma accuracy claim


Sample = GnssFix  # accelerometer, gyro and barometer samples join this union later


class SensorSource(Protocol):
    def read(self, until_t_s: float) -> list[Sample]:
        """Every sample with time <= until_t_s not returned before, in time order."""
        ...
