# TunnelSimulator

Estimating a car's position on a smartphone while GPS is unavailable inside a tunnel, with a visual simulator to evaluate the approach.

## The problem

A driver follows turn-by-turn directions on a phone. The road enters a long tunnel (single lane, 500 m – 5 km), GPS fades out and stays unusable for minutes. The navigation app still needs to:

- show where the car is,
- call out an exit *inside* the tunnel at the right moment,
- recover cleanly when the car comes out.

## Goals

1. Propose one or more approaches for estimating position while GPS is unreliable, using sensors available on a modern smartphone (plus anything else reasonably assumed available, justified).
2. Build a visual simulator: a road with a tunnel, one or more cars driving through it, the sensor data the phone would record, and the true position shown next to the estimate.
3. Use the simulator to evaluate the approach: how well it works, where it breaks, and why.

## Status

Planning. Open decisions and research are tracked as GitHub issues (see the `wayfinder:map` issue).
