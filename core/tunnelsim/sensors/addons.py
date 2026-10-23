"""Add-ons: information from outside the phone, each switched on per scenario.

  vehicle speed  the car's own speed reading, passed to the phone (an OBD-II dongle
                 or a car link). It is off by its own error: reported = k × true + b
                 (+ an optional bend at high speed) + noise. A standing car reads 0.
  beacons        short-range radio transmitters on the tunnel walls, every 35 m, at
                 positions the map knows. Passing one tells the phone where it is;
                 some passes go unheard, and some beacons may be dead.

Both need a native app (research/gnss-denied-approaches.md, sections 5 and 6).
Their numbers come from that research; they are defaults, not measured on a car.
"""

from dataclasses import dataclass

import numpy as np
from pydantic import BaseModel, Field

from tunnelsim.road import MAIN, Road
from tunnelsim.sensors.source import BeaconSample, VehicleSpeedSample
from tunnelsim.truth import Truth

STANDSTILL_MPS = 0.5  # wheel-speed sensors read 0 below about 2 km/h
BEND_AT_MPS = 100 / 3.6


class VehicleSpeedSpec(BaseModel):
    k: float = Field(1.03, gt=0, description="Scale: the car reads this many times its true speed")
    b_mps: float = Field(0.3, description="Offset added to every reading while moving")
    bend_mps: float = Field(0, description="Extra error at 100 km/h, growing with speed squared; "
                                           "the estimator doesn't model it")
    noise_mps: float = Field(0.1, ge=0, description="1 sigma per reading")
    rate_hz: float = Field(10, gt=0)


class DeadStretch(BaseModel):
    """A stretch of tunnel whose beacons are dead, in metres from the tunnel entrance."""

    start_m: float
    end_m: float


class BeaconSpec(BaseModel):
    spacing_m: float = Field(35, gt=0)
    miss_rate: float = Field(0.05, ge=0, le=1, description="Chance a pass goes unheard")
    position_noise_m: float = Field(10, ge=0, description="Where along the road a pass is heard, 1 sigma around "
                                                          "the beacon")
    dead: list[DeadStretch] = Field([], description="Beacons in these stretches never answer")


class AddOns(BaseModel):
    """Off unless set. Each one switched on adds a copy of the map filter that also uses it."""

    vehicle_speed: VehicleSpeedSpec | None = None
    beacons: BeaconSpec | None = None


@dataclass(frozen=True)
class Beacon:
    """One beacon as the map knows it: where it is, never whether it works."""

    id: str
    path: str  # the path it is on: main, or the branch it is past the split on
    s_m: float


def place_beacons(road: Road, spacing_m: float) -> list[Beacon]:
    """Beacons through every tunnel, every `spacing_m` from each tunnel's entrance.
    A branch gets its own only past the point where it splits off."""
    beacons = []
    for path in road.paths():
        split = road.split_m(path.name, MAIN) or 0.0
        for span in path.tunnel_spans():
            for s in np.arange(span.start_m, span.end_m, spacing_m):
                if path.name == MAIN or s > split:
                    beacons.append(Beacon(id=f"{path.name} {len(beacons)}", path=path.name, s_m=float(s)))
    return beacons


def on_path(beacon: Beacon, path: str, road: Road) -> bool:
    """Is the beacon somewhere a car on `path` drives past?"""
    split = road.split_m(beacon.path, path)
    return split is None or beacon.s_m < split


def is_dead(beacon: Beacon, spec: BeaconSpec, road: Road) -> bool:
    from_entrance = beacon.s_m - road.path(MAIN).tunnel_spans()[0].start_m
    return any(d.start_m <= from_entrance < d.end_m for d in spec.dead)


def simulate_vehicle_speed(truth: Truth, spec: VehicleSpeedSpec, rng: np.random.Generator) -> list[VehicleSpeedSample]:
    every = max(round(1 / (spec.rate_hz * (truth.t_s[1] - truth.t_s[0]))), 1)
    t, v = truth.t_s[::every], truth.v_mps[::every]
    reported = spec.k * v + spec.b_mps + spec.bend_mps * (v / BEND_AT_MPS) ** 2 + rng.normal(0, spec.noise_mps, len(t))
    reported = np.where(v < STANDSTILL_MPS, 0.0, np.maximum(reported, 0.0))
    return [VehicleSpeedSample(float(a), float(b)) for a, b in zip(t, reported)]


def simulate_beacons(truth: Truth, beacons: list[Beacon], spec: BeaconSpec, road: Road,
                     rng: np.random.Generator) -> list[BeaconSample]:
    """One detection per beacon the car passes, heard a little before or after it, unless
    the beacon is dead or the pass goes unheard. Every beacon draws its chances, so a dead
    stretch never changes what happens at the others."""
    missed = rng.random(len(beacons)) < spec.miss_rate
    offset = rng.normal(0, spec.position_noise_m, len(beacons))
    heard = []
    for beacon, miss, off in zip(beacons, missed, offset):
        if miss or is_dead(beacon, spec, road) or not on_path(beacon, truth.path.name, road):
            continue
        i = int(np.searchsorted(truth.s_m, beacon.s_m + off))  # the first moment the car gets there
        if 0 < i < len(truth.t_s):
            heard.append(BeaconSample(float(truth.t_s[i]), beacon.id))
    return heard
