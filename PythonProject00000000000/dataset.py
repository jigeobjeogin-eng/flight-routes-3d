import pandas as pd
import geopandas as gpd
from shapely.geometry import Polygon, MultiPolygon
import numpy as np

def get_airway_data(np, lat_lon_to_xyz, EARTH_RADIUS, POINTS_PER_ARC):
    print("Fetching and Cleaning OpenFlights Data...")
    try:
        a_url = "https://raw.githubusercontent.com/jpatokal/openflights/master/data/airports.dat"
        r_url = "https://raw.githubusercontent.com/jpatokal/openflights/master/data/routes.dat"

        # 1. Load airports but keep City and Name columns now!
        # Col 0: ID, Col 1: Name, Col 2: City, Col 6: Lat, Col 7: Lon
        airports = pd.read_csv(a_url, header=None,
                               usecols=[0, 1, 2, 6, 7],
                               names=['id', 'name', 'city', 'lat', 'lon'],
                               index_col='id',
                               na_values='\\N')

        routes = pd.read_csv(r_url, header=None,
                             usecols=[3, 5],
                             names=['src_id', 'dst_id'],
                             na_values='\\N')

        routes = routes.dropna(subset=['src_id', 'dst_id'])
        routes['src_id'] = routes['src_id'].astype(int)
        routes['dst_id'] = routes['dst_id'].astype(int)

        # Merge for the lines
        routes_merged = routes.merge(airports, left_on='src_id', right_index=True)
        routes_merged = routes_merged.merge(airports, left_on='dst_id', right_index=True, suffixes=('_src', '_dst'))

        print(f"Merge successful! Valid routes found: {len(routes_merged)}")

        # --- PART A: GENERATE PARTICLES ---
        data = routes_merged[['lat_src', 'lon_src', 'lat_dst', 'lon_dst']].values
        all_points = []
        for r in data:
            p1 = np.array(lat_lon_to_xyz(r[0], r[1], EARTH_RADIUS))
            p2 = np.array(lat_lon_to_xyz(r[2], r[3], EARTH_RADIUS))
            for i in range(POINTS_PER_ARC):
                t = i / (POINTS_PER_ARC - 1)
                interp = p1 * (1 - t) + p2 * t
                norm = np.linalg.norm(interp)
                alt = np.sin(t * np.pi) * 0.15
                all_points.append((interp / norm) * (EARTH_RADIUS + alt))

        vertex_array = np.array(all_points, dtype='float32')

        # --- PART B: GENERATE LABELS ---
        # Get unique airports that actually have routes
        active_ids = list(set(routes['src_id'].unique()) | set(routes['dst_id'].unique()))
        active_airports = airports.loc[airports.index.isin(active_ids)] # Top 300 to start

        label_data = []
        for id, row in active_airports.iterrows():
            pos = lat_lon_to_xyz(row['lat'], row['lon'], EARTH_RADIUS)
            label_data.append({
                'pos': pos,
                'text': f"{row['city']}" # or row['name']
            })

        # Return both!
        return vertex_array, label_data

    except Exception as e:
        print(f"Process failed: {e}")
        return np.array([[0,0,0]], dtype='float32'), []





def get_world_borders(lat_lon_to_xyz, r):
    print("Loading World Borders (Solid Lines)...")
    # Load Natural Earth low-res dataset built into GeoPandas
    try:
        world = gpd.read_file(gpd.datasets.get_path('naturalearth_lowres'))
    except AttributeError:
        # Fallback for newer GeoPandas versions
        import geodatasets
        world = gpd.read_file(geodatasets.get_path('naturalearth.land'))

    line_vertices = []

    for _, row in world.iterrows():
        geom = row.geometry

        # Handle both single Polygons and MultiPolygons (e.g., islands, Japan, UK)
        polys = [geom] if isinstance(geom, Polygon) else geom.geoms

        for poly in polys:
            coords = list(poly.exterior.coords)

            # Convert all 2D lat/lon to 3D sphere coordinates
            # Render slightly below the airways (0.99)
            pts = [lat_lon_to_xyz(lat, lon, r * 0.99) for lon, lat in coords]

            # Create pairs for GL_LINES
            for i in range(len(pts) - 1):
                line_vertices.append(pts[i])  # Start of segment
                line_vertices.append(pts[i + 1])  # End of segment

    return np.array(line_vertices, dtype='float32')


# --- NEW: Standalone Search System ---
_search_airports = None
_search_routes = None


def get_filtered_airway_data(np_module, lat_lon_to_xyz, r, points_per_arc, search_query):
    """A completely separate function dedicated to searching, leaving the original intact."""
    global _search_airports, _search_routes

    # 1. Download and cache data specifically for the search engine (runs once)
    if _search_airports is None or _search_routes is None:
        print("Initializing Search Engine Cache...")
        import pandas as pd
        a_url = "https://raw.githubusercontent.com/jpatokal/openflights/master/data/airports.dat"
        r_url = "https://raw.githubusercontent.com/jpatokal/openflights/master/data/routes.dat"

        _search_airports = pd.read_csv(a_url, header=None,
                                       usecols=[0, 1, 2, 4, 6, 7],
                                       names=['id', 'name', 'city', 'iata', 'lat', 'lon'],
                                       index_col='id', na_values='\\N')
        _search_airports.fillna('', inplace=True)

        routes = pd.read_csv(r_url, header=None, usecols=[3, 5], names=['src_id', 'dst_id'], na_values='\\N')
        routes = routes.dropna().astype(int)
        routes = routes.merge(_search_airports[['lat', 'lon']], left_on='src_id', right_index=True)
        _search_routes = routes.merge(_search_airports[['lat', 'lon']], left_on='dst_id', right_index=True,
                                      suffixes=('_src', '_dst'))

    # 2. Perform the text search
    sq = search_query.strip().lower()
    matched_airports = _search_airports[
        _search_airports['name'].str.lower().str.contains(sq) |
        _search_airports['city'].str.lower().str.contains(sq) |
        (_search_airports['iata'].str.lower() == sq)
        ]
    matched_ids = matched_airports.index.values

    filtered_routes = _search_routes[
        _search_routes['src_id'].isin(matched_ids) | _search_routes['dst_id'].isin(matched_ids)]
    data_to_render = filtered_routes[['lat_src', 'lon_src', 'lat_dst', 'lon_dst']].values

    if len(data_to_render) == 0:
        return np_module.zeros((0, 3), dtype='float32')

    # 3. Generate the 3D curves
    all_points = []
    for row in data_to_render:
        p1 = np_module.array(lat_lon_to_xyz(row[0], row[1], r))
        p2 = np_module.array(lat_lon_to_xyz(row[2], row[3], r))
        for i in range(points_per_arc):
            t = i / (points_per_arc - 1)
            interp = p1 * (1 - t) + p2 * t
            norm = np_module.linalg.norm(interp)
            alt = np_module.sin(t * np_module.pi) * 0.15
            all_points.append((interp / norm) * (r + alt))

    return np_module.array(all_points, dtype='float32')