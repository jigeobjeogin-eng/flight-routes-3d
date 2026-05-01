import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import numpy as np
import dataset
from TextBox import TextBox
import themes.default as colors
import math

#9.0



# --- Project Config ---
WINDOW_SIZE = (1300, 700)
EARTH_RADIUS = 3.0
POINTS_PER_ARC = 20

pygame.font.init()
UI_FONT = pygame.font.SysFont('Consolas', 18)

# Search Bar Dimensions
BAR_WIDTH = 400
BAR_HEIGHT = 40
BAR_X = (WINDOW_SIZE[0] - BAR_WIDTH) // 2
BAR_Y_MARGIN = 20


# check if the mouse clicks inside the box.
SEARCH_RECT = pygame.Rect(BAR_X, WINDOW_SIZE[1] - BAR_Y_MARGIN - BAR_HEIGHT, BAR_WIDTH, BAR_HEIGHT)


def draw_text_2d(x, y, text, font, color=colors.TEXT_DEFAULT):
    """Converts a Pygame text surface into raw pixels for OpenGL to draw."""
    if not text:
        return
    text_surface = font.render(text, True, color)
    # The 'True' argument flips the image vertically because OpenGL renders bottom-to-top
    text_data = pygame.image.tostring(text_surface, "RGBA", True)

    # Set the pixel position and draw
    glRasterPos2d(x, y)
    glDrawPixels(text_surface.get_width(), text_surface.get_height(), GL_RGBA, GL_UNSIGNED_BYTE, text_data)

def draw_ui(screen_width, screen_height, search_text, is_active):
    """Switches to 2D mode to draw the search UI, then switches back to 3D."""
    # --- Switch to 2D Orthographic Mode ---
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()  # Save 3D state
    glLoadIdentity()
    gluOrtho2D(0, screen_width, 0, screen_height)

    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()  # Save 3D state
    glLoadIdentity()

    # Disable depth testing so UI renders on top of everything
    glDisable(GL_DEPTH_TEST)
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

    # --- Draw Search Box Background ---
    if is_active:
        glColor4f(*colors.BAR_ACTIVE_BG)
    else:
        glColor4f(*colors.BAR_INACTIVE_BG)

    glBegin(GL_QUADS)
    glVertex2f(BAR_X, BAR_Y_MARGIN)
    glVertex2f(BAR_X + BAR_WIDTH, BAR_Y_MARGIN)
    glVertex2f(BAR_X + BAR_WIDTH, BAR_Y_MARGIN + BAR_HEIGHT)
    glVertex2f(BAR_X, BAR_Y_MARGIN + BAR_HEIGHT)
    glEnd()

    # --- Draw Search Box Outline ---
    if is_active:
        glColor4f(*colors.BAR_ACTIVE_OUTLINE)
    else:
        glColor4f(*colors.BAR_INACTIVE_OUTLINE)

    glLineWidth(2.0)
    glBegin(GL_LINE_LOOP)
    glVertex2f(BAR_X, BAR_Y_MARGIN)
    glVertex2f(BAR_X + BAR_WIDTH, BAR_Y_MARGIN)
    glVertex2f(BAR_X + BAR_WIDTH, BAR_Y_MARGIN + BAR_HEIGHT)
    glVertex2f(BAR_X, BAR_Y_MARGIN + BAR_HEIGHT)
    glEnd()

    # --- Draw Text ---
    display_text = search_text + ("_" if is_active else "")
    if not search_text and not is_active:
        display_text = "Click here to search airport (e.g. JFK)..."

    draw_text_2d(BAR_X + 15, BAR_Y_MARGIN + 12, display_text, UI_FONT)

    # --- Restore 3D Mode ---
    glEnable(GL_DEPTH_TEST)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE)

    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)
    glPopMatrix()

