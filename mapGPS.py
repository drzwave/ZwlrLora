#!/usr/bin/env python3
"""
mapGPS.py

Draws a 2D map of GPS locations from a CSV file
(columns: Time, Lat, Lon, Alt, Sats, Zero), with a straight line
drawn from the FIRST point to every later point.

Usage:
    python mapGPS.py filename.csv [--output map.png] [--satellite]
    the satellite options adds a satellite map to the background
    The satellite option is now on by default - todo remove the non-satellite code
"""

import argparse
import csv
import sys
import xml.etree.ElementTree as ET
from math import radians, sin, cos, sqrt, atan2
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


def load_gpx_points(gpx_path):
    """
    Reads a GPX file and returns a list of (lat, lon) tuples, in order,
    pulled from any track points, route points, or waypoints found in
    the file (namespace-agnostic, so it works with GPX 1.0 and 1.1).
    """
    points = []
    try:
        tree = ET.parse(gpx_path)
    except ET.ParseError as e:
        print(f"Warning: could not parse GPX file {gpx_path} ({e}) - skipping.")
        return points

    root = tree.getroot()
    for elem in root.iter():
        tag = elem.tag.split("}")[-1]  # strip namespace, e.g. "{...}trkpt" -> "trkpt"
        if tag in ("trkpt", "rtept", "wpt"):
            lat_str, lon_str = elem.get("lat"), elem.get("lon")
            if lat_str is None or lon_str is None:
                continue
            try:
                points.append((float(lat_str), float(lon_str)))
            except ValueError:
                continue
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


def plot_points(points, csv_path, output_path=None, satellite=True, gpx_path=None):
    if not points:
        print("No valid Lat/Lon data rows found in the CSV - nothing to plot.")
        sys.exit(1)

    lats = [p[0] for p in points]
    lons = [p[1] for p in points]

    gpx_points = []
    if gpx_path:
        gpx_points = load_gpx_points(gpx_path)
        if not gpx_points:
            print(f"Warning: no valid trkpt/rtept/wpt data found in {gpx_path}.")

    # Bounds used for the satellite basemap extent include both the CSV
    # points and any GPX track points, so the whole track stays in frame.
    bound_lats = lats + [p[0] for p in gpx_points]
    bound_lons = lons + [p[1] for p in gpx_points]

    first_lat, first_lon = points[0]

    fig, ax = plt.subplots(figsize=(9, 9))

    # Draw the GPX track first, as the base layer underneath everything
    # else: small white dots connected by thin white lines.
    if gpx_points:
        gpx_lats = [p[0] for p in gpx_points]
        gpx_lons = [p[1] for p in gpx_points]
        ax.plot(gpx_lons, gpx_lats, color="white", linewidth=2.0,
                alpha=0.8, zorder=1)
        ax.scatter(gpx_lons, gpx_lats, color="white", s=8, zorder=1,
                   label="GPX track", edgecolors="none")

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
               zorder=4, label="Controller", marker="*",
               edgecolors="black", linewidths=0.6)

    # Find and highlight the point farthest from the first point,
    # and label the distance between them.
    farthest_point, farthest_dist = find_farthest_point(points)
    if farthest_point is not None:
        far_lat, far_lon = farthest_point
        far_color = "lime" if satellite else "darkorange"

        ax.scatter([far_lon], [far_lat], color=far_color, s=140,
                   zorder=5, label="Farthest point", marker="D",
                   edgecolors="black", linewidths=0.6)

        # Draw the first-to-farthest line a bit thicker so it stands out
        ax.plot([first_lon, far_lon], [first_lat, far_lat], color=far_color,
                linewidth=2.2, alpha=0.9, zorder=4)

        # Label with the distance, placed at the midpoint of that line
        mid_lon = (first_lon + far_lon) / 2
        mid_lat = (first_lat + far_lat) / 2
        dist_label = f"Max distance: {format_distance(farthest_dist)}"
        ax.annotate(
            dist_label,
            xy=(mid_lon, mid_lat),
            xytext=(8, 8),
            textcoords="offset points",
            fontsize=9,
            fontweight="bold",
            color="black",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="white",
                      edgecolor=far_color, alpha=0.85),
            zorder=6,
        )

    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.set_title(csv_path)
    ax.legend()
    ax.set_aspect("equal", adjustable="datalim")

    if satellite:
        if not HAS_CONTEXTILY:
            print("contextily is not installed. Install it with:\n"
                  "    pip install contextily\n"
                  "then re-run with --satellite.")
            sys.exit(1)
        # Give the imagery a little breathing room around the points
        lon_pad = (max(bound_lons) - min(bound_lons)) * 0.1 or 0.0005
        lat_pad = (max(bound_lats) - min(bound_lats)) * 0.1 or 0.0005
        ax.set_xlim(min(bound_lons) - lon_pad, max(bound_lons) + lon_pad)
        ax.set_ylim(min(bound_lats) - lat_pad, max(bound_lats) + lat_pad)
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
    parser.add_argument("--gpx", default=None,
                         help="Path to a GPX file. Its track/route/waypoints are plotted "
                              "as small white dots connected by thin white lines, drawn "
                              "first so every other layer sits on top of it.")
    args = parser.parse_args()

    points = load_points(args.csv_path)
    #plot_points(points, args.output, satellite=args.satellite)
    plot_points(points, args.csv_path, args.output, satellite=True, gpx_path=args.gpx) # always add satellite background


if __name__ == "__main__":
    main()
