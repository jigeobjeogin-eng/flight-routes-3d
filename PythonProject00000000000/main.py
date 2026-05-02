import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import numpy as np
import dataset
from TextBox import TextBox
import themes.default as colors
import math

# --- Project Config ---
WINDOW_SIZE = (1280, 720)
EARTH_RADIUS = 3.0
POINTS_PER_ARC = 50

pygame.font.init()

W, H = WINDOW_SIZE
UI_FONT = pygame.font.SysFont('Consolas', int(18 * H/1440 ))

# Search Bar Dimensions — all relative to window size
BAR_WIDTH    = int(W * 0.307)
BAR_HEIGHT   = int(H * 0.057)
BAR_X        = (W - BAR_WIDTH) // 2
BAR_Y_MARGIN = int(H * 0.029)

# Pygame mouse coords: (0,0) = top-left, so rect uses BAR_Y_MARGIN from top
SEARCH_RECT = pygame.Rect(BAR_X, BAR_Y_MARGIN, BAR_WIDTH, BAR_HEIGHT)

import math


def draw_shining_dots(vertex_data, distance_flown, points_per_arc):
    if len(vertex_data) <= 1:
        return False  # Return False to signal the animation hasn't finished

    # 1. Reshape the flat data into individual routes
    num_routes = len(vertex_data) // points_per_arc
    routes = vertex_data.reshape(num_routes, points_per_arc, 3)

    # 2. Calculate the physical 3D distance of every single route
    starts = routes[:, 0, :]
    ends = routes[:, -1, :]
    # (Adding a tiny 0.0001 to prevent division-by-zero on bugged routes)
    distances = np.linalg.norm(ends - starts, axis=1) + 0.0001

    # 3. Check if the longest flight has reached its destination
    max_distance = np.max(distances)
    if distance_flown > max_distance + 0.5:  # 0.5 is the pause before resetting
        return True  # Return True to tell the main loop to reset!

    # --- HELPER FUNCTION: Interpolates the exact 3D position ---
    def get_positions(current_distance):
        prog_array = current_distance / distances
        active_mask = prog_array <= 1.0

        if not np.any(active_mask):
            return None

        p_active = prog_array[active_mask]
        r_active = routes[active_mask]

        float_idx = p_active * (points_per_arc - 1)
        idx0 = np.floor(float_idx).astype(int)
        idx1 = np.minimum(idx0 + 1, points_per_arc - 1)
        blend = (float_idx - idx0)[:, np.newaxis]

        p0 = r_active[np.arange(len(r_active)), idx0]
        p1 = r_active[np.arange(len(r_active)), idx1]

        return np.ascontiguousarray((p0 + (p1 - p0) * blend) * 1.01)
        # ------------------------------------------------------------

    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE)
    glEnableClientState(GL_VERTEX_ARRAY)

    # --- Draw Main Bright Dots (Single Blink) ---
    # --- Draw a Continuous Comet Streak ---
    # Draws 5 overlapping circles fading out behind the main dot
    for i in range(20):
        # Extremely tiny gap (0.02) so the circles overlap seamlessly
        streak_gap = i * 0.02

        if distance_flown > streak_gap:
            streak_dots = get_positions(distance_flown - streak_gap)
            if streak_dots is not None:
                # Get smaller and more transparent the further back it goes
                glPointSize(1)
                alpha = 1.0 - (i * 0.2)
                glColor4f(0.2, 0.2, 0.6, alpha)  # Blueish fade

                glVertexPointer(3, GL_FLOAT, 0, streak_dots)
                glDrawArrays(GL_POINTS, 0, len(streak_dots))

    glDisableClientState(GL_VERTEX_ARRAY)
    return False


def get_zoom_scale_factor(current_zoom, base_zoom=-40.0):
    """
    Returns a scale multiplier based on the zoom distance.
    If you are at the base zoom, it returns 1.0.
    If you zoom out twice as far, it returns 0.5.
    If you zoom in twice as close, it returns 2.0.
    """
    # Prevent division by zero just in case camera clips inside the exact center
    if current_zoom == 0:
        return 1.0

    # We use abs() because OpenGL zoom levels are usually negative Z values
    return abs(base_zoom) / abs(current_zoom)

