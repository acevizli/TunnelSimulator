"""The road map: the known geometry of the route the car drives.

Along-track distance `s` is measured in metres from the start of the road.
For now the only road is straight and flat, lying along the x axis.
"""

from pydantic import BaseModel


class Road(BaseModel):
    """A straight, flat road with one tunnel on it."""

    length_m: float
    tunnel_start_m: float
    tunnel_end_m: float

    @property
    def tunnel_length_m(self) -> float:
        return self.tunnel_end_m - self.tunnel_start_m

    def in_tunnel(self, s: float) -> bool:
        return self.tunnel_start_m <= s <= self.tunnel_end_m

    def position(self, s: float) -> tuple[float, float]:
        """Map coordinates (x, y) in metres of the point at along-track distance s."""
        return (s, 0.0)

    def project(self, x: float, y: float) -> float:
        """Along-track distance of the road point closest to (x, y): map matching."""
        return min(max(x, 0.0), self.length_m)
