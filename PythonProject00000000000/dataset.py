import pandas as pd
import requests
import io



def get_airway_data(np, lat_lon_to_xyz, EARTH_RADIUS, POINTS_PER_ARC):
    print("Fetching and Cleaning OpenFlights Data...")
    try:
        a_url = "https://raw.githubusercontent.com/jpatokal/openflights/master/data/airports.dat"
        r_url = "https://raw.githubusercontent.com/jpatokal/openflights/master/data/routes.dat"

        # Airport IDs are in column 0, Lat in 6, Lon in 7
        airports = pd.read_csv(a_url, header=None,
                               usecols=[0, 6, 7],
                               names=['id', 'lat', 'lon'],
                               index_col='id',
                               na_values='\\N')

        # Route Source ID is column 3, Destination ID is column 5
        # We use usecols=[3, 5] instead of [2, 4]
        routes = pd.read_csv(r_url, header=None,
                             usecols=[3, 5],
                             names=['src_id', 'dst_id'],
                             na_values='\\N')

        # Drop rows with missing IDs and convert to int
        routes = routes.dropna(subset=['src_id', 'dst_id'])
        routes['src_id'] = routes['src_id'].astype(int)
        routes['dst_id'] = routes['dst_id'].astype(int)

        # Merge source coords
        routes = routes.merge(airports, left_on='src_id', right_index=True)
        # Merge destination coords
        routes = routes.merge(airports, left_on='dst_id', right_index=True, suffixes=('_src', '_dst'))

        print(f"Merge successful! Valid routes found: {len(routes)}")

        # Take the first 15,000 for a dense but performant sphere
        data = routes[['lat_src', 'lon_src', 'lat_dst', 'lon_dst']].values[:15000]

        all_points = []
        for r in data:
            p1 = np.array(lat_lon_to_xyz(r[0], r[1], EARTH_RADIUS))
            p2 = np.array(lat_lon_to_xyz(r[2], r[3], EARTH_RADIUS))

            for i in range(POINTS_PER_ARC):
                t = i / (POINTS_PER_ARC - 1)
                interp = p1 * (1 - t) + p2 * t
                norm = np.linalg.norm(interp)
                # Apply arc lift (Great Circle approximation)
                alt = np.sin(t * np.pi) * 0.15
                all_points.append((interp / norm) * (EARTH_RADIUS + alt))

        return np.array(all_points, dtype='float32')

    except Exception as e:
        print(f"Process failed: {e}")
        # Crosshair fallback
        return np.array([[0, 0, 0], [1, 0, 0], [-1, 0, 0], [0, 1, 0], [0, -1, 0], [0, 0, 1], [0, 0, -1]],
                        dtype='float32')
