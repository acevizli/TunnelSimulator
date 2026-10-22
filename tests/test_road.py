import math

import numpy as np

from tunnelsim.road import MAIN, Road, Segment
from tunnelsim.roads import ForkRoad, LongGradeRoad, SpiralRoad, StraightRoad, TwoExitsRoad


def test_straight_road_is_open_tunnel_open():
    road = StraightRoad(tunnel_length_m=1500).build(before_m=500, after_m=300)
    path = road.path()
    assert path.length_m == 2300
    [span] = path.tunnel_spans()
    assert (span.start_m, span.end_m) == (500, 2000)


def test_a_quarter_circle_turns_ninety_degrees_and_ends_where_geometry_says():
    radius = 100.0
    path = Road(main=[Segment(length_m=math.pi / 2 * radius, radius_m=radius)]).path()
    assert np.isclose(path.heading[-1], math.pi / 2, atol=0.02)
    assert np.isclose(path.x[-1], radius, atol=1.5) and np.isclose(path.y[-1], radius, atol=1.5)


def test_grade_raises_the_road():
    path = Road(main=[Segment(length_m=1000, grade_pct=5)]).path()
    assert np.isclose(path.z[-1], 50, atol=0.1)


def test_paths_share_geometry_until_the_exit_then_split():
    road = TwoExitsRoad().build(before_m=1000, after_m=500)
    main, via_a = road.path(MAIN), road.path("Exit A")
    split = road.exit("Exit A").at_m
    before = main.s < split - 1
    assert np.allclose(main.x[before], via_a.x[: before.sum()])
    s_after = split + 200
    gap = math.dist((main.lookup(main.x, s_after), main.lookup(main.y, s_after)),
                    (via_a.lookup(via_a.x, s_after), via_a.lookup(via_a.y, s_after)))
    assert gap > 20


def test_fork_road_has_an_open_air_gap_inside_the_tunnel():
    path = ForkRoad().build(before_m=1000, after_m=500).path()
    assert len(path.tunnel_spans()) == 2


def test_spiral_turns_about_six_times_and_climbs():
    path = SpiralRoad().build(before_m=500, after_m=500).path()
    assert 5.5 < path.heading[-1] / (2 * math.pi) < 6.5
    assert path.z[-1] > 120


def test_long_grade_goes_down_then_up():
    path = LongGradeRoad().build(before_m=500, after_m=500).path()
    assert path.z.min() < -50 and path.z[-1] > path.z.min() + 50


def test_projection_finds_the_along_track_distance():
    path = SpiralRoad().build(before_m=500, after_m=500).path()
    s_true = 2400.0
    s, off = path.project(path.lookup(path.x, s_true) + 2, path.lookup(path.y, s_true), near_s=s_true)
    assert abs(s - s_true) <= 3 and off < 3
