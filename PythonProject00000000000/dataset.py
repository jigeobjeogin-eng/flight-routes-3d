import pandas as pd

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