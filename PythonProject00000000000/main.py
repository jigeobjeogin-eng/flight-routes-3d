import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import numpy as np
import dataset

# --- Project Config ---
WINDOW_SIZE = (2560, 1440)
EARTH_RADIUS = 3.0
POINTS_PER_ARC = 400




def lat_lon_to_xyz(lat, lon, r):
    phi = np.radians(90 - lat)
    theta = np.radians(lon + 180)
    x = r * np.sin(phi) * np.cos(theta)
    y = r * np.cos(phi)
    z = r * np.sin(phi) * np.sin(theta)
    return [x, y, z]

def draw_flight_routes(base_particle_size,hover_glow,vbo,points_to_draw):
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE)
    glPointSize(base_particle_size)
    glColor4f(0.0, 0.7 * hover_glow, 1.0 * hover_glow, 0.3 * hover_glow)

    glEnableClientState(GL_VERTEX_ARRAY)
    glBindBuffer(GL_ARRAY_BUFFER, vbo)
    glVertexPointer(3, GL_FLOAT, 0, None)
    glDrawArrays(GL_POINTS, 0, points_to_draw)
    glDisableClientState(GL_VERTEX_ARRAY)
    glBindBuffer(GL_ARRAY_BUFFER, 0)

def draw_hub_dots(zoom_level, airport_labels):
    if zoom_level > -10.0:
        glPointSize(4.0)
        glColor4f(1.0, 1.0, 1.0, 1.0)
        glBegin(GL_POINTS)
        for hub in airport_labels:
            glVertex3f(hub['pos'][0], hub['pos'][1], hub['pos'][2])
        glEnd()

def draw_labels(zoom_level, airport_labels,to_render):
    if zoom_level > -18.0:
        modelview = glGetDoublev(GL_MODELVIEW_MATRIX)
        projection = glGetDoublev(GL_PROJECTION_MATRIX)
        viewport = glGetIntegerv(GL_VIEWPORT)

        for hub in airport_labels:
            if 'tex_id' not in hub: continue
            try:
                sx, sy, sz = gluProject(hub['pos'][0], hub['pos'][1], hub['pos'][2],
                                        modelview, projection, viewport)

                # sz < 0.7 filters for the front of the globe
                if 0 < sz < 1:
                    to_render.append({
                        'depth': sz,
                        'hub_ref': hub  # THIS IS THE KEY LINK

                    })
            except:
                continue

        to_render.sort(key=lambda x: x['depth'])
        to_render = to_render[:90]

        # --- STEP 2: RENDERING ---

        # --- STEP 2: DYNAMICALLY SCALED 3D RENDERER ---
        if to_render:
            glEnable(GL_TEXTURE_2D)
            glEnable(GL_BLEND)
            glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
            glColor4f(1, 1, 1, 1)

            mv = glGetDoublev(GL_MODELVIEW_MATRIX)
            right = np.array([mv[0][0], mv[1][0], mv[2][0]])
            up = np.array([mv[0][1], mv[1][1], mv[2][1]])

            for item in to_render:
                hub = item['hub_ref']
                glBindTexture(GL_TEXTURE_2D, hub['tex_id'])

                p = np.array(hub['pos']) * 1.05

                # --- THE DYNAMIC FIX ---
                # Since the camera is at 0,0,0 and the world is moved by zoom_level:
                # We use the absolute value of zoom_level to determine 'distance'
                # As zoom_level goes from -3.5 to -50.0, the labels will scale up
                # to stay visible.

                actual_dist = abs(zoom_level)**2

                # Scale logic: Base_Size * Distance * Constant
                # Adjust 0.001 to find your "sweet spot" for text size
                dynamic_scale = actual_dist * 0.0005

                w = hub['w_base'] * dynamic_scale
                h = hub['h_base'] * dynamic_scale

                glBegin(GL_QUADS)
                glTexCoord2f(0, 0);
                glVertex3f(p[0], p[1], p[2])
                glTexCoord2f(1, 0);
                glVertex3f(p[0] + right[0] * w,
                           p[1] + right[1] * w,
                           p[2] + right[2] * w)
                glTexCoord2f(1, 1);
                glVertex3f(p[0] + right[0] * w + up[0] * h,
                           p[1] + right[1] * w + up[1] * h,
                           p[2] + right[2] * w + up[2] * h)
                glTexCoord2f(0, 1);
                glVertex3f(p[0] + up[0] * h,
                           p[1] + up[1] * h,
                           p[2] + up[2] * h)
                glEnd()

            glDisable(GL_TEXTURE_2D)

def draw_borders(rot_x,rot_y,zoom_level,show_border,border_vbo,border_data,earth_core):
    # --- DRAWING PHASE ---
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()
    glTranslatef(0, 0, zoom_level)
    glRotatef(rot_x, 1, 0, 0)
    glRotatef(rot_y, 0, 1, 0)

    # 0. DRAW THE OCCLUSION CORE (Blocks the back side)
    # Disable blending so it draws a solid black mask
    glDisable(GL_BLEND)
    glColor3f(0.0, 0.0, 0.0)  # Pitch black
    # Radius 2.94 ensures it sits just under borders (2.97) and air (3.0)
    gluSphere(earth_core, EARTH_RADIUS * 0.98, 32, 32)
    glEnable(GL_BLEND)  # Turn the glow effect back on for the data

    # 1. DRAW BORDERS (If enabled)
    if show_border:
        glLineWidth(1.0)
        glColor4f(0.7, 0.2, 0.1, 0.9)

        glEnableClientState(GL_VERTEX_ARRAY)
        glBindBuffer(GL_ARRAY_BUFFER, border_vbo)
        glVertexPointer(3, GL_FLOAT, 0, None)
        glDrawArrays(GL_LINES, 0, len(border_data))
        glDisableClientState(GL_VERTEX_ARRAY)

