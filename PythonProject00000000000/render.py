import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GL import shaders
import numpy as np
import pandas as pd
import dataset

# --- Project Config ---
WINDOW_SIZE = (1280, 720)
EARTH_RADIUS = 3.0
POINTS_PER_ARC = 50  # Resolution of each flight path


def lat_lon_to_xyz(lat, lon, r):
    phi = np.radians(90 - lat)
    theta = np.radians(lon + 180)
    x = r * np.sin(phi) * np.cos(theta)
    y = r * np.cos(phi)
    z = r * np.sin(phi) * np.sin(theta)
    return [x, y, z]


def get_mouse_ray():
    """Converts 2D mouse position to a 3D direction vector."""
    mx, my = pygame.mouse.get_pos()

    # Normalized Device Coordinates
    x = (2.0 * mx) / WINDOW_SIZE[0] - 1.0
    y = 1.0 - (2.0 * my) / WINDOW_SIZE[1]

    # We create a ray pointing "into" the screen
    ray_clip = np.array([x, y, -1.0, 1.0])

    # To be truly accurate with rotation, we would multiply by
    # the inverse of our rotation matrices here.
    return ray_clip[:3]

def proximity_glow(rot_x,rot_y , zoom_level,base_particle_size,vbo,vertex_data):
    # ... inside your while loop ...
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()
    glTranslatef(0, 0, zoom_level)
    glRotatef(rot_x, 1, 0, 0)
    glRotatef(rot_y, 0, 1, 0)

    # INTERACTION: Pulse effect when mouse is near center
    mx, my = pygame.mouse.get_pos()
    center_dist = np.linalg.norm(np.array([mx - WINDOW_SIZE[0] / 2, my - WINDOW_SIZE[1] / 2]))

    # If mouse is near the middle of the screen, brighten the routes
    hover_glow = max(0.3, 1.0 - (center_dist / 400.0))

    glPointSize(base_particle_size)

    # Apply the dynamic glow color
    glColor4f(0.0, 0.7 * hover_glow, 1.0 * hover_glow, 0.3 * hover_glow)

    glEnableClientState(GL_VERTEX_ARRAY)
    glBindBuffer(GL_ARRAY_BUFFER, vbo)
    glVertexPointer(3, GL_FLOAT, 0, None)
    glDrawArrays(GL_POINTS, 0, len(vertex_data))
    glDisableClientState(GL_VERTEX_ARRAY)

def smart_zoom(rot_x,rot_y , zoom_level,base_particle_size,vbo,vertex_data):

    zoom_percent = (zoom_level - (-50.0)) / ((-3.5) - (-50.0))
    zoom_percent = max(0.01, min(zoom_percent, 1.0))
    total_points_in_vbo = len(vertex_data)
    points_to_draw = int(total_points_in_vbo * zoom_percent)

    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()
    glTranslatef(0, 0, zoom_level)
    glRotatef(rot_x, 1, 0, 0)
    glRotatef(rot_y, 0, 1, 0)

    glPointSize(base_particle_size)
    glColor4f(0.0, 0.7, 1.0, 0.3)

    glEnableClientState(GL_VERTEX_ARRAY)
    glBindBuffer(GL_ARRAY_BUFFER, vbo)
    glVertexPointer(3, GL_FLOAT, 0, None)

    # 2. Draw only the subset of points based on zoom
    glDrawArrays(GL_POINTS, 0, points_to_draw)

    glDisableClientState(GL_VERTEX_ARRAY)



def main():
    global POINTS_PER_ARC
    pygame.init()
    pygame.display.set_mode(WINDOW_SIZE, DOUBLEBUF | OPENGL)
    pygame.display.set_caption("Global Transportation Tree - AIR PHASE")

    # --- Matrix Setup ---
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(45, (WINDOW_SIZE[0] / WINDOW_SIZE[1]), 0.1, 100.0)
    glMatrixMode(GL_MODELVIEW)

    glEnable(GL_DEPTH_TEST)
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE)
    glEnable(GL_POINT_SMOOTH)
    glClearColor(0, 0, 0, 1)

    # --- Initial Point Scaling ---
    # Coefficients: [Constant, Linear, Quadratic]
    # Increasing the 3rd value (Quadratic) makes distant points shrink faster
    attenuation = [0.0, 0.0, 0.01]
    glPointParameterfv(GL_POINT_DISTANCE_ATTENUATION, attenuation)

    vertex_data = dataset.get_airway_data(np, lat_lon_to_xyz, EARTH_RADIUS, POINTS_PER_ARC)
    vbo = glGenBuffers(1)
    glBindBuffer(GL_ARRAY_BUFFER, vbo)
    glBufferData(GL_ARRAY_BUFFER, vertex_data.nbytes, vertex_data, GL_STATIC_DRAW)

    # --- State Variables ---
    rot_x, rot_y = 0, 0
    zoom_level = -12.0
    base_particle_size = 1.0  # Default starting size
    clock = pygame.time.Clock()

    while True:


        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return

            # --- Zooming ---
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 4: zoom_level += 0.5
                if event.button == 5: zoom_level -= 0.5
                zoom_level = min(-3.5, max(zoom_level, -50.0))
                POINTS_PER_ARC = 10 + 3* zoom_level

            # --- CUSTOMIZATION: Particle Size Control ---
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    base_particle_size += 0.1
                if event.key == pygame.K_DOWN:
                    base_particle_size -= 0.1

                # Keep size within a visible range
                base_particle_size = max(0.1, min(base_particle_size, 100.0))
                print(f"Current Particle Base Size: {base_particle_size}")

            if event.type == pygame.MOUSEMOTION and pygame.mouse.get_pressed()[0]:
                dx, dy = event.rel
                rot_y += dx * 0.3
                rot_x += dy * 0.3



        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        glTranslatef(0, 0, zoom_level)
        glRotatef(rot_x, 1, 0, 0)
        glRotatef(rot_y, 0, 1, 0)

        # Apply the customized size
        glPointSize(base_particle_size)

        # Render
        glColor4f(0.0, 0.7, 1.0, 0.3)
        glEnableClientState(GL_VERTEX_ARRAY)
        glBindBuffer(GL_ARRAY_BUFFER, vbo)
        glVertexPointer(3, GL_FLOAT, 0, None)
        glDrawArrays(GL_POINTS, 0, len(vertex_data))
        glDisableClientState(GL_VERTEX_ARRAY)

        proximity_glow(rot_x, rot_y, zoom_level, base_particle_size, vbo, vertex_data)
        smart_zoom(rot_x,rot_y , zoom_level,base_particle_size,vbo,vertex_data)


        pygame.display.flip()
        clock.tick(60)


if __name__ == "__main__":
    main()