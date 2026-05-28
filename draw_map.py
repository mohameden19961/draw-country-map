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
from shapely.geometry import MultiPolygon, Polygon
import numpy as np


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


def compute_area_km2(geom):
    centroid = geom.centroid
    try:
        from pyproj import Proj
        lon, lat = centroid.x, centroid.y
        proj_str = f'+proj=laea +lat_0={lat} +lon_0={lon} +x_0=0 +y_0=0 +ellps=WGS84 +units=m +no_defs'
        proj = Proj(proj_str)
        from shapely.ops import transform
        projected = transform(lambda x, y: proj(x, y), geom)
        return projected.area / 1_000_000
    except Exception:
        return None


def format_number(n):
    if n is None:
        return 'N/A'
    if n >= 1_000_000_000:
        return f'{n / 1_000_000_000:.1f}B'
    if n >= 1_000_000:
        return f'{n / 1_000_000:.1f}M'
    if n >= 1_000:
        return f'{n / 1_000:.0f}K'
    return f'{n:.0f}'


def get_country_info(record):
    area_km2 = compute_area_km2(record.attr_geom) if hasattr(record, 'attr_geom') else None
    lines = []
    formal = record.attributes.get('FORMAL_EN', '')
    if formal and formal != '-99':
        lines.append(formal)
    pop = record.attributes.get('POP_EST')
    if pop and pop != -99:
        lines.append(f'Population: {format_number(pop)}')
    gdp = record.attributes.get('GDP_MD')
    if gdp and gdp != -99:
        lines.append(f'GDP: ${format_number(gdp * 1_000_000)}')
    continent = record.attributes.get('CONTINENT', '')
    if continent and continent != '-99':
        lines.append(f'Continent: {continent}')
    subregion = record.attributes.get('SUBREGION', '')
    if subregion and subregion != '-99':
        lines.append(f'Region: {subregion}')
    return '\n'.join(lines)


