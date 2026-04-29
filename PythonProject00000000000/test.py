import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import numpy as np
import pandas as pd
from TextBox import TextBox

# --- Project Config ---
WINDOW_SIZE = (1280, 720)
EARTH_RADIUS = 3.0
POINTS_PER_ARC = 10


def lat_lon_to_xyz(lat, lon, r):
    phi = np.radians(90 - lat)
    theta = np.radians(lon + 180)
    x = r * np.sin(phi) * np.cos(theta)
    y = r * np.cos(phi)
    z = r * np.sin(phi) * np.sin(theta)
    return [x, y, z]


def get_airway_data():
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


def main():
    pygame.init()
    pygame.display.set_mode(WINDOW_SIZE, DOUBLEBUF | OPENGL)
    pygame.display.set_caption("Global Transportation Tree - AIR PHASE")

    # --- 1. Set up the "Lens" (Projection Matrix) ---
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(45, (WINDOW_SIZE[0] / WINDOW_SIZE[1]), 0.1, 100.0)

    # --- 2. Switch to "World" (Modelview Matrix) ---
    glMatrixMode(GL_MODELVIEW)

    glEnable(GL_DEPTH_TEST)
    glClearColor(0, 0, 0, 1)

    vertex_data = get_airway_data()
    vbo = glGenBuffers(1)
    glBindBuffer(GL_ARRAY_BUFFER, vbo)
    glBufferData(GL_ARRAY_BUFFER, vertex_data.nbytes, vertex_data, GL_STATIC_DRAW)

    info_box = TextBox(x=20, y=WINDOW_SIZE[1] - 140, width=250, height=120)
    # You can set initial multiline text
    info_box.set_text("Global Network Mode\nTotal Routes: 15,000\nStatus: Active")

    rot_x, rot_y = 0, 0
    zoom_level = -12.0
    clock = pygame.time.Clock()

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit();
                return

            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 4: zoom_level += 0.5
                if event.button == 5: zoom_level -= 0.5
                zoom_level = min(-4.0, max(zoom_level, -50.0))

            if event.type == pygame.MOUSEMOTION and pygame.mouse.get_pressed()[0]:
                dx, dy = event.rel
                rot_y += dx * 0.3
                rot_x += dy * 0.3

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        # --- 3. Position the Camera ---
        glLoadIdentity()  # Resets only the Modelview matrix
        glTranslatef(0, 0, zoom_level)
        glRotatef(rot_x, 1, 0, 0)
        glRotatef(rot_y, 0, 1, 0)

        # --- 4. Draw ---
        glPointSize(1.5)
        glColor3f(0.0, 0.7, 1.0)
        glEnableClientState(GL_VERTEX_ARRAY)
        glBindBuffer(GL_ARRAY_BUFFER, vbo)
        glVertexPointer(3, GL_FLOAT, 0, None)
        glDrawArrays(GL_POINTS, 0, len(vertex_data))
        glDisableClientState(GL_VERTEX_ARRAY)

        pygame.display.flip()
        clock.tick(60)


if __name__ == "__main__":
    main()