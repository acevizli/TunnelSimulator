"""A scenario: one complete drive, built from separate pieces.

Each piece is its own model with editable numbers, so a scenario can be
changed one piece at a time ("same tunnel, but stop-and-go").
"""

import re
from pathlib import Path
from typing import Annotated, get_args

from pydantic import BaseModel, Field, model_validator

from tunnelsim.road import MAIN, Road
from tunnelsim.sensors.addons import AddOns, BeaconSpec, VehicleSpeedSpec
from tunnelsim.sensors.gnss import GpsSpec
from tunnelsim.sensors.mounting import FixedMount, LooseMount, Mounting
from tunnelsim.roads import ForkRoad, LongGradeRoad, SpiralRoad, StraightRoad, TwoExitsRoad
from tunnelsim.speed_profiles import ChangeInside, FreeFlow, FullStop, SlowdownAtEntry, StopAndGo

RoadPiece = Annotated[
    StraightRoad | LongGradeRoad | TwoExitsRoad | ForkRoad | SpiralRoad, Field(discriminator="kind")
]
SpeedPiece = Annotated[
    FreeFlow | SlowdownAtEntry | StopAndGo | FullStop | ChangeInside, Field(discriminator="kind")
]


class OpenRoad(BaseModel):
    """Driving with good GPS before and after the tunnel."""

    before_s: float = Field(90, ge=0, description="Seconds of driving before the tunnel")
    after_m: float = Field(1000, ge=0)


class Route(BaseModel):
    """Which exit the driver is meant to take, and whether they actually do."""

    planned_exit: str | None = Field(None, description="None = stay on the main road")
    missed_exit: bool = Field(False, description="The car drives past the planned exit")
    callouts_m: list[float] = Field([400, 100], description="Announce the planned exit this far before it")


class Scenario(BaseModel):
    name: str
    description: str = ""
    seed: int
    road: RoadPiece = StraightRoad()
    open_road: OpenRoad = OpenRoad()
    speed: SpeedPiece = FreeFlow()
    route: Route = Route()
    mounting: Mounting = FixedMount()
    gps: GpsSpec = GpsSpec()
    add_ons: AddOns = AddOns()

    @model_validator(mode="after")
    def _route_fits_road(self):
        planned = self.route.planned_exit
        if planned is not None and planned not in self.road.exit_names():
            raise ValueError(f"planned exit {planned!r} is not on this road; it has {self.road.exit_names()}")
        if self.route.missed_exit and planned is None:
            raise ValueError("missed_exit needs a planned exit to miss")
        return self

    @property
    def driven_exit(self) -> str:
        """The path the car really takes."""
        if self.route.planned_exit is None or self.route.missed_exit:
            return MAIN
        return self.route.planned_exit

    @property
    def planned_path(self) -> str:
        return self.route.planned_exit or MAIN


def build_road(scenario: Scenario) -> Road:
    """Lay out the road so the car reaches the tunnel after `open_road.before_s` seconds."""
    before_m = scenario.open_road.before_s * scenario.speed.speed_kmh / 3.6
    return scenario.road.build(before_m=max(before_m, 1.0), after_m=max(scenario.open_road.after_m, 1.0))


def load_scenarios(folder: Path) -> list[Scenario]:
    """Read every scenario JSON file in `folder`, sorted by file name."""
    return [Scenario.model_validate_json(p.read_text()) for p in sorted(folder.glob("*.json"))]


def save_scenario(scenario: Scenario, folder: Path) -> Path:
    """Write the scenario to `folder`, named after it; a scenario saved earlier under the same name is replaced."""
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{re.sub(r'[^a-z0-9]+', '-', scenario.name.lower()).strip('-')}.json"
    path.write_text(scenario.model_dump_json(indent=2) + "\n")
    return path


class PieceChoices(BaseModel):
    """Every kind of each piece with its default numbers, for an editor to switch between."""

    road: dict[str, dict]
    speed: dict[str, dict]
    mounting: dict[str, dict]
    add_ons: dict[str, dict]
    exits: dict[str, list[str]]  # the exits each kind of road has, by road kind


def piece_choices() -> PieceChoices:
    roads = [kind() for kind in get_args(get_args(RoadPiece)[0])]
    speeds = [kind() for kind in get_args(get_args(SpeedPiece)[0])]
    return PieceChoices(
        road={r.kind: r.model_dump() for r in roads},
        speed={s.kind: s.model_dump() for s in speeds},
        mounting={m.kind: m.model_dump() for m in (FixedMount(), LooseMount())},
        add_ons={"vehicle_speed": VehicleSpeedSpec().model_dump(), "beacons": BeaconSpec().model_dump()},
        exits={r.kind: r.exit_names() for r in roads},
    )
