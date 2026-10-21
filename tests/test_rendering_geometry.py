"""Testes unitários para a geometria pura dos efeitos de fluxo."""

from __future__ import annotations

import unittest

from svz.rendering_geometry import flow_points, ribbon_polygon, water_ribbon_polygon


class RenderingGeometryTests(unittest.TestCase):
    def test_flow_points_keep_exact_endpoints_and_sample_count(self) -> None:
        start = (15, 21)
        end = (135, 61)

        points = flow_points(start, end, elapsed=0.2, amplitude=4.0, count=12)

        self.assertEqual(len(points), 12)
        self.assertEqual(points[0], start)
        self.assertEqual(points[-1], end)

    def test_flow_points_enforce_minimum_samples_for_small_counts(self) -> None:
        start = (3, 5)
        end = (9, 17)

        points = flow_points(start, end, elapsed=0.1, amplitude=2.0, count=1)

        self.assertEqual(len(points), 3)
        self.assertEqual(points[0], start)
        self.assertEqual(points[-1], end)

    def test_flow_points_are_deterministic_for_the_same_time(self) -> None:
        first = flow_points((0, 0), (120, 30), elapsed=0.4, amplitude=5.0, count=18)
        second = flow_points((0, 0), (120, 30), elapsed=0.4, amplitude=5.0, count=18)

        self.assertEqual(first, second)

    def test_ribbon_polygon_builds_two_edges_with_optional_taper(self) -> None:
        centerline = [(0, 0), (10, 0), (20, 0), (30, 0)]

        polygon = ribbon_polygon(centerline, 8.0, 4.0, taper_tip=True)

        self.assertEqual(len(polygon), 2 * len(centerline))
        self.assertEqual(polygon[0], (0, 8))
        self.assertEqual(polygon[len(centerline) - 1][1], 0)
        self.assertEqual(polygon[len(centerline)], (30, 0))

    def test_ribbon_polygon_returns_short_inputs_unchanged(self) -> None:
        self.assertEqual(ribbon_polygon([], 5.0, 2.0), [])
        self.assertEqual(ribbon_polygon([(4, 7)], 5.0, 2.0), [(4, 7)])

    def test_water_ribbon_polygon_has_two_edges_and_is_deterministic(self) -> None:
        centerline = [(0, 0), (20, 0), (40, 5), (60, 8)]

        first = water_ribbon_polygon(centerline, 5.0, 2.0, elapsed=0.4, phase=1.2)
        second = water_ribbon_polygon(centerline, 5.0, 2.0, elapsed=0.4, phase=1.2)

        self.assertEqual(len(first), 2 * len(centerline))
        self.assertEqual(first, second)

    def test_water_ribbon_polygon_returns_short_inputs_unchanged(self) -> None:
        self.assertEqual(water_ribbon_polygon([], 5.0, 2.0, 0.2), [])
        self.assertEqual(
            water_ribbon_polygon([(4, 7)], 5.0, 2.0, 0.2),
            [(4, 7)],
        )


if __name__ == "__main__":
    unittest.main()