def lat_lon_to_xyz(lat, lon, r):
    phi = np.radians(90 - lat)
    theta = np.radians(lon + 180)
    x = r * np.sin(phi) * np.cos(theta)
    y = r * np.cos(phi)
    z = r * np.sin(phi) * np.sin(theta)
    return [x, y, z]

def draw_flight_routes(base_particle_size, hover_glow, vbo, points_to_draw):
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE)
    glPointSize(base_particle_size)
    r, g, b, a = colors.ROUTE_GLOW
    glColor4f(r, g * hover_glow, b * hover_glow, a * hover_glow)

    glEnableClientState(GL_VERTEX_ARRAY)
    glBindBuffer(GL_ARRAY_BUFFER, vbo)
    glVertexPointer(3, GL_FLOAT, 0, None)
    glDrawArrays(GL_POINTS, 0, points_to_draw)
    glDisableClientState(GL_VERTEX_ARRAY)
    glBindBuffer(GL_ARRAY_BUFFER, 0)

def draw_hub_dots(zoom_level, airport_labels):
    if zoom_level > -15.0:
        glPointSize(1.0)
        glColor4f(*colors.HUB_DOT)
        glBegin(GL_POINTS)
        for hub in airport_labels:
            px, py, pz = np.array(hub['pos']) * 1.01
            glVertex3f(px, py, pz)
        glEnd()

def draw_labels(zoom_level, airport_labels, to_render, show_labels):
    if show_labels:

        if zoom_level > -18.0:
            modelview = glGetDoublev(GL_MODELVIEW_MATRIX)
            projection = glGetDoublev(GL_PROJECTION_MATRIX)
            viewport = glGetIntegerv(GL_VIEWPORT)

            for hub in airport_labels:
                if 'tex_id' not in hub: continue
                try:
                    sx, sy, sz = gluProject(hub['pos'][0], hub['pos'][1], hub['pos'][2],
                                            modelview, projection, viewport)
                    if 0 < sz < 1:
                        to_render.append({
                            'depth': sz,
                            'hub_ref': hub

                        })
                except:
                    continue

            to_render.sort(key=lambda x: x['depth'])
            to_render = to_render[:90]



            # --- STEP 2: DYNAMICALLY SCALED 3D RENDERER ---
            if to_render:
                glEnable(GL_TEXTURE_2D)
                glEnable(GL_BLEND)
                glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
                glColor4f(*colors.LABEL_TINT)

                mv = glGetDoublev(GL_MODELVIEW_MATRIX)
                right = np.array([mv[0][0], mv[1][0], mv[2][0]])
                up = np.array([mv[0][1], mv[1][1], mv[2][1]])

                for item in to_render:
                    hub = item['hub_ref']
                    glBindTexture(GL_TEXTURE_2D, hub['tex_id'])

                    p = np.array(hub['pos']) * 1.05

                    actual_dist = abs(zoom_level) ** 2
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