def get_screen_center_lat_lon(rot_x, rot_y):
    """
    Converts camera rotations directly into real-world Latitude and Longitude.
    Returns: (latitude, longitude)
    """
    # Latitude is just your pitch (rot_x)
    # It should already be clamped between -90 and 90 by your camera controls,
    # but we clamp it here just to be perfectly safe.
    lat = max(-90.0, min(90.0, rot_x))

    # Longitude is your reversed yaw (-rot_y)
    raw_lon = -rot_y

    # Wrap the longitude so it always stays between -180 and 180 degrees
    lon = ((raw_lon + 180) % 360) - 180

    return [lat, lon]

def draw_text_2d(x, y, text, font, color=colors.TEXT_DEFAULT):
    if not text:
        return
    text_surface = font.render(text, True, color)
    text_data = pygame.image.tostring(text_surface, "RGBA", True)
    glRasterPos2d(x, y)
    glDrawPixels(text_surface.get_width(), text_surface.get_height(),
                 GL_RGBA, GL_UNSIGNED_BYTE, text_data)


def draw_ui(screen_width, screen_height, search_text, is_active):
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, screen_width, 0, screen_height)

    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()

    glDisable(GL_DEPTH_TEST)
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

    # In OpenGL ortho with gluOrtho2D(0,W,0,H): y=0 is BOTTOM, y=H is TOP.
    # Pygame mouse y=0 is TOP. So we flip: gl_y = H - pygame_y - height
    gl_bar_y = screen_height - BAR_Y_MARGIN - BAR_HEIGHT

    # Background
    glColor4f(*(colors.BAR_ACTIVE_BG if is_active else colors.BAR_INACTIVE_BG))
    glBegin(GL_QUADS)
    glVertex2f(BAR_X,             gl_bar_y)
    glVertex2f(BAR_X + BAR_WIDTH, gl_bar_y)
    glVertex2f(BAR_X + BAR_WIDTH, gl_bar_y + BAR_HEIGHT)
    glVertex2f(BAR_X,             gl_bar_y + BAR_HEIGHT)
    glEnd()

    # Outline
    glColor4f(*(colors.BAR_ACTIVE_OUTLINE if is_active else colors.BAR_INACTIVE_OUTLINE))
    glLineWidth(2.0)
    glBegin(GL_LINE_LOOP)
    glVertex2f(BAR_X,             gl_bar_y)
    glVertex2f(BAR_X + BAR_WIDTH, gl_bar_y)
    glVertex2f(BAR_X + BAR_WIDTH, gl_bar_y + BAR_HEIGHT)
    glVertex2f(BAR_X,             gl_bar_y + BAR_HEIGHT)
    glEnd()

    # Text — vertically centred
    display_text = search_text + ("_" if is_active else "")
    if not search_text and not is_active:
        display_text = "Click here to search airport (e.g. JFK)..."
    text_y = gl_bar_y + int(BAR_HEIGHT * 0.28)
    draw_text_2d(BAR_X + int(BAR_WIDTH * 0.037), text_y, display_text, UI_FONT)

    glEnable(GL_DEPTH_TEST)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE)
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)
    glPopMatrix()


def lat_lon_to_xyz(lat, lon, r):
    phi   = np.radians(90 - lat)
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


def draw_hub_dots(zoom_level, airport_labels, zoom_dot_threshold):
    if zoom_level > zoom_dot_threshold:
        glPointSize(1.0)
        glColor4f(*colors.HUB_DOT)
        glBegin(GL_POINTS)
        for hub in airport_labels:
            px, py, pz = np.array(hub['pos']) * 1.01
            glVertex3f(px, py, pz)
        glEnd()