def main():
    pygame.init()
    pygame.display.set_mode(WINDOW_SIZE, DOUBLEBUF | OPENGL)
    pygame.display.set_caption("Global Transportation Tree - AIR PHASE")
    pygame.font.init()
    FONT = pygame.font.SysFont('Arial', 12)

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

    attenuation = [0.0, 0.0, 0.01]
    glPointParameterfv(GL_POINT_DISTANCE_ATTENUATION, attenuation)

    vertex_data, airport_labels = dataset.get_airway_data(np, lat_lon_to_xyz, EARTH_RADIUS, POINTS_PER_ARC)


    vbo = glGenBuffers(1)
    glBindBuffer(GL_ARRAY_BUFFER, vbo)
    glBufferData(GL_ARRAY_BUFFER, vertex_data.nbytes, vertex_data, GL_STATIC_DRAW)
    glBindBuffer(GL_ARRAY_BUFFER, 0)

    # Pre-generate label textures ONCE (not every frame)
    for hub in airport_labels:
        surf = FONT.render(hub['text'], True, (255, 255, 255), (0, 0, 0))
        w, h = surf.get_size()
        data = pygame.image.tostring(surf, "RGBA", True)
        tex_id = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, tex_id)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, w, h, 0, GL_RGBA, GL_UNSIGNED_BYTE, data)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        hub['tex_id'] = tex_id
        hub['w_base'] = w / h  # Aspect Ratio
        hub['h_base'] = 1.0  # Base Unit


    border_data = dataset.get_world_borders(lat_lon_to_xyz, EARTH_RADIUS)
    border_vbo = glGenBuffers(1)
    glBindBuffer(GL_ARRAY_BUFFER, border_vbo)
    glBufferData(GL_ARRAY_BUFFER, border_data.nbytes, border_data, GL_STATIC_DRAW)

    # Create the geometry for the invisible occlusion sphere
    earth_core = gluNewQuadric()
    gluQuadricNormals(earth_core, GLU_SMOOTH)

    # --- State ---
    rot_x, rot_y = 0, 0
    zoom_level = -12.0
    base_particle_size = 1.0
    total_points = len(vertex_data) // 3
    clock = pygame.time.Clock()
    show_borders = True


    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return

            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 4:
                    zoom_level = min(-3.5, zoom_level + 0.5)
                if event.button == 5:
                    zoom_level = max(-50.0, zoom_level - 0.5)

            # --- TOGGLE BORDERS (Press 'B') ---
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_b:
                    show_borders = not show_borders
                    print(f"Borders Visible: {show_borders}")


            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    base_particle_size = min(100.0, base_particle_size + 0.1)
                if event.key == pygame.K_DOWN:
                    base_particle_size = max(0.1, base_particle_size - 0.1)

            if event.type == pygame.MOUSEMOTION and pygame.mouse.get_pressed()[0]:
                dx, dy = event.rel
                rot_y += dx * 0.3
                rot_x += dy * 0.3

        # ── SINGLE RENDER PASS ──────────────────────────────────────────────
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        glTranslatef(0, 0, zoom_level)
        glRotatef(rot_x, 1, 0, 0)
        glRotatef(rot_y, 0, 1, 0)

        # Proximity glow: mouse near center brightens routes
        mx, my = pygame.mouse.get_pos()
        center_dist = np.linalg.norm(
            np.array([mx - WINDOW_SIZE[0] / 2, my - WINDOW_SIZE[1] / 2])
        )
        hover_glow = max(0.9, 1.0 - (center_dist / 800.0))

        # Smart zoom: draw fewer points when zoomed out
        zoom_percent = (zoom_level - (-50.0)) / ((-3.5) - (-50.0))
        zoom_percent = max(0.01, min(zoom_percent, 1.0))
        points_to_draw = max(1, int(total_points * zoom_percent))

        # --- DYNAMIC ALPHA BACKSIDE FADE ---
        # Define zoom range for the fade (e.g., starts at -20, fully opaque at -10)
        start_fade = -15.0
        end_fade = -5.0

        if zoom_level > start_fade:
            # Calculate alpha: 0.0 (transparent) to 1.0 (fully opaque)
            fade_range = end_fade - start_fade

            alpha = (zoom_level - start_fade) / fade_range
            alpha = max(0.0, min(1.0, alpha))  # Clamp between 0 and 1
            print(1- alpha)

            glEnable(GL_BLEND)
            # Use Standard Transparency for the "Shield"
            glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

            # Set the color to Black but with our dynamic Alpha
            glColor4f(0, 0, 0, 1 - alpha)

            # Create and draw the "Occlusion Shield"
            # It must be slightly smaller than the earth so it doesn't hide front routes
            quadric = gluNewQuadric()
            gluSphere(quadric, EARTH_RADIUS * 0.99, 64, 64)

            # Reset blending to Additive for the routes/particles
            glBlendFunc(GL_SRC_ALPHA, GL_ONE)

        # --- 1. Draw flight routes ---
        draw_borders(rot_x, rot_y, zoom_level, show_borders, border_vbo, border_data,earth_core)
        draw_flight_routes(base_particle_size, hover_glow, vbo, points_to_draw)

        # --- 2. Airport hub dots ---
        draw_hub_dots(zoom_level, airport_labels)

        # --- 3. LABELS ---
        to_render = []
        draw_labels(zoom_level, airport_labels, to_render)




        # ── END RENDER PASS ─────────────────────────────────────────────────

        pygame.display.flip()
        clock.tick(60)


if __name__ == "__main__":
    main()