def draw_borders(rot_x, rot_y, zoom_level, show_border, border_vbo, border_data, earth_core):
    # --- DRAWING PHASE ---
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()
    glTranslatef(0, 0, zoom_level)
    glRotatef(rot_x, 1, 0, 0)
    glRotatef(rot_y, 0, 1, 0)

    # 0. DRAW THE OCCLUSION CORE (Blocks the back side)
    glDisable(GL_BLEND)
    glColor3f(*colors.EARTH_CORE)
    gluSphere(earth_core, EARTH_RADIUS * 0.98, 32, 32)
    glEnable(GL_BLEND)

    # 1. DRAW BORDERS (If enabled)
    if show_border:
        glLineWidth(1.0)
        glColor4f(*colors.BORDER_LINE)

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
    search_query = ""
    is_filtered = False

    # --- Matrix Setup ---
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(45, (WINDOW_SIZE[0] / WINDOW_SIZE[1]), 0.1, 100.0)
    glMatrixMode(GL_MODELVIEW)

    glEnable(GL_DEPTH_TEST)
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE)
    glEnable(GL_POINT_SMOOTH)
    glClearColor(*colors.EARTH_CORE, 1)

    attenuation = [0.0, 0.0, 0.01]
    glPointParameterfv(GL_POINT_DISTANCE_ATTENUATION, attenuation)

    vertex_data, airport_labels = dataset.get_airway_data(np, lat_lon_to_xyz, EARTH_RADIUS, POINTS_PER_ARC)

    vbo = glGenBuffers(1)
    glBindBuffer(GL_ARRAY_BUFFER, vbo)
    glBufferData(GL_ARRAY_BUFFER, vertex_data.nbytes, vertex_data, GL_STATIC_DRAW)
    glBindBuffer(GL_ARRAY_BUFFER, 0)

    # Pre-generate label textures ONCE (not every frame)
    for hub in airport_labels:
        surf = FONT.render(hub['text'], True, colors.LABEL_TEXT_FG, colors.LABEL_TEXT_BG)
        w, h = surf.get_size()
        data = pygame.image.tostring(surf, "RGBA", True)
        tex_id = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, tex_id)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, w, h, 0, GL_RGBA, GL_UNSIGNED_BYTE, data)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        hub['tex_id'] = tex_id
        hub['w_base'] = w / h  # Aspect Ratio
        hub['h_base'] = 1.0    # Base Unit

    border_data = dataset.get_world_borders(lat_lon_to_xyz, EARTH_RADIUS)
    border_vbo = glGenBuffers(1)
    glBindBuffer(GL_ARRAY_BUFFER, border_vbo)
    glBufferData(GL_ARRAY_BUFFER, border_data.nbytes, border_data, GL_STATIC_DRAW)

    earth_core = gluNewQuadric()
    gluQuadricNormals(earth_core, GLU_SMOOTH)

    info_box = TextBox(x=1155, y=WINDOW_SIZE[1] - 1300, width=250, height=120)
    ap_list  = TextBox(x=2000, y=WINDOW_SIZE[1] / 2,    width=350,  height=0)

    # --- State ---
    rot_x, rot_y = 0, 0
    zoom_level = -12.0
    base_particle_size = 1.0
    total_points = len(vertex_data) // 3
    clock = pygame.time.Clock()
    show_borders = True
    show_labels  = True
    show_ui = True
    is_typing    = False

    # Setup for Infinite Mouse Rotation
    camera_locked = True
    center_x = WINDOW_SIZE[0] // 2
    center_y = WINDOW_SIZE[1] // 2

    # Start with the mouse hidden and locked to the center
    pygame.mouse.set_visible(False)
    pygame.mouse.set_pos(center_x, center_y)

    # Animation setup
    is_animating = False
    target_rot_x = 0.0
    target_rot_y = 0.0

    master_airport_labels = list(airport_labels)

    frame_dx = 0
    frame_dy = 0








    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return

            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1 and not camera_locked:
                    mx, my = pygame.mouse.get_pos()
                    if SEARCH_RECT.collidepoint(mx, my):
                        is_typing = True
                    else:
                        is_typing = False


                # Scroll Wheel Zoom
                if event.button == 4: zoom_level += 0.5
                if event.button == 5: zoom_level -= 0.5
                zoom_level = min(-3.5, max(zoom_level, -50.0))


            # --- NEW: Rotate purely on mouse movement ---

            # --- 2. KEYBOARD TYPING LOGIC ---
            if event.type == pygame.KEYDOWN:
                if is_typing:
                    if event.key == pygame.K_RETURN:
                        is_typing = False
                        clean_query = search_query.strip()

                        if clean_query == "":
                            search_query = ""
                            print("Clearing filter. Loading original network...")

                            original_data = dataset.get_airway_data(np, lat_lon_to_xyz, EARTH_RADIUS, POINTS_PER_ARC)

                            if isinstance(original_data, tuple):
                                vertex_data = original_data[0]
                            else:
                                vertex_data = original_data

                            if not isinstance(vertex_data, np.ndarray):
                                vertex_data = np.array(vertex_data, dtype='float32')

                            # 👉 THE FIX: Just restore the master list!
                            airport_labels = list(master_airport_labels)

                            route_count = len(vertex_data) // POINTS_PER_ARC
                            info_box.set_text(f"Display: Global Network\nTotal Paths: {route_count}")
                            is_filtered = False

                        else:
                            print(f"Filtering for: {clean_query}")

                            vertex_data, arrivals = dataset.get_filtered_airway_data(
                                np, lat_lon_to_xyz, EARTH_RADIUS, POINTS_PER_ARC, clean_query
                            )

                            route_count = len(vertex_data) // POINTS_PER_ARC
                            display_arrivals = "\n  - " + "\n  - ".join(arrivals)

                            ui_text = f"Search: {clean_query.upper()}\nTotal Paths: {route_count}"
                            info_box.set_text(ui_text)
                            ap_list.set_text(display_arrivals)
                            is_filtered = True

                            if len(vertex_data) > 0:
                                starts = vertex_data[0::POINTS_PER_ARC]
                                ends = vertex_data[POINTS_PER_ARC - 1::POINTS_PER_ARC]

                                combined_hubs = np.concatenate((starts, ends), axis=0)
                                unique_hubs = np.unique(combined_hubs, axis=0)

                                # 👉 THE FIX: Rebuild the labels by matching coordinates with the master list
                                airport_labels = []
                                for pt in unique_hubs:
                                    for master_hub in master_airport_labels:
                                        # Use a tiny distance check in case of float precision differences
                                        if abs(pt[0] - master_hub['pos'][0]) < 0.01 and \
                                                abs(pt[1] - master_hub['pos'][1]) < 0.01 and \
                                                abs(pt[2] - master_hub['pos'][2]) < 0.01:
                                            airport_labels.append(master_hub)
                                            break  # Found it, move to next point

                                # Target the first airport for camera animation
                                target_pos = unique_hubs[0]  # Fallback just in case

                                for master_hub in master_airport_labels:
                                    # Check if the search query matches the airport text
                                    if clean_query.upper() in master_hub['text'].upper():
                                        target_pos = master_hub['pos']
                                        break

                                # Now calculate the target rotation based on the CORRECT airport
                                tx, ty, tz = target_pos

                                target_rot_x = math.degrees(math.asin(ty / EARTH_RADIUS))

                                # Note: Depending on your specific OpenGL axis setup, you MIGHT need
                                # to add + 90, - 90, or + 180 to the Y rotation if it points at the side/back.
                                target_rot_y = -math.degrees(math.atan2(tx, tz))



                                is_animating = True
                            else:
                                airport_labels = []

                        if len(vertex_data) == 0:
                            is_filtered = False
                            print("No results found. Hiding routes.")
                            vertex_data = np.array([[0.0, 0.0, 0.0]], dtype='float32')
                            #airport_labels = []  # Clear dots when no results

                        glBindBuffer(GL_ARRAY_BUFFER, vbo)
                        glBufferData(GL_ARRAY_BUFFER, vertex_data.nbytes, vertex_data, GL_STATIC_DRAW)

                    elif event.key == pygame.K_BACKSPACE:
                        search_query = search_query[:-1]

                    elif event.unicode.isprintable() and len(search_query) < 25:
                        search_query += event.unicode
                else:
                    if event.key == pygame.K_b:
                        show_borders = not show_borders
                    if event.key == pygame.K_n:
                        show_labels = not show_labels
                    if event.key == pygame.K_h:
                        show_ui = not show_ui
                    if event.key == pygame.K_UP:
                        base_particle_size = min(100.0, base_particle_size + 0.1)
                    if event.key == pygame.K_DOWN:
                        base_particle_size = max(0.1, base_particle_size - 0.1)

                    if event.key == pygame.K_TAB:
                        camera_locked = not camera_locked

                        if camera_locked:
                            # Hide and snap to center
                            pygame.mouse.set_visible(False)
                            pygame.mouse.set_pos(center_x, center_y)
                        else:
                            # Show cursor so they can click the search bar
                            pygame.mouse.set_visible(True)




        if is_animating:
            # LERP X (Tilt)
            rot_x += (target_rot_x - rot_x) * 0.05

            # LERP Y (Spin) - Shortest Path Math
            # This prevents wild spinning if you've rotated the globe multiple times!
            diff_y = (target_rot_y - rot_y + 180) % 360 - 180
            rot_y += diff_y * 0.05


            # Stop condition
            if abs(target_rot_x - rot_x) < 0.5 and abs(diff_y) < 0.5:
                rot_x = target_rot_x
                # Normalize rot_y so it stays between 0 and 360 cleanly
                rot_y = target_rot_y % 360
                is_animating = False

        elif camera_locked:
            # Only allow manual mouse rotation if we are NOT currently animating
            mx, my = pygame.mouse.get_pos()
            frame_dx = mx - center_x
            frame_dy = my - center_y



            if frame_dx != 0 or frame_dy != 0:
                rot_y += frame_dx * 0.2
                rot_x += frame_dy * 0.2
                rot_x = max(-90.0, min(90.0, rot_x))

                pygame.mouse.set_pos(center_x, center_y)


        # ── SINGLE RENDER PASS ──────────────────────────────────────────────
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        glTranslatef(0, 0, zoom_level)
        glRotatef(rot_x, 1, 0, 0)
        glRotatef(rot_y, 0, 1, 0)

        mx, my = pygame.mouse.get_pos()
        center_dist = np.linalg.norm(
            np.array([mx - WINDOW_SIZE[0] / 2, my - WINDOW_SIZE[1] / 2])
        )
        hover_glow = max(0.9, 1.0 - (center_dist / 800.0))

        zoom_percent = (zoom_level - (-50.0)) / ((-3.5) - (-50.0))
        zoom_percent = max(0.01, min(zoom_percent, 1.0))
        points_to_draw = max(1, int(total_points * zoom_percent))

        # --- DYNAMIC ALPHA BACKSIDE FADE ---
        start_fade = -15.0
        end_fade   = -5.0

        if zoom_level > start_fade:
            fade_range = end_fade - start_fade
            alpha = (zoom_level - start_fade) / fade_range
            alpha = max(0.0, min(1.0, alpha))

            glEnable(GL_BLEND)
            glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
            glColor4f(*colors.SPHERE, 1 - alpha)

            quadric = gluNewQuadric()
            gluSphere(quadric, EARTH_RADIUS * 0.99, 64, 64)

            glBlendFunc(GL_SRC_ALPHA, GL_ONE)

        # --- 1. Draw flight routes ---
        draw_borders(rot_x, rot_y, zoom_level, show_borders, border_vbo, border_data, earth_core)
        draw_flight_routes(base_particle_size, hover_glow, vbo, points_to_draw)

        # --- 2. Airport hub dots ---
        draw_hub_dots(zoom_level, airport_labels)

        # --- 3. LABELS ---
        to_render = []
        draw_labels(zoom_level, airport_labels, to_render, show_labels)

        if show_ui:
            draw_ui(WINDOW_SIZE[0], WINDOW_SIZE[1], search_query, is_typing)

            info_box.draw(WINDOW_SIZE[0], WINDOW_SIZE[1])
            info_box.update_shake(frame_dx, frame_dy)

            if is_filtered:
                ap_list.update_shake(frame_dx, frame_dy)
                ap_list.draw(WINDOW_SIZE[0], WINDOW_SIZE[1])



        glClearColor(*colors.BACKGROUND)  # background color

        # ── END RENDER PASS ─────────────────────────────────────────────────
        pygame.display.flip()
        clock.tick(60)


if __name__ == "__main__":
    main()