def draw_labels(zoom_level, airport_labels, to_render, show_labels,
                zoom_label_threshold, max_labels):
    if not show_labels or zoom_level <= zoom_label_threshold:
        return

    modelview  = glGetDoublev(GL_MODELVIEW_MATRIX)
    projection = glGetDoublev(GL_PROJECTION_MATRIX)
    viewport   = glGetIntegerv(GL_VIEWPORT)

    for hub in airport_labels:
        if 'tex_id' not in hub:
            continue
        try:
            sx, sy, sz = gluProject(hub['pos'][0], hub['pos'][1], hub['pos'][2],
                                    modelview, projection, viewport)
            if 0 < sz < 1:
                to_render.append({'depth': sz, 'hub_ref': hub})
        except:
            continue

    to_render.sort(key=lambda x: x['depth'])
    to_render[:] = to_render[:max_labels]

    if not to_render:
        return

    glEnable(GL_TEXTURE_2D)
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    glColor4f(*colors.LABEL_TINT)

    mv    = glGetDoublev(GL_MODELVIEW_MATRIX)
    right = np.array([mv[0][0], mv[1][0], mv[2][0]])
    up    = np.array([mv[0][1], mv[1][1], mv[2][1]])

    for item in to_render:
        hub = item['hub_ref']
        glBindTexture(GL_TEXTURE_2D, hub['tex_id'])

        p             = np.array(hub['pos']) * 1.05
        dynamic_scale = (abs(zoom_level) ** 2) * 0.0005
        w = hub['w_base'] * dynamic_scale
        h = hub['h_base'] * dynamic_scale

        glBegin(GL_QUADS)
        glTexCoord2f(0, 0); glVertex3f(p[0], p[1], p[2])
        glTexCoord2f(1, 0); glVertex3f(p[0] + right[0]*w, p[1] + right[1]*w, p[2] + right[2]*w)
        glTexCoord2f(1, 1); glVertex3f(p[0] + right[0]*w + up[0]*h,
                                       p[1] + right[1]*w + up[1]*h,
                                       p[2] + right[2]*w + up[2]*h)
        glTexCoord2f(0, 1); glVertex3f(p[0] + up[0]*h, p[1] + up[1]*h, p[2] + up[2]*h)
        glEnd()

    glDisable(GL_TEXTURE_2D)


