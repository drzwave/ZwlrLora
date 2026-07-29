#!/usr/bin/env python3
"""
mapGPSAnimated.py

Creates an animated GIF showing GPS points from a CSV file
(columns: Time, Lat, Lon, Alt, Sats, Zero) appearing one-by-one in the
order given by the Time column, with a line drawn from the FIRST point
to every point revealed so far.

Usage:
    python mapGPSAnimated.py filename.csv --output animation.gif
"""

import argparse
import csv
import io
import re
import sys

import matplotlib.pyplot as plt
from PIL import Image

try:
    import contextily as cx
    HAS_CONTEXTILY = True
except ImportError:
    HAS_CONTEXTILY = False


def parse_time_to_seconds(time_str):
    """
    Parses a Time value like '19:06.1' (MM:SS.s) into total seconds.
    Returns None if it can't be parsed.
    """
    m = re.match(r"^(\d+):(\d+(?:\.\d+)?)$", time_str.strip())
    if not m:
        return None
    minutes, seconds = m.groups()
    return int(minutes) * 60 + float(seconds)


def load_points(csv_path):
    """
    Reads the CSV and returns a list of (lat, lon, seconds) tuples,
    in file order, where `seconds` is a monotonically increasing
    elapsed-time value derived from the Time column (handles minute
    wraparound past 59). Rows with invalid/missing Lat/Lon are skipped.
    """
    points = []
    prev_raw = None
    wrap_offset = 0
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) < 3:
                continue
            time_str, lat_str, lon_str = row[0].strip(), row[1].strip(), row[2].strip()
            try:
                lat = float(lat_str)
                lon = float(lon_str)
            except ValueError:
                continue

            raw_seconds = parse_time_to_seconds(time_str)
            if raw_seconds is None:
                # Fall back to simple ordering if the time can't be parsed
                seconds = points[-1][2] + 1 if points else 0.0
            else:
                if prev_raw is not None and raw_seconds < prev_raw - 1:
                    # Detected wraparound (e.g. minutes rolled past 59)
                    wrap_offset += 3600
                seconds = raw_seconds + wrap_offset
                prev_raw = raw_seconds

            points.append((lat, lon, seconds))
    return points


def render_frame(points, upto_index, satellite, bounds):
    """Renders a single frame (matplotlib figure) up to and including
    points[upto_index], returns a PIL Image."""
    lats_all = [p[0] for p in points]
    lons_all = [p[1] for p in points]
    first_lat, first_lon = points[0][0], points[0][1]

    fig, ax = plt.subplots(figsize=(9, 9), dpi=100)

    line_color = "yellow" if satellite else "steelblue"
    point_color = "yellow" if satellite else "steelblue"
    first_color = "red" if satellite else "crimson"

    shown = points[:upto_index + 1]
    shown_lats = [p[0] for p in shown]
    shown_lons = [p[1] for p in shown]

    # Lines from first point to every point revealed so far
    for lat, lon, _ in shown[1:]:
        ax.plot([first_lon, lon], [first_lat, lat], color=line_color,
                linewidth=1.2, alpha=0.8, zorder=2)

    # All revealed points
    ax.scatter(shown_lons, shown_lats, color=point_color, s=30, zorder=3,
               edgecolors="black", linewidths=0.4)

    # Current (most recent) point highlighted
    ax.scatter([shown_lons[-1]], [shown_lats[-1]], color="lime", s=90,
               zorder=5, edgecolors="black", linewidths=0.6, marker="o")

    # First point
    ax.scatter([first_lon], [first_lat], color=first_color, s=140,
               zorder=4, marker="*", edgecolors="black", linewidths=0.6)

    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.set_title(f"GPS Track  ({upto_index + 1}/{len(points)} points)")

    min_lon, max_lon, min_lat, max_lat = bounds
    ax.set_xlim(min_lon, max_lon)
    ax.set_ylim(min_lat, max_lat)
    ax.set_aspect("equal", adjustable="box")

    if satellite:
        cx.add_basemap(ax, crs="EPSG:4326", source=cx.providers.Esri.WorldImagery)
    else:
        ax.grid(True, linestyle="--", alpha=0.4)

    plt.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    plt.close(fig)
    buf.seek(0)
    return Image.open(buf).convert("RGB")


def make_gif(points, output_path, satellite=False, min_ms=80, max_ms=800,
             hold_last_ms=1500, speed=1.0):
    if not points:
        print("No valid Lat/Lon data rows found in the CSV - nothing to animate.")
        sys.exit(1)

    lats = [p[0] for p in points]
    lons = [p[1] for p in points]
    lon_pad = (max(lons) - min(lons)) * 0.12 or 0.0005
    lat_pad = (max(lats) - min(lats)) * 0.12 or 0.0005
    bounds = (min(lons) - lon_pad, max(lons) + lon_pad,
              min(lats) - lat_pad, max(lats) + lat_pad)

    if satellite and not HAS_CONTEXTILY:
        print("contextily is not installed. Install it with:\n"
              "    pip install contextily\n"
              "then re-run with --satellite.")
        sys.exit(1)

    frames = []
    durations = []
    n = len(points)
    for i in range(n):
        print(f"Rendering frame {i + 1}/{n}...")
        frames.append(render_frame(points, i, satellite, bounds))
        if i == 0:
            durations.append(min_ms)
        else:
            dt = points[i][2] - points[i - 1][2]
            ms = int(max(min_ms, min(max_ms, dt * 1000 / speed)))
            durations.append(ms)

    # Hold on the final, fully-drawn frame for a bit
    durations[-1] = hold_last_ms

    frames[0].save(
        output_path,
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        loop=0,
    )
    print(f"Animated GIF saved to {output_path} ({n} frames)")


def main():
    parser = argparse.ArgumentParser(
        description="Animate GPS points from a HaLow-style CSV appearing over time, "
                    "with lines from the first point to each revealed point.")
    parser.add_argument("csv_path", help="Path to the HaLow-style CSV file")
    parser.add_argument("--output", "-o", default="animation.gif",
                         help="Output GIF path (default: animation.gif)")
    parser.add_argument("--satellite", action="store_true",
                         help="Overlay on satellite imagery (requires 'pip install contextily' and internet access).")
    parser.add_argument("--speed", type=float, default=5.0,
                         help="Playback speed multiplier relative to real recorded time (default: 1.0). "
                              "E.g. 2.0 plays twice as fast.")
    parser.add_argument("--min-ms", type=int, default=80,
                         help="Minimum duration per frame in milliseconds (default: 80).")
    parser.add_argument("--max-ms", type=int, default=800,
                         help="Maximum duration per frame in milliseconds, caps long real-world gaps (default: 800).")
    args = parser.parse_args()

    points = load_points(args.csv_path)
    make_gif(points, args.output, satellite=True,
              min_ms=args.min_ms, max_ms=args.max_ms, speed=args.speed)


if __name__ == "__main__":
    main()
