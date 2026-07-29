#!/usr/bin/env python3
"""
mapGPS.py

Draws a 2D map of GPS locations from up to three CSV files
(columns: Time, Lat, Lon, Alt, Sats, Zero). For each file, a straight
line is drawn from that file's FIRST point to every later point in
that file. Each file is plotted in its own color, and each file's
farthest point (from its own first point) is highlighted using a
lighter shade of that same color.

Usage:
    python mapGPS.py file1.csv file2.csv file3.csv [--output map.png]
    python mapGPS.py file1.csv                       (1-3 files supported)

    Satellite imagery background is on by default (requires
    'pip install contextily' and internet access).
"""

import argparse
import colorsys
import csv
import os
import sys
from math import radians, sin, cos, sqrt, atan2
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

try:
    import contextily as cx
    HAS_CONTEXTILY = True
except ImportError:
    HAS_CONTEXTILY = False


# Base colors for up to 3 files, chosen to show up well over satellite
# imagery. If more than 3 files are ever passed, colors cycle.
BASE_COLORS = ["yellow", "cyan", "magenta"]


def load_points(csv_path):
    """
    Reads the CSV and returns a list of (lat, lon) tuples.
    Skips header rows and any row that doesn't have valid numeric
    Lat/Lon values (e.g. rows where the GPS never got a fix).
    """
    points = []
    with open(csv_path, newline="") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) < 3:
                continue
            lat_str, lon_str = row[1].strip(), row[2].strip()
            try:
                lat = float(lat_str)
                lon = float(lon_str)
            except ValueError:
                # Not a numeric row (header, or a fix-less log line) - skip it
                continue
            points.append((lat, lon))
    return points


def haversine_m(lat1, lon1, lat2, lon2):
    """Great-circle distance in meters between two lat/lon points."""
    R = 6371000.0  # Earth radius in meters
    phi1, phi2 = radians(lat1), radians(lat2)
    dphi = radians(lat2 - lat1)
    dlambda = radians(lon2 - lon1)
    a = sin(dphi / 2) ** 2 + cos(phi1) * cos(phi2) * sin(dlambda / 2) ** 2
    return 2 * R * atan2(sqrt(a), sqrt(1 - a))


def format_distance(meters):
    """Human-friendly distance string, switching to km/miles once it's large."""
    feet = meters * 3.28084
    miles = meters / 1609.344
    km = meters / 1000.0
    if miles >= 0.5:
        return f"{meters:.0f} m ({km:.2f} km / {miles:.2f} mi)"
    return f"{meters:.0f} m ({feet:.0f} ft)"


def find_farthest_point(points):
    """
    Given a list of (lat, lon) points, returns
    (farthest_point, distance_m) for the point farthest from points[0].
    """
    first_lat, first_lon = points[0]
    farthest_point = None
    farthest_dist = -1.0
    for lat, lon in points[1:]:
        d = haversine_m(first_lat, first_lon, lat, lon)
        if d > farthest_dist:
            farthest_dist = d
            farthest_point = (lat, lon)
    return farthest_point, farthest_dist


def lighten_color(color, amount=0.5):
    """
    Returns a lighter shade of the given matplotlib color by blending
    it toward white. amount=0 returns the original color, amount=1
    returns white.
    """
    r, g, b = mcolors.to_rgb(color)
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    l = l + (1 - l) * amount
    return colorsys.hls_to_rgb(h, l, s)