def draw_borders(rot_x, rot_y, zoom_level, show_border,
                 border_vbo, border_data, earth_core):
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()
    glTranslatef(0, 0, zoom_level)
    glRotatef(rot_x, 1, 0, 0)
    glRotatef(rot_y, 0, 1, 0)

    glDisable(GL_BLEND)
    glColor3f(*colors.EARTH_CORE)
    gluSphere(earth_core, EARTH_RADIUS * 0.98, 32, 32)
    glEnable(GL_BLEND)

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

    # Proportional derived values
    hover_radius         = ((W**2 + H**2) ** 0.5) * 0.5
    max_labels           = int(90 * (W * H) / (1300 * 700))
    zoom_dot_threshold   = -15.0
    zoom_label_threshold = -18.0

    # NEW: Flight animation tracker
    flight_tick = 0
    distance_flown = 0.0
    active_waves = [0.0]  # A list to track multiple waves flying at the same time
    wave_spawn_timer = 0.0  # A timer to trigger the next wave



    # --- OpenGL Matrix Setup ---
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(45, W / H, 0.1, 100.0)
    glMatrixMode(GL_MODELVIEW)

    glEnable(GL_DEPTH_TEST)
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE)
    glEnable(GL_POINT_SMOOTH)
    glClearColor(*colors.EARTH_CORE, 1)

    attenuation = [0.0, 0.0, 0.01]
    glPointParameterfv(GL_POINT_DISTANCE_ATTENUATION, attenuation)

    # --- Load Data ---
    vertex_data, airport_labels = dataset.get_airway_data(
        np, lat_lon_to_xyz, EARTH_RADIUS, POINTS_PER_ARC)

    vbo = glGenBuffers(1)
    glBindBuffer(GL_ARRAY_BUFFER, vbo)
    glBufferData(GL_ARRAY_BUFFER, vertex_data.nbytes, vertex_data, GL_STATIC_DRAW)
    glBindBuffer(GL_ARRAY_BUFFER, 0)

    # Pre-generate label textures
    for hub in airport_labels:
        surf   = FONT.render(hub['text'], True, colors.LABEL_TEXT_FG, colors.LABEL_TEXT_BG)
        tw, th = surf.get_size()
        data   = pygame.image.tostring(surf, "RGBA", True)
        tex_id = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, tex_id)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, tw, th, 0, GL_RGBA, GL_UNSIGNED_BYTE, data)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        hub['tex_id'] = tex_id
        hub['w_base'] = tw / th
        hub['h_base'] = 1.0

    border_data = dataset.get_world_borders(lat_lon_to_xyz, EARTH_RADIUS)
    border_vbo  = glGenBuffers(1)
    glBindBuffer(GL_ARRAY_BUFFER, border_vbo)
    glBufferData(GL_ARRAY_BUFFER, border_data.nbytes, border_data, GL_STATIC_DRAW)

    earth_core = gluNewQuadric()
    gluQuadricNormals(earth_core, GLU_SMOOTH)

    # TextBox positions — proportional to window

    mult_x = W / 2560
    mult_y = H / 1440

    def center(i):
        return (W - i)/2 + (i - (i * mult_x))/2

    info_box_w = int(W * 0.25)
    info_box_h = int(H * 0.171)
    info_box_y = int(H * 0.2)

    ap_list_w = int(W * 0.269)
    ap_list_x = W - ap_list_w - int(W * 0.011)
    ap_list_y = int(H * 0.30)

    coord_box_w = int(W* 0.45)
    coord_box_h = int(H * 0.1)
    coord_box_y = int(H * 0.02)




    info_box = TextBox(x=center(info_box_w), y=info_box_y * mult_y, width=info_box_w * mult_x, height=info_box_h * mult_y,
                       font=UI_FONT)
    ap_list  = TextBox(x=ap_list_x, y=ap_list_y, width=ap_list_w, height=0, font=UI_FONT)
    coord_box = TextBox(x = center(coord_box_w), y = coord_box_y, width = coord_box_w * mult_x, height = coord_box_h * mult_y,
                        font=UI_FONT)

    vertex_data = np.array(vertex_data, dtype='float32')
    route_count = len(vertex_data) // POINTS_PER_ARC
    info_box.set_text(f"Display: Global Network\nTotal Paths: {route_count}")

    # --- State ---
    rot_x, rot_y       = 0, 0
    zoom_level         = -12.0
    base_particle_size = 1.0
    total_points       = len(vertex_data) // 3
    clock              = pygame.time.Clock()
    show_borders       = True
    show_labels        = True
    show_ui            = True
    is_typing          = False
    is_filtered        = False
    search_query       = ""

    # Camera: starts unlocked so cursor is visible and search bar is clickable
    camera_locked = False
    camera_just_locked = False
    center_x      = W // 2
    center_y      = H // 2
    pygame.mouse.set_visible(True)

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

            # --- MOUSE CLICKS ---
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    mx, my = pygame.mouse.get_pos()
                    if SEARCH_RECT.collidepoint(mx, my):
                        # Clicked search bar — unlock camera, activate typing
                        is_typing     = True
                        camera_locked = False
                        pygame.mouse.set_visible(True)
                    else:
                        is_typing = False

                # Scroll Wheel Zoom
                if event.button == 4: zoom_level += 0.5
                if event.button == 5: zoom_level -= 0.5
                zoom_level = min(-3.5, max(zoom_level, -50.0))

            # --- KEYBOARD ---
            if event.type == pygame.KEYDOWN:
                if is_typing:
                    if event.key == pygame.K_RETURN:
                        is_typing   = False
                        clean_query = search_query.strip()

                        if clean_query == "":
                            search_query  = ""
                            original_data = dataset.get_airway_data(
                                np, lat_lon_to_xyz, EARTH_RADIUS, POINTS_PER_ARC)
                            vertex_data   = original_data[0] if isinstance(original_data, tuple) else original_data
                            if not isinstance(vertex_data, np.ndarray):
                                vertex_data = np.array(vertex_data, dtype='float32')
                            airport_labels = list(master_airport_labels)
                            route_count    = len(vertex_data) // POINTS_PER_ARC
                            info_box.set_text(f"Display: Global Network\nTotal Paths: {route_count}")
                            tx, ty, tz = 0,0,0
                            target_rot_x = math.degrees(math.asin(ty / EARTH_RADIUS))
                            target_rot_y = -math.degrees(math.atan2(tx, tz))
                            target_zoom_level = -12
                            is_animating = True
                            is_filtered = False

                        else:
                            vertex_data, arrivals = dataset.get_filtered_airway_data(
                                np, lat_lon_to_xyz, EARTH_RADIUS, POINTS_PER_ARC, clean_query)

                            route_count      = len(vertex_data) // POINTS_PER_ARC
                            display_arrivals = "\n  - " + "\n  - ".join(arrivals)
                            info_box.set_text(f"Search: {clean_query.upper()}\nTotal Paths: {route_count}")
                            ap_list.set_text(display_arrivals)
                            is_filtered = True

                            if len(vertex_data) > 0:
                                starts        = vertex_data[0::POINTS_PER_ARC]
                                ends          = vertex_data[POINTS_PER_ARC - 1::POINTS_PER_ARC]
                                combined_hubs = np.concatenate((starts, ends), axis=0)
                                unique_hubs   = np.unique(combined_hubs, axis=0)

                                airport_labels = []
                                for pt in unique_hubs:
                                    for master_hub in master_airport_labels:
                                        if (abs(pt[0] - master_hub['pos'][0]) < 0.01 and
                                                abs(pt[1] - master_hub['pos'][1]) < 0.01 and
                                                abs(pt[2] - master_hub['pos'][2]) < 0.01):
                                            airport_labels.append(master_hub)
                                            break

                                target_pos = unique_hubs[0]
                                for master_hub in master_airport_labels:
                                    if clean_query.upper() in master_hub['text'].upper():
                                        target_pos = master_hub['pos']
                                        break

                                # --- ALIGN ALL ROUTES TO START AT THE SEARCHED HUB ---
                                num_routes = len(vertex_data) // POINTS_PER_ARC
                                # Reshape the array so each row is exactly one route (10 points)
                                routes = vertex_data.reshape(num_routes, POINTS_PER_ARC, 3)
                                target_np = np.array(target_pos, dtype='float32')

                                for i in range(num_routes):
                                    # Check distance from the start point and end point to our hub
                                    dist_to_start = np.linalg.norm(routes[i, 0] - target_np)
                                    dist_to_end = np.linalg.norm(routes[i, -1] - target_np)

                                    # If the end is closer to the hub than the start, reverse the array!
                                    if dist_to_end < dist_to_start:
                                        routes[i] = routes[i][::-1]

                                tx, ty, tz   = target_pos
                                target_rot_x = math.degrees(math.asin(ty / EARTH_RADIUS))
                                target_rot_y = -math.degrees(math.atan2(tx, tz))
                                target_zoom_level = -3.5
                                is_animating = True
                            else:
                                airport_labels = []

                        if len(vertex_data) == 0:
                            is_filtered = False
                            vertex_data = np.array([[0.0, 0.0, 0.0]], dtype='float32')

                        glBindBuffer(GL_ARRAY_BUFFER, vbo)
                        glBufferData(GL_ARRAY_BUFFER, vertex_data.nbytes, vertex_data, GL_STATIC_DRAW)

                    elif event.key == pygame.K_BACKSPACE:
                        search_query = search_query[:-1]
                    elif event.unicode.isprintable() and len(search_query) < 25:
                        search_query += event.unicode

                else:
                    # Global hotkeys (only when not typing)
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
                            pygame.mouse.set_visible(False)
                            pygame.mouse.set_pos(center_x, center_y)
                            camera_just_locked = True  # ← ADD THIS
                        else:
                            pygame.mouse.set_visible(True)
                    if event.key == pygame.K_ESCAPE:
                        # Escape always unlocks camera and shows cursor
                        camera_locked = False
                        is_typing     = False
                        pygame.mouse.set_visible(True)

        # --- Animation / Camera ---
        if is_animating:

            show_ui = False
            rot_x  += (target_rot_x - rot_x) * 0.05
            diff_y  = (target_rot_y - rot_y + 180) % 360 - 180
            rot_y  += diff_y * 0.05
            if zoom_level < -3.5:
                zoom_level += (target_zoom_level - zoom_level) * 0.1

            if abs(target_rot_x - rot_x) < 0.5 and abs(diff_y) < 0.5 and abs(target_zoom_level - zoom_level) < 0.1:
                rot_x        = target_rot_x
                rot_y        = target_rot_y % 360
                zoom_level = target_zoom_level
                is_animating = False
                show_ui = True

        elif camera_locked:

            if camera_just_locked:  # ← ADD THIS BLOCK
                camera_just_locked = False  # consume the flag
                frame_dx = 0  # throw away the snap-frame delta
                frame_dy = 0
            else:
                mx, my = pygame.mouse.get_pos()
                frame_dx = mx - center_x
                frame_dy = my - center_y
                if frame_dx != 0 or frame_dy != 0:
                    rot_y += frame_dx * 0.2
                    rot_x += frame_dy * 0.2
                    rot_x = max(-90.0, min(90.0, rot_x))
                    pygame.mouse.set_pos(center_x, center_y)
        else:
            frame_dx = 0
            frame_dy = 0

        # ── RENDER ──────────────────────────────────────────────────────────
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        glTranslatef(0, 0, zoom_level)
        glRotatef(rot_x, 1, 0, 0)
        glRotatef(rot_y, 0, 1, 0)

        mx, my      = pygame.mouse.get_pos()
        center_dist = np.linalg.norm(np.array([mx - W / 2, my - H / 2]))
        hover_glow  = max(0.9, 1.0 - (center_dist / hover_radius))

        zoom_percent   = (zoom_level - (-50.0)) / ((-3.5) - (-50.0))
        zoom_percent   = max(0.01, min(zoom_percent, 1.0))
        points_to_draw = max(1, int(total_points * zoom_percent))

        # Dynamic alpha backside fade
        start_fade = -15.0
        end_fade   = -5.0
        if zoom_level > start_fade:
            alpha = (zoom_level - start_fade) / (end_fade - start_fade)
            alpha = max(0.0, min(1.0, alpha))
            glEnable(GL_BLEND)
            glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
            glColor4f(*colors.SPHERE, 1 - alpha)
            quadric = gluNewQuadric()
            gluSphere(quadric, EARTH_RADIUS * 0.99, 64, 64)
            glBlendFunc(GL_SRC_ALPHA, GL_ONE)

        draw_borders(rot_x, rot_y, zoom_level, show_borders,
                     border_vbo, border_data, earth_core)
        draw_flight_routes(base_particle_size, hover_glow, vbo, points_to_draw)

        # --- ONLY ANIMATE OUTBOUND FLIGHTS ON FILTERED SEARCH ---
        if is_filtered:
            speed = 0.03  # The constant speed of the dots

            # 1. Tick the timer and spawn a new wave if it's time
            wave_spawn_timer += speed
            if wave_spawn_timer >= 1.5:  # Every 1.5 units, launch a new pulse! (Lower = faster pulses)
                active_waves.append(0.0)
                wave_spawn_timer = 0.0

            # 2. Draw all active waves and move them forward
            surviving_waves = []
            for dist in active_waves:
                # Draw this wave (your function returns True when it completely finishes)
                wave_finished = draw_shining_dots(vertex_data, dist, POINTS_PER_ARC)

                # If the wave is still actively flying, keep it and add speed for the next frame
                if not wave_finished:
                    surviving_waves.append(dist + speed)

            # Update the main list with only the waves that haven't finished yet
            active_waves = surviving_waves
        # --------------------------------------------------------

        draw_shining_dots(vertex_data, flight_tick, POINTS_PER_ARC)


        draw_hub_dots(zoom_level, airport_labels, zoom_dot_threshold)

        to_render = []
        draw_labels(zoom_level, airport_labels, to_render, show_labels,
                    zoom_label_threshold, max_labels)

        if show_ui:
            draw_ui(W, H, search_query, is_typing)
            info_box.draw(W, H)
            info_box.update_shake(frame_dx, frame_dy)
            coord_box.draw(W,H)
            coord_box.update_shake(frame_dx, frame_dy)
            coord_box.set_text(f"{(get_screen_center_lat_lon(rot_x, rot_y)[0]):.5f}° N , {(get_screen_center_lat_lon(rot_x, rot_y)[1]):.5f}° W | %{get_zoom_scale_factor(zoom_level):.0f}")
            if is_filtered:
                ap_list.update_shake(frame_dx, frame_dy)
                ap_list.draw(W, H)

        glClearColor(*colors.BACKGROUND)
        pygame.display.flip()
        clock.tick(60)


if __name__ == "__main__":
    main()