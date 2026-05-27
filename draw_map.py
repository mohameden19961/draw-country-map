#!/usr/bin/env python3
"""Draw a map of a given country using cartopy, with its flag."""
import sys
import os
import urllib.request
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from cartopy.io.shapereader import natural_earth, Reader
from shapely.geometry import MultiPolygon


def fetch_flag(iso_code):
    if not iso_code:
        return None
    url = f"https://flagcdn.com/w640/{iso_code.lower()}.png"
    cache_dir = os.path.join(os.path.dirname(__file__), '.flag_cache')
    os.makedirs(cache_dir, exist_ok=True)
    cache_path = os.path.join(cache_dir, f"{iso_code.lower()}.png")
    if os.path.exists(cache_path):
        return cache_path
    try:
        urllib.request.urlretrieve(url, cache_path)
        return cache_path
    except Exception:
        return None


def draw_country(country_name):
    resolution = '10m'
    shp = natural_earth(resolution=resolution, category='cultural', name='admin_0_countries')
    reader = Reader(shp)

    countries = []
    match_record = None
    for geom, record in zip(reader.geometries(), reader.records()):
        name = record.attributes.get('NAME', record.attributes.get('ADMIN', ''))
        if name.lower() == country_name.lower():
            countries.append(geom)
            match_record = record

    if not countries:
        for geom, record in zip(reader.geometries(), reader.records()):
            name = record.attributes.get('NAME', record.attributes.get('ADMIN', ''))
            if country_name.lower() in name.lower():
                countries.append(geom)
                if match_record is None:
                    match_record = record

    if not countries:
        print(f"Country '{country_name}' not found.")
        sys.exit(1)

    combined = MultiPolygon(countries) if len(countries) > 1 else countries[0]
    bounds = combined.bounds

    fig = plt.figure(figsize=(14, 10))
    ax = fig.add_subplot(1, 1, 1, projection=ccrs.PlateCarree())

    pad = max((bounds[2] - bounds[0]) * 0.1, 1)
    ax.set_extent([bounds[0] - pad, bounds[2] + pad, bounds[1] - pad, bounds[3] + pad], crs=ccrs.PlateCarree())

    ax.add_feature(cfeature.OCEAN, facecolor='#c6e2ff')
    ax.add_feature(cfeature.LAND, facecolor='#f5f5dc', alpha=0.4)
    ax.add_feature(cfeature.COASTLINE, linewidth=0.4, edgecolor='#555555')
    ax.add_feature(cfeature.BORDERS, linewidth=0.4, edgecolor='#555555', alpha=0.6)
    ax.add_feature(cfeature.LAKES, facecolor='#c6e2ff', edgecolor='#555555', linewidth=0.3)
    ax.add_feature(cfeature.RIVERS, linewidth=0.3, edgecolor='#87ceeb')

    ax.add_geometries(
        countries, crs=ccrs.PlateCarree(),
        facecolor='#90ee90', edgecolor='#2e8b57', linewidth=1.5, alpha=0.85
    )

    admin_name = match_record.attributes.get('ADMIN', '') if match_record else ''
    if admin_name:
        shp1 = natural_earth(resolution='10m', category='cultural', name='admin_1_states_provinces')
        reader1 = Reader(shp1)
        admin1_geoms = []
        admin1_labels = []
        for geom, rec in zip(reader1.geometries(), reader1.records()):
            if rec.attributes.get('admin') == admin_name:
                admin1_geoms.append(geom)
                admin1_labels.append((geom.centroid, rec.attributes.get('name', '')))
        if admin1_geoms:
            ax.add_geometries(
                admin1_geoms, crs=ccrs.PlateCarree(),
                facecolor='none', edgecolor='#666666', linewidth=0.6, alpha=0.7
            )
            for centroid, label in admin1_labels:
                if label:
                    ax.plot(centroid.x, centroid.y, 'o', color='#444444', markersize=1.5,
                            transform=ccrs.PlateCarree())
                    ax.text(centroid.x, centroid.y, label, fontsize=3.5,
                            ha='center', va='center', transform=ccrs.PlateCarree(),
                            bbox=dict(boxstyle='round,pad=0.1', facecolor='white',
                                      edgecolor='none', alpha=0.5))

    ax.set_title(country_name, fontsize=18, fontweight='bold')
    ax.set_xlabel('Longitude')
    ax.set_ylabel('Latitude')
    ax.gridlines(draw_labels=True, linestyle='--', alpha=0.4, linewidth=0.3)

    iso = None
    if match_record:
        iso = match_record.attributes.get('ISO_A2_EH')
        if not iso or iso == '-99':
            iso = match_record.attributes.get('ISO_A2')
        if not iso or iso == '-99':
            iso = match_record.attributes.get('ADM0_A3')
    flag_path = fetch_flag(iso)
    if flag_path:
        flag_img = mpimg.imread(flag_path)
        ax_flag = fig.add_axes([0.82, 0.82, 0.12, 0.08], anchor='NE', zorder=10)
        ax_flag.imshow(flag_img)
        ax_flag.axis('off')

    out = f"{country_name.lower().replace(' ', '_')}_map.png"
    plt.savefig(out, dpi=300, bbox_inches='tight')
    print(f"Map saved as {out}")
    plt.close(fig)


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <country_name>")
        print(f"Example: {sys.argv[0]} France")
        sys.exit(1)
    draw_country(sys.argv[1])