def plot_datasets(csv_paths, output_path=None, satellite=True):
    datasets = []  # list of dicts with points, color, light_color, label
    all_lats, all_lons = [], []

    for idx, csv_path in enumerate(csv_paths):
        points = load_points(csv_path)
        if not points:
            print(f"Warning: no valid Lat/Lon rows found in {csv_path} - skipping.")
            continue
        color = BASE_COLORS[idx % len(BASE_COLORS)]
        light_color = lighten_color(color, amount=0.55)
        datasets.append({
            "path": csv_path,
            "label": os.path.basename(csv_path),
            "points": points,
            "color": color,
            "light_color": light_color,
        })
        lats = [p[0] for p in points]
        lons = [p[1] for p in points]
        all_lats.extend(lats)
        all_lons.extend(lons)

    if not datasets:
        print("No valid Lat/Lon data rows found in any CSV - nothing to plot.")
        sys.exit(1)

    fig, ax = plt.subplots(figsize=(9, 9))

    for ds in datasets:
        points = ds["points"]
        color = ds["color"]
        light_color = ds["light_color"]
        label = ds["label"]

        lats = [p[0] for p in points]
        lons = [p[1] for p in points]
        first_lat, first_lon = points[0]

        # Draw a line from this file's first point to every later point
        for lat, lon in points[1:]:
            ax.plot([first_lon, lon], [first_lat, lat], color=color,
                    linewidth=1.0, alpha=0.7, zorder=2)

        # Plot all points for this file
        ax.scatter(lons, lats, color=color, s=30, zorder=3,
                   label=f"{label} points", edgecolors="black", linewidths=0.4)

        # Highlight the first point (this file's "controller")
        ax.scatter([first_lon], [first_lat], color=color, s=140,
                   zorder=4, label=f"{label} start", marker="*",
                   edgecolors="black", linewidths=0.8)

        # Find and highlight the point farthest from the first point,
        # using a lighter shade of this file's color.
        farthest_point, farthest_dist = find_farthest_point(points)
        if farthest_point is not None:
            far_lat, far_lon = farthest_point

            ax.scatter([far_lon], [far_lat], color=light_color, s=150,
                       zorder=5, label=f"{label} farthest", marker="D",
                       edgecolors="black", linewidths=0.8)

            # Draw the first-to-farthest line a bit thicker so it stands out
            ax.plot([first_lon, far_lon], [first_lat, far_lat], color=light_color,
                    linewidth=2.2, alpha=0.95, zorder=4)

            # Label with the distance, placed at the midpoint of that line
            mid_lon = (first_lon + far_lon) / 2
            mid_lat = (first_lat + far_lat) / 2
            dist_label = f"{label}: {format_distance(farthest_dist)}"
            ax.annotate(
                dist_label,
                xy=(mid_lon, mid_lat),
                xytext=(8, 8),
                textcoords="offset points",
                fontsize=9,
                fontweight="bold",
                color="black",
                bbox=dict(boxstyle="round,pad=0.3", facecolor="white",
                          edgecolor=color, alpha=0.85),
                zorder=6,
            )

    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.set_title(", ".join(os.path.basename(p) for p in csv_paths))
    ax.legend(fontsize=8, loc="best")
    ax.set_aspect("equal", adjustable="datalim")

    if satellite:
        if not HAS_CONTEXTILY:
            print("contextily is not installed. Install it with:\n"
                  "    pip install contextily\n"
                  "then re-run.")
            sys.exit(1)
        # Give the imagery a little breathing room around the points
        lon_pad = (max(all_lons) - min(all_lons)) * 0.1 or 0.0005
        lat_pad = (max(all_lats) - min(all_lats)) * 0.1 or 0.0005
        ax.set_xlim(min(all_lons) - lon_pad, max(all_lons) + lon_pad)
        ax.set_ylim(min(all_lats) - lat_pad, max(all_lats) + lat_pad)
        cx.add_basemap(ax, crs="EPSG:4326", source=cx.providers.Esri.WorldImagery)
    else:
        ax.grid(True, linestyle="--", alpha=0.4)

    plt.tight_layout()

    if output_path:
        plt.savefig(output_path, dpi=150)
        print(f"Map saved to {output_path}")
    else:
        plt.show()


def main():
    parser = argparse.ArgumentParser(
        description="Plot GPS points from up to 3 CSV files, each in its own "
                     "color, with lines from each file's first point to each "
                     "later point in that file, and each file's farthest "
                     "point highlighted in a lighter shade of its color.")
    parser.add_argument("csv_paths", nargs="+",
                         help="Path(s) to 1-3 HaLow-style CSV files.")
    parser.add_argument("--output", "-o", default=None,
                         help="Path to save the plot image (e.g. map.png). If omitted, shows an interactive window.")
    parser.add_argument("--satellite", action="store_true", default=True,
                         help="Overlay the points on satellite imagery (on by default; requires 'pip install contextily' and internet access).")
    args = parser.parse_args()

    if len(args.csv_paths) > 3:
        print(f"Warning: {len(args.csv_paths)} files given; only 3 distinct "
              f"colors are defined so colors will repeat.")

    plot_datasets(args.csv_paths, args.output, satellite=True)  # always add satellite background


if __name__ == "__main__":
    main()
