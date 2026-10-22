"""How fast the car wants to go, shaped by traffic.

A speed profile gives a *target* speed at each moment. The car then follows
it smoothly (see truth.py), never faster than the road's curves allow.
Each profile is written in terms of the tunnel's start and end along the
car's path, so the same profile fits any road.
"""

from typing import Callable, Literal

from pydantic import BaseModel, Field

KMH = 1 / 3.6  # km/h -> m/s
BRAKING_MPS2 = 1.5  # gentle braking used to plan a stop at a chosen point

# target_mps(t_s, s_m, v_mps) -> target speed in m/s
Driver = Callable[[float, float, float], float]


class SpeedProfileSpec(BaseModel):
    speed_kmh: float = Field(80, gt=0, description="Cruising speed before the tunnel")
    wobble_kmh: float = Field(2, ge=0, description="Size of the slow random speed variation")

    def driver(self, tunnel_start_m: float, tunnel_end_m: float) -> Driver:
        raise NotImplementedError


class FreeFlow(SpeedProfileSpec):
    kind: Literal["free_flow"] = "free_flow"

    def driver(self, tunnel_start_m, tunnel_end_m):
        return lambda t, s, v: self.speed_kmh * KMH


class SlowdownAtEntry(SpeedProfileSpec):
    """Traffic bunches up at the entrance, then clears."""

    kind: Literal["slowdown_at_entry"] = "slowdown_at_entry"
    slow_kmh: float = Field(40, gt=0)
    starts_before_m: float = Field(200, description="Slowdown begins this far before the entrance")
    lasts_m: float = Field(700, gt=0)

    def driver(self, tunnel_start_m, tunnel_end_m):
        start = tunnel_start_m - self.starts_before_m
        end = start + self.lasts_m

        def target(t, s, v):
            return (self.slow_kmh if start <= s < end else self.speed_kmh) * KMH

        return target


class StopAndGo(SpeedProfileSpec):
    """Inside the tunnel: drive a little, stop, drive a little, stop..."""

    kind: Literal["stop_and_go"] = "stop_and_go"
    go_kmh: float = Field(30, gt=0)
    go_s: float = Field(20, gt=0)
    stop_s: float = Field(10, ge=0)

    def driver(self, tunnel_start_m, tunnel_end_m):
        entered_at: float | None = None

        def target(t, s, v):
            nonlocal entered_at
            if not tunnel_start_m <= s < tunnel_end_m:
                return self.speed_kmh * KMH
            if entered_at is None:
                entered_at = t
            phase = (t - entered_at) % (self.go_s + self.stop_s)
            return self.go_kmh * KMH if phase < self.go_s else 0.0

        return target


class FullStop(SpeedProfileSpec):
    """One long stop inside the tunnel, e.g. behind a breakdown."""

    kind: Literal["full_stop"] = "full_stop"
    stop_at_fraction: float = Field(0.5, ge=0, le=1, description="Where in the tunnel, 0 = entrance, 1 = exit")
    stop_s: float = Field(60, gt=0)

    def driver(self, tunnel_start_m, tunnel_end_m):
        stop_at = tunnel_start_m + self.stop_at_fraction * (tunnel_end_m - tunnel_start_m)
        stopped_at: float | None = None
        done = False

        def target(t, s, v):
            nonlocal stopped_at, done
            braking_distance = v * v / (2 * BRAKING_MPS2)
            if done or s + braking_distance < stop_at:
                return self.speed_kmh * KMH
            if stopped_at is None and v < 0.05:
                stopped_at = t
            if stopped_at is not None and t - stopped_at >= self.stop_s:
                done = True
            return 0.0

        return target


class ChangeInside(SpeedProfileSpec):
    """Steady speed up to the tunnel, then a different steady speed inside it."""

    kind: Literal["change_inside"] = "change_inside"
    speed_kmh: float = 70
    new_speed_kmh: float = Field(100, gt=0)
    change_at_fraction: float = Field(0.3, ge=0, le=1)

    def driver(self, tunnel_start_m, tunnel_end_m):
        change_at = tunnel_start_m + self.change_at_fraction * (tunnel_end_m - tunnel_start_m)
        return lambda t, s, v: (self.new_speed_kmh if s >= change_at else self.speed_kmh) * KMH
