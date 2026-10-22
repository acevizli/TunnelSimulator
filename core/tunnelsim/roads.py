"""The five roads the simulator ships with, each simplified from a real tunnel.

Every road is: open road, the tunnel section, open road. A road spec only
describes its tunnel section; positions are in metres from the tunnel
entrance. Exits split off inside the tunnel, and every branch also ends in
open road.
"""

from typing import Literal

from pydantic import BaseModel, Field

from tunnelsim.road import Exit, Road, Segment


def tunnel(length_m: float, radius_m: float | None = None, grade_pct: float = 0) -> Segment:
    return Segment(length_m=length_m, radius_m=radius_m, grade_pct=grade_pct, tunnel=True)


def open_air(length_m: float, radius_m: float | None = None, grade_pct: float = 0) -> Segment:
    return Segment(length_m=length_m, radius_m=radius_m, grade_pct=grade_pct, tunnel=False)


class RoadSpec(BaseModel):
    def tunnel_section(self) -> list[Segment]:
        raise NotImplementedError

    def tunnel_exits(self) -> list[Exit]:
        return []

    def exit_names(self) -> list[str]:
        return [e.name for e in self.tunnel_exits()]

    def build(self, before_m: float, after_m: float) -> Road:
        """Put open road before and after the tunnel section and on the end of every branch."""
        exits = [
            Exit(name=e.name, at_m=before_m + e.at_m, branch=e.branch + [open_air(after_m)])
            for e in self.tunnel_exits()
        ]
        return Road(main=[open_air(before_m)] + self.tunnel_section() + [open_air(after_m)], exits=exits)


class StraightRoad(RoadSpec):
    """Flat and straight: the control case, and the case with no landmarks at all."""

    kind: Literal["straight"] = "straight"
    description: str = "Based on the Fort McHenry Tunnel (straight, flat, 2.2 km)"
    tunnel_length_m: float = Field(2000, ge=500, le=5000)

    def tunnel_section(self):
        return [tunnel(self.tunnel_length_m)]


class LongGradeRoad(RoadSpec):
    """A long descent and climb with gentle curves and one exit partway in."""

    kind: Literal["long_grade"] = "long_grade"
    description: str = "Based on Södra länken, Stockholm (4.5 km, 5% grades, exits underground)"
    tunnel_length_m: float = Field(4500, ge=2000, le=5000)
    grade_pct: float = Field(5, ge=0, le=10)
    exit_at_m: float = Field(2700, description="Exit position from the tunnel entrance")

    def tunnel_section(self):
        L, g = self.tunnel_length_m, self.grade_pct
        return [
            tunnel(0.12 * L),
            tunnel(0.28 * L, radius_m=1000, grade_pct=-g),
            tunnel(0.20 * L, radius_m=-600),
            tunnel(0.28 * L, grade_pct=g),
            tunnel(0.12 * L),
        ]

    def tunnel_exits(self):
        ramp = [tunnel(250, radius_m=-150, grade_pct=self.grade_pct), tunnel(150, grade_pct=self.grade_pct)]
        return [Exit(name="Exit", at_m=self.exit_at_m, branch=ramp)]


class TwoExitsRoad(RoadSpec):
    """Two exits close together: is the callout for the right one at the right time?"""

    kind: Literal["two_exits"] = "two_exits"
    description: str = "Based on the I-93 O'Neill Tunnel, Boston (2.4 km, exits inside)"
    tunnel_length_m: float = Field(2400, ge=1500, le=5000)
    exit_a_at_m: float = 1200
    exit_b_at_m: float = 1600

    def tunnel_section(self):
        L = self.tunnel_length_m
        return [
            tunnel(0.5 * L, grade_pct=-2),
            tunnel(0.3 * L, radius_m=1200, grade_pct=2),
            tunnel(0.2 * L, grade_pct=2),
        ]

    def tunnel_exits(self):
        ramp = [tunnel(200, radius_m=-200, grade_pct=4), tunnel(100, grade_pct=4)]
        return [
            Exit(name="Exit A", at_m=self.exit_a_at_m, branch=ramp),
            Exit(name="Exit B", at_m=self.exit_b_at_m, branch=ramp),
        ]


class ForkRoad(RoadSpec):
    """A dip, a short open-air gap where GPS briefly returns, then the road forks."""

    kind: Literal["fork"] = "fork"
    description: str = "Based on the Opera Tunnel, Oslo (5.8 km, a dip, an open-air gap, a fork)"
    dip_grade_pct: float = Field(4, ge=0, le=8)
    gap_m: float = Field(100, ge=0, description="Open-air gap length; 0 removes it")

    def tunnel_section(self):
        g = self.dip_grade_pct
        before_gap = [tunnel(1200), tunnel(600, radius_m=2000, grade_pct=-g), tunnel(600, grade_pct=g)]
        gap = [open_air(self.gap_m)] if self.gap_m > 0 else []
        return before_gap + gap + [tunnel(600), tunnel(1000, radius_m=2000), tunnel(1700)]

    def fork_at_m(self) -> float:
        return 1200 + 600 + 600 + self.gap_m + 600

    def tunnel_exits(self):
        right = [tunnel(300, radius_m=-600), tunnel(1000, grade_pct=2)]
        return [Exit(name="Fork right", at_m=self.fork_at_m(), branch=right)]


class SpiralRoad(RoadSpec):
    """A tight climbing spiral: extreme, but the most for curve and grade checks to work with."""

    kind: Literal["spiral"] = "spiral"
    description: str = "Based on the Spiralen tunnel, Drammen (1.65 km, ~35 m radius, ~10% grade)"
    radius_m: float = Field(35, ge=20, le=200)
    grade_pct: float = Field(10, ge=0, le=12)

    def tunnel_section(self):
        return [
            tunnel(150),
            tunnel(1300, radius_m=self.radius_m, grade_pct=self.grade_pct),
            tunnel(200, grade_pct=2),
        ]
