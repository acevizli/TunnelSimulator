"""How the phone sits in the car: fixed in a mount, or loose and shifting.

Angles describe the phone relative to the car, starting from the phone lying
flat, screen up, top pointing forward:
  yaw   turns it left about the car's vertical axis,
  pitch tilts its top up (90° = upright, screen facing the driver),
  roll  tips it sideways about its own long axis.
"""

from typing import Annotated, Literal

import numpy as np
from pydantic import BaseModel, Field

DEG = np.pi / 180
SHIFT_DURATION_S = 0.5  # how long a loose phone takes to slide into its new position


class MountAngles(BaseModel):
    roll_deg: float = 0
    pitch_deg: float = Field(70, description="Default: tilted up toward the driver in a dashboard mount")
    yaw_deg: float = 5


class FixedMount(BaseModel):
    kind: Literal["fixed"] = "fixed"
    angles: MountAngles = MountAngles()


class Shift(BaseModel):
    at_fraction: float = Field(0.5, ge=0, le=1, description="When, as a fraction of the way through the tunnel")
    change: MountAngles = MountAngles(roll_deg=0, pitch_deg=10, yaw_deg=20)


class LooseMount(BaseModel):
    """Starts like a fixed mount, then shifts suddenly at set moments inside the tunnel."""

    kind: Literal["loose"] = "loose"
    angles: MountAngles = MountAngles()
    shifts: list[Shift] = [Shift()]


Mounting = Annotated[FixedMount | LooseMount, Field(discriminator="kind")]


def rotation(axis: np.ndarray, angle: float) -> np.ndarray:
    """Rotation matrix turning vectors by `angle` radians about `axis` (Rodrigues' formula)."""
    k = axis / np.linalg.norm(axis)
    K = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
    return np.eye(3) + np.sin(angle) * K + (1 - np.cos(angle)) * K @ K


def car_to_phone(angles: np.ndarray) -> np.ndarray:
    """Matrix M with v_phone = M @ v_car, for (roll, pitch, yaw) in degrees.

    Car axes: x forward, y left, z up. Each row of M is one phone axis
    written in car axes.
    """
    roll, pitch, yaw = np.asarray(angles) * DEG
    right, forward, up = np.array([0.0, -1, 0]), np.array([1.0, 0, 0]), np.array([0.0, 0, 1])
    x, y, z = right, forward, up  # phone lying flat, top forward
    turn = rotation(up, yaw)
    x, y, z = turn @ x, turn @ y, turn @ z
    tilt = rotation(x, pitch)
    y, z = tilt @ y, tilt @ z
    tip = rotation(y, roll)
    x, z = tip @ x, tip @ z
    return np.vstack([x, y, z])


def mount_angles_over_time(mounting: FixedMount | LooseMount, t_s: np.ndarray, tunnel_times: tuple[float, float]) -> np.ndarray:
    """(roll, pitch, yaw) in degrees at every time, shape (n, 3)."""
    a = mounting.angles
    angles = np.tile([a.roll_deg, a.pitch_deg, a.yaw_deg], (len(t_s), 1)).astype(float)
    if isinstance(mounting, LooseMount):
        enter, leave = tunnel_times
        for shift in mounting.shifts:
            start = enter + shift.at_fraction * (leave - enter)
            progress = np.clip((t_s - start) / SHIFT_DURATION_S, 0, 1)[:, None]
            angles += progress * [shift.change.roll_deg, shift.change.pitch_deg, shift.change.yaw_deg]
    return angles


def mount_matrices(angles: np.ndarray) -> np.ndarray:
    """car_to_phone for every row of (n, 3) angles; computed once per distinct mount position."""
    distinct, which = np.unique(angles, axis=0, return_inverse=True)
    matrices = np.array([car_to_phone(a) for a in distinct])
    return matrices[which.ravel()]
