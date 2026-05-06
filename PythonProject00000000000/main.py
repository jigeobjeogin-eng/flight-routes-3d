from PythonProject00000000000.data import dataset
from TextBox import TextBox, SearchBar
from renderer import *
import sys
import math


def lat_lon_to_xyz(lat, lon, r):
    phi   = np.radians(90 - lat)
    theta = np.radians(lon + 180)
    x = r * np.sin(phi) * np.cos(theta)
    y = r * np.cos(phi)
    z = r * np.sin(phi) * np.sin(theta)
    return [x, y, z]





def main():
    pygame.init()
    pygame.display.set_mode(WINDOW_SIZE, DOUBLEBUF | OPENGL)
    pygame.display.set_caption("Global Transportation Tree - AIR PHASE")
    pygame.font.init()

    LABEL_FONT = pygame.font.SysFont('Arial', 12)

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

    #BORDER PULSE
    # New variables for the map pulse effect
    pulse_origin = None
    border_distances = None

    # New Pygame UI sliding variables
    ui_offset_x = 0.0
    target_ui_offset_x = 0.0
    pan_x = 0.0
    target_pan_x = 0.0
    is_tab = False





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
        surf   = LABEL_FONT.render(hub['text'], True, colors.LABEL_TEXT_FG, colors.LABEL_TEXT_BG)
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

    info_box_w = int(W * 0.15)* mult_x
    info_box_h = int(H * 0.01)* mult_y
    info_box_y = int(H * 0.1) * mult_y

    ap_list_w = int(W * 0.1)* mult_x
    ap_list_x = W - ap_list_w - int(W * 0.1)
    ap_list_y = int(H * 0.5)* mult_y

    search_box_w = int(W * 0.2)* mult_x
    search_box_h = int(H * 0.05)* mult_y
    search_box_y = int(H * 0.09)* mult_y

    coord_box_w = int(W* 0.2)* mult_x
    coord_box_h = int(H * 0.01)* mult_y
    coord_box_y = int(H * 0.01)* mult_y

    info_box = TextBox(x=center(info_box_w), y=info_box_y, width=info_box_w, height=info_box_h,font=UI_FONT)
    ap_list  = TextBox(x=ap_list_x, y=ap_list_y, width=ap_list_w, height=0, font=AP_FONT)
    coord_box = TextBox(x = center(coord_box_w), y = coord_box_y, width = coord_box_w, height = coord_box_h,font=UI_FONT)
    search_bar = SearchBar(x= center(search_box_w), y= search_box_y, width= search_box_w, height=search_box_h, font=UI_FONT, screen_height= H)


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
    is_filtered        = False

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

    running = True

    while running:

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return

            # --- MOUSE CLICKS ---
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    if search_bar.rect.collidepoint(event.pos):
                        search_bar.set_active(True)
                    else:
                        search_bar.set_active(False)

                # Scroll Wheel Zoom
                if event.button == 4: zoom_level += 0.5
                if event.button == 5: zoom_level -= 0.5
                zoom_level = min(-3.5, max(zoom_level, -50.0))

            # --- KEYBOARD ---

            if event.type == pygame.KEYDOWN:
                # 1. Check the new SearchBar's active state instead of 'is_typing'
                if search_bar.is_active:

                    if event.key == pygame.K_RETURN:
                        search_bar.set_active(False)  # Deactivate typing mode
                        clean_query = search_bar.text.strip()  # Pull text directly from the bar

                        if clean_query == "":
                            search_bar.set_text("")
                            pulse_origin = None
                            border_distances = None
                            original_data = dataset.get_airway_data(
                                np, lat_lon_to_xyz, EARTH_RADIUS, POINTS_PER_ARC)
                            vertex_data = original_data[0] if isinstance(original_data, tuple) else original_data
                            if not isinstance(vertex_data, np.ndarray):
                                vertex_data = np.array(vertex_data, dtype='float32')

                            airport_labels = list(master_airport_labels)
                            route_count = len(vertex_data) // POINTS_PER_ARC

                            info_box.set_text(f"Display: Global Network\nTotal Paths: {route_count}")
                            ap_list.set_text("")  # Clear the arrivals list

                            tx, ty, tz = 0, 0, 0
                            target_rot_x = math.degrees(math.asin(ty / EARTH_RADIUS))
                            target_rot_y = -math.degrees(math.atan2(tx, tz))
                            target_zoom_level = -12

                            # Reset globe pan and smoothly slide UI back to the center
                            target_pan_x = 0.0
                            target_ui_offset_x = 0.0

                            is_animating = True
                            is_filtered = False

                        else:
                            vertex_data, arrivals = dataset.get_filtered_airway_data(
                                np, lat_lon_to_xyz, EARTH_RADIUS, POINTS_PER_ARC, clean_query)



                            route_count = len(vertex_data) // POINTS_PER_ARC


                            MAX_CHARS = 25


                            truncated_arrivals = [
                                (a[:MAX_CHARS] + "...") if len(a) > MAX_CHARS else a
                                for a in arrivals
                            ]

                            display_arrivals = "\n - " + "\n - ".join(truncated_arrivals)

                            info_box.set_text(f"Search: {clean_query.upper()}\nTotal Paths: {route_count}")
                            ap_list.set_text(display_arrivals)
                            is_filtered = True

                            if len(vertex_data) > 0:
                                starts = vertex_data[0::POINTS_PER_ARC]
                                ends = vertex_data[POINTS_PER_ARC - 1::POINTS_PER_ARC]
                                combined_hubs = np.concatenate((starts, ends), axis=0)
                                unique_hubs = np.unique(combined_hubs, axis=0)

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
                                routes = vertex_data.reshape(num_routes, POINTS_PER_ARC, 3)
                                target_np = np.array(target_pos, dtype='float32')

                                # --- PRE-CALCULATE MAP DISTANCES FOR BORDER PULSE ---
                                pulse_origin = target_pos
                                b_data_3d = border_data.reshape(-1, 3)
                                border_distances = np.linalg.norm(b_data_3d - target_np, axis=1)

                                for i in range(num_routes):
                                    dist_to_start = np.linalg.norm(routes[i, 0] - target_np)
                                    dist_to_end = np.linalg.norm(routes[i, -1] - target_np)

                                    if dist_to_end < dist_to_start:
                                        routes[i] = routes[i][::-1]

                                # --- Update the Rotation and Pan Logic ---
                                tx, ty, tz = target_pos
                                print(target_pos)

                                lon = math.atan2(tx, tz)  # Lon in radians
                                lat = math.asin(ty / EARTH_RADIUS)  # Lat in radians



                                # Use the radius that matches your data (appears to be ~2.99)
                                R = np.sqrt(tx ** 2 + ty ** 2 + tz ** 2)

                                # 1. Calculate Latitude (X)
                                # We use the positive value to match your 40.27 expectation
                                target_lat_deg = math.degrees(math.asin(ty / R))

                                # 2. Calculate Longitude (Y)
                                # atan2(x, z) gives us the horizontal angle
                                current_lon_deg = math.degrees(math.atan2(tx, tz))

                                # 3. Final Rotation Alignment
                                # To match your 'Expected' output:
                                target_rot_x = target_lat_deg  # Result: 40.27
                                target_rot_y = -current_lon_deg + 20.0  # Result: 142.99 ( -(-122.99) + 20 )

                                # --- Pan and Zoom ---
                                # Since you are moving the point 45 degrees to the right,
                                # keep the pan smaller or zero so it doesn't fly off the right edge.
                                target_pan_x = -1.0  # Subtle shift to the right
                                target_zoom_level = -6.0
                                target_ui_offset_x = target_pan_x * W/6

                                is_animating = True






                                is_animating = True
                            else:
                                airport_labels = []

                        if len(vertex_data) == 0:
                            is_filtered = False
                            vertex_data = np.array([[0.0, 0.0, 0.0]], dtype='float32')

                        glBindBuffer(GL_ARRAY_BUFFER, vbo)
                        glBufferData(GL_ARRAY_BUFFER, vertex_data.nbytes, vertex_data, GL_STATIC_DRAW)

                    # 2. Let the SearchBar object handle typing and backspacing internally
                    elif event.key == pygame.K_BACKSPACE:
                        search_bar.set_text(search_bar.text[:-1])

                    elif event.unicode.isprintable() and len(search_bar.text) < 25:
                        search_bar.set_text(search_bar.text + event.unicode)


                else:
                    # Global hotkeys (only when not typing)
                    if event.key == pygame.K_b:
                        show_borders = not show_borders
                    if event.key == pygame.K_n:
                        show_labels = not show_labels

                    if event.key == pygame.K_UP:
                        base_particle_size = min(100.0, base_particle_size + 0.1)
                    if event.key == pygame.K_DOWN:
                        base_particle_size = max(0.1, base_particle_size - 0.1)
                    if event.key == pygame.K_TAB:
                        camera_locked = not camera_locked
                        if camera_locked:
                            show_ui = False
                            pygame.mouse.set_visible(False)
                            pygame.mouse.set_pos(center_x, center_y)
                            target_pan_x =  0.0
                            camera_just_locked = True
                        else:
                            show_ui = True
                            target_pan_x = -W / 1000
                            pygame.mouse.set_visible(True)

                        if is_filtered:
                            is_tab = True

                    if event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_ESCAPE:
                            running = False

        if is_tab:
            pan_x += (target_pan_x - pan_x) * 0.3
            if abs(target_pan_x - pan_x) < 0.1:
                pan_x = target_pan_x
                is_tab = False

        # --- Animation / Camera ---
        if is_animating:




            show_ui = False

            rot_x += (target_rot_x - rot_x) * 0.05
            diff_y = (target_rot_y - rot_y + 180) % 360 - 180
            rot_y += diff_y * 0.05


            pan_x += (target_pan_x - pan_x) * 0.05
            ui_offset_x += (target_ui_offset_x - ui_offset_x) * 0.05


            if zoom_level < -3.5:
                zoom_level += (target_zoom_level - zoom_level) * 0.1

            if abs(target_rot_x - rot_x) < 0.5 and abs(diff_y) < 0.5 and abs(target_zoom_level - zoom_level) < 0.1:
                rot_x        = target_rot_x
                rot_y        = target_rot_y % 360
                zoom_level = target_zoom_level
                show_ui = True
                is_animating = False

        elif camera_locked:
            if camera_just_locked:
                camera_just_locked = False
                frame_dx = 0
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
        glTranslatef(pan_x, 0, zoom_level)
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
                     border_vbo, border_data, earth_core,
                     pulse_origin, border_distances, active_waves)
        draw_flight_routes(base_particle_size, hover_glow, vbo, points_to_draw)

        # --- ONLY ANIMATE OUTBOUND FLIGHTS ON FILTERED SEARCH ---
        if is_filtered:
            speed = 0.03  # The constant speed of the dots

            # 1. Tick the timer and spawn a new wave if it's time
            wave_spawn_timer += speed
            if wave_spawn_timer >= 2:  # Every 1.5 units, launch a new pulse! (Lower = faster pulses)
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
            search_bar.update(frame_dx, frame_dy, target_ui_offset_x)
            search_bar.draw(W, H)
            info_box.draw(W, H)
            info_box.update(frame_dx, frame_dy, target_ui_offset_x)
            coord_box.draw(W,H)
            coord_box.update(frame_dx, frame_dy, target_ui_offset_x)
            coord_box.set_text(f"{(get_screen_center_lat_lon(rot_x, rot_y)[0]):.5f}° N , {(get_screen_center_lat_lon(rot_x, rot_y)[1]):.5f}° W | %{get_zoom_scale_factor(zoom_level):.0f}")
            if is_filtered:
                ap_list.update(frame_dx, frame_dy)
                ap_list.draw(W, H)

        glClearColor(*colors.BACKGROUND)
        pygame.display.flip()
        clock.tick(60)
    pygame.quit()
    sys.exit()




if __name__ == "__main__":
    main()