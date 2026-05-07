
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import numpy as np
from config import *






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
                glColor4f(*colors.ROUTE_PULSE,alpha)  # Blueish fade

                glVertexPointer(3, GL_FLOAT, 0, streak_dots)
                glDrawArrays(GL_POINTS, 0, len(streak_dots))

    glDisableClientState(GL_VERTEX_ARRAY)
    return False


def get_zoom_scale_factor(current_zoom, base_zoom=-40.0):
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
                 border_vbo, border_data, earth_core,
                 pulse_origin, border_distances, active_waves):
    # 1. Solid Earth Core
    glDisable(GL_BLEND)
    glColor3f(*colors.EARTH_CORE)
    gluSphere(earth_core, EARTH_RADIUS * 0.98, 32, 32)

    # 2. Dynamic Borders
    if show_border and len(border_data) > 0:
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glLineWidth(1.0)

        glEnableClientState(GL_VERTEX_ARRAY)
        glBindBuffer(GL_ARRAY_BUFFER, border_vbo)
        glVertexPointer(3, GL_FLOAT, 0, None)

        num_vertices = len(border_data.reshape(-1, 3))

        # --- DYNAMIC PULSE RENDERER ---
        if pulse_origin is not None and border_distances is not None and len(active_waves) > 0:

            alphas = np.full(num_vertices, 0.05, dtype=np.float32)

            # 1. Start by tracking raw wave intensity (0.0 to 1.0) instead of alpha
            max_intensity = np.zeros(num_vertices, dtype=np.float32)

            for wave_dist in active_waves:
                distance_from_wave = np.abs(border_distances - wave_dist)
                wave_intensity = np.clip(1.0 - (distance_from_wave / 0.5), 0.0, 8.0)

                # Keep the strongest wave hitting this specific point
                max_intensity = np.maximum(max_intensity, wave_intensity)

            # 2. Map the intensity smoothly to your desired alpha range (0.3 to 1.0)
            # If max_intensity is 0.0, alpha is 0.3. If max_intensity is 1.0, alpha is 1.0.
            alphas = 0.3 + (max_intensity * 0.7)

            color_array = np.empty((num_vertices, 4), dtype=np.float32)
            color_array[:, 0] = colors.BORDER_LINE[0]
            color_array[:, 1] = colors.BORDER_LINE[1]
            color_array[:, 2] = colors.BORDER_LINE[2]
            color_array[:, 3] = alphas

            # Force array into strict C-contiguous memory
            color_array = np.ascontiguousarray(color_array, dtype=np.float32)

            # === THE MAGIC FIX ===
            # Unbind the VBO so OpenGL knows the color array is coming from Python RAM, not the GPU!
            glBindBuffer(GL_ARRAY_BUFFER, 0)

            glEnableClientState(GL_COLOR_ARRAY)
            glColorPointer(4, GL_FLOAT, 0, color_array)

            glDrawArrays(GL_LINES, 0, num_vertices)

            glDisableClientState(GL_COLOR_ARRAY)

        # --- NORMAL STATIC RENDERER ---
        else:
            glColor4f(*colors.BORDER_LINE)
            glDrawArrays(GL_LINES, 0, num_vertices)

        glDisableClientState(GL_VERTEX_ARRAY)
        glBindBuffer(GL_ARRAY_BUFFER, 0)