def draw_country(country_name):
    if country_name.lower() == 'israel':
        print("The occupied Palestinian territories are part of Palestine.")
        sys.exit(1)

    resolution = '10m'
    shp = natural_earth(resolution=resolution, category='cultural', name='admin_0_countries')
    reader = Reader(shp)

    countries = []
    match_record = None
    all_country_geoms = []
    for geom, record in zip(reader.geometries(), reader.records()):
        name = record.attributes.get('NAME', record.attributes.get('ADMIN', ''))
        if name.lower() == country_name.lower():
            countries.append(geom)
            match_record = record
            all_country_geoms.append(geom)

    if not countries:
        for geom, record in zip(reader.geometries(), reader.records()):
            name = record.attributes.get('NAME', record.attributes.get('ADMIN', ''))
            if country_name.lower() in name.lower():
                countries.append(geom)
                if match_record is None:
                    match_record = record
                all_country_geoms.append(geom)

    if not countries:
        print(f"Country '{country_name}' not found.")
        sys.exit(1)

    if country_name.lower() == 'palestine':
        for geom, record in zip(reader.geometries(), reader.records()):
            name = record.attributes.get('NAME', record.attributes.get('ADMIN', ''))
            if name.lower() == 'israel':
                countries.append(geom)
                all_country_geoms.append(geom)

    polygons = []
    for g in countries:
        if isinstance(g, MultiPolygon):
            polygons.extend(list(g.geoms))
        else:
            polygons.append(g)
    combined = MultiPolygon(polygons)
    bounds = combined.bounds

    country_geom = MultiPolygon([g for g in all_country_geoms if isinstance(g, Polygon)] +
                               [g for multi in all_country_geoms if isinstance(multi, MultiPolygon)
                                for g in multi.geoms])
    if match_record:
        match_record.attr_geom = country_geom

    fig = plt.figure(figsize=(14, 10))
    lon_range = bounds[2] - bounds[0]
    lat_range = bounds[3] - bounds[1]
    wide = lon_range > 120
    central_lon = (bounds[0] + bounds[2]) / 2
    if wide:
        ax = fig.add_subplot(1, 1, 1, projection=ccrs.Robinson(central_longitude=central_lon))
    else:
        ax = fig.add_subplot(1, 1, 1, projection=ccrs.PlateCarree())
    pad_lon = max(lon_range * (0.06 if wide else 0.1), 1)
    pad_lat = max(lat_range * 0.08, 1)
    ax.set_extent([bounds[0] - pad_lon, bounds[2] + pad_lon,
                   bounds[1] - pad_lat, bounds[3] + pad_lat], crs=ccrs.PlateCarree())

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

    if country_name.lower() == 'palestine':
        cities = [
            (31.7683, 35.2137, 'Al-Quds'),
            (31.5, 34.4667, 'Gaza'),
            (31.5333, 35.095, 'Al-Khalil'),
            (32.2167, 35.2667, 'Nablus'),
            (32.4667, 35.3, 'Jenin'),
            (31.9, 35.2, 'Ramallah'),
            (31.7031, 35.1956, 'Bethlehem'),
            (31.8667, 35.45, 'Jericho'),
            (32.3167, 35.0167, 'Tulkarm'),
            (32.1833, 34.9667, 'Qalqilya'),
            (32.0833, 35.1833, 'Salfit'),
            (32.3167, 35.3667, 'Tubas'),
            (32.05, 34.7667, 'Yafa'),
            (32.9333, 35.0833, 'Akka'),
            (32.8167, 34.9833, 'Haifa'),
            (32.7, 35.3, 'Al-Nasira'),
            (32.9667, 35.5, 'Safad'),
            (32.7833, 35.5333, 'Tabariyya'),
            (31.25, 34.7833, 'Bir al-Saba'),
            (31.6667, 34.5667, 'Asqalan'),
            (31.95, 34.9, 'Al-Lydd'),
            (31.9333, 34.8667, 'Al-Ramla'),
            (32.55, 35.85, 'Irbid'),
            (31.95, 35.9333, 'Amman'),
        ]
        for lat, lon, label in cities:
            ax.plot(lon, lat, 'o', color='#8b0000', markersize=3, transform=ccrs.PlateCarree())
            fs = 5.5 if 'Al-Quds' in label else 4
            ax.text(lon, lat, label, fontsize=fs, ha='center', va='bottom',
                    transform=ccrs.PlateCarree(),
                    bbox=dict(boxstyle='round,pad=0.15', facecolor='white',
                              edgecolor='#8b0000', alpha=0.75))

    elif admin_name:
        shp1 = natural_earth(resolution='10m', category='cultural', name='admin_1_states_provinces')
        reader1 = Reader(shp1)
        admin1_geoms = []
        admin1_data = []
        for geom, rec in zip(reader1.geometries(), reader1.records()):
            if rec.attributes.get('admin') == admin_name:
                admin1_geoms.append(geom)
                label = rec.attributes.get('name', '')
                if label:
                    area_km2 = compute_area_km2(geom)
                    admin1_data.append((geom.centroid, label, area_km2))
        if admin1_geoms:
            ax.add_geometries(
                admin1_geoms, crs=ccrs.PlateCarree(),
                facecolor='none', edgecolor='#666666', linewidth=0.6, alpha=0.7
            )
            if admin1_data:
                areas = [a for _, _, a in admin1_data if a]
                med_area = np.median(areas) if areas else 0
                min_area = med_area * 0.02 if med_area > 0 else 0
                max_label = 30
                if len(admin1_data) > 100:
                    max_label = int(len(admin1_data) * 0.25)
                elif len(admin1_data) > 50:
                    max_label = int(len(admin1_data) * 0.35)
                filtered = [(c, l, a) for c, l, a in admin1_data
                            if a is None or a >= min_area]
                filtered.sort(key=lambda x: -(x[2] or 0))
                filtered = filtered[:max_label]

                texts = []
                for centroid, label, _ in filtered:
                    ax.plot(centroid.x, centroid.y, 'o', color='#444444',
                            markersize=1.5, transform=ccrs.PlateCarree(),
                            zorder=5)
                    fs = max(2.5, min(5, 5 - len(filtered) / 40))
                    t = ax.text(centroid.x, centroid.y, label, fontsize=fs,
                                ha='center', va='center', transform=ccrs.PlateCarree(),
                                bbox=dict(boxstyle='round,pad=0.08', facecolor='white',
                                          edgecolor='none', alpha=0.6),
                                zorder=6)
                    texts.append(t)

                if len(texts) > 5:
                    try:
                        from adjustText import adjust_text
                        adjust_text(texts, ax=ax, force_text=0.3,
                                    force_static=0.3, force_pull=0.2,
                                    ensure_inside_axes=False,
                                    avoid_self=False,
                                    autoalign='xy',
                                    expand=(1.3, 1.5))
                    except Exception:
                        pass

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

    if match_record:
        info_text = get_country_info(match_record)
        if info_text:
            ax_info = fig.add_axes([0.82, 0.82 - 0.08 - 0.05, 0.16, 0.12], anchor='NE', zorder=10)
            ax_info.axis('off')
            ax_info.text(0, 1, info_text, fontsize=6.5, va='top', ha='left',
                         transform=ax_info.transAxes,
                         bbox=dict(boxstyle='round,pad=0.4', facecolor='white',
                                   edgecolor='#333333', alpha=0.85))

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
