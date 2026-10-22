"""A scenario: one complete drive, built from separate pieces.

Each piece is its own model so it can be swapped or edited on its own.
For now there is one choice per piece; more roads, speed profiles,
mountings and GPS models are added as further pieces.
"""

from pathlib import Path

from pydantic import BaseModel, Field

from tunnelsim.road import Road


class StraightRoadSpec(BaseModel):
    """Flat, straight road: open road, then the tunnel, then open road."""

    tunnel_length_m: float = Field(2000, ge=500, le=5000)
    open_before_s: float = Field(90, ge=0, description="Seconds of driving with GPS before the tunnel")
    open_after_m: float = Field(1000, ge=0)


class FreeFlowSpeed(BaseModel):
    """Steady speed with a gentle, slow wobble around it."""

    speed_kmh: float = Field(80, gt=0)
    wobble_kmh: float = Field(2, ge=0, description="Size of the slow speed variation")


class CleanGps(BaseModel):
    """GPS that works normally outside the tunnel and is simply absent inside."""

    noise_m: float = Field(3.0, ge=0, description="Horizontal position noise, 1 sigma")
    speed_noise_mps: float = Field(0.2, ge=0)


class Scenario(BaseModel):
    name: str
    seed: int
    road: StraightRoadSpec = StraightRoadSpec()
    speed: FreeFlowSpeed = FreeFlowSpeed()
    gps: CleanGps = CleanGps()


def build_road(scenario: Scenario) -> Road:
    """Lay out the road so the car reaches the tunnel after `open_before_s` seconds."""
    before_m = scenario.road.open_before_s * scenario.speed.speed_kmh / 3.6
    tunnel_end_m = before_m + scenario.road.tunnel_length_m
    return Road(
        length_m=tunnel_end_m + scenario.road.open_after_m,
        tunnel_start_m=before_m,
        tunnel_end_m=tunnel_end_m,
    )


def load_scenarios(folder: Path) -> list[Scenario]:
    """Read every scenario JSON file in `folder`, sorted by file name."""
    return [Scenario.model_validate_json(p.read_text()) for p in sorted(folder.glob("*.json"))]
