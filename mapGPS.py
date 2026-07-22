#!/usr/bin/env python3
"""
plot_halow_map.py

Draws a 2D map of GPS locations from a HaLow-style CSV file
(columns: Time, Lat, Lon, Alt, Sats, Zero), with a straight line
drawn from the FIRST point to every later point.

Usage:
    python plot_halow_map.py HaLow.csv [--output map.png] [--satellite]
    the satellite options adds a satellite map to the background
"""

import argparse
import csv
import sys
import matplotlib.pyplot as plt

try:
    import contextily as cx
    HAS_CONTEXTILY = True
except ImportError:
    HAS_CONTEXTILY = False


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


def plot_points(points, output_path=None, satellite=False):
    if not points:
        print("No valid Lat/Lon data rows found in the CSV - nothing to plot.")
        sys.exit(1)

    lats = [p[0] for p in points]
    lons = [p[1] for p in points]

    first_lat, first_lon = points[0]

    fig, ax = plt.subplots(figsize=(9, 9))

    # Colors that show up well over satellite imagery vs. a plain background
    line_color = "yellow" if satellite else "steelblue"
    point_color = "yellow" if satellite else "steelblue"
    first_color = "red" if satellite else "crimson"

    # Draw a line from the first point to every later point
    for lat, lon in points[1:]:
        ax.plot([first_lon, lon], [first_lat, lat], color=line_color,
                linewidth=1.2, alpha=0.8, zorder=2)

    # Plot all points
    ax.scatter(lons, lats, color=point_color, s=30, zorder=3,
               label="Points", edgecolors="black", linewidths=0.4)

    # Highlight the first point
    ax.scatter([first_lon], [first_lat], color=first_color, s=140,
               zorder=4, label="First point", marker="*",
               edgecolors="black", linewidths=0.6)

    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.set_title("GPS Locations (lines from first point to each other point)")
    ax.legend()
    ax.set_aspect("equal", adjustable="datalim")

    if satellite:
        if not HAS_CONTEXTILY:
            print("contextily is not installed. Install it with:\n"
                  "    pip install contextily\n"
                  "then re-run with --satellite.")
            sys.exit(1)
        # Give the imagery a little breathing room around the points
        lon_pad = (max(lons) - min(lons)) * 0.1 or 0.0005
        lat_pad = (max(lats) - min(lats)) * 0.1 or 0.0005
        ax.set_xlim(min(lons) - lon_pad, max(lons) + lon_pad)
        ax.set_ylim(min(lats) - lat_pad, max(lats) + lat_pad)
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
    parser = argparse.ArgumentParser(description="Plot GPS points with lines from the first point to each later point.")
    parser.add_argument("csv_path", help="Path to the HaLow-style CSV file")
    parser.add_argument("--output", "-o", default=None,
                         help="Path to save the plot image (e.g. map.png). If omitted, shows an interactive window.")
    parser.add_argument("--satellite", action="store_true",
                         help="Overlay the points on satellite imagery (requires 'pip install contextily' and internet access).")
    args = parser.parse_args()

    points = load_points(args.csv_path)
    plot_points(points, args.output, satellite=args.satellite)


if __name__ == "__main__":
    main()
