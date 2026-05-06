import pygame
from OpenGL.GL import *
from OpenGL.GLU import *
import math
from config import *

#9.0
class TextBox:
    def __init__(self, x, y, width, height, text="", font=12, screen_height=1440):
        self.base_width = width
        self.current_width = width
        self.max_height = screen_height - 100

        self.center_x = x + (width / 2.0)
        self.center_y = y + (height / 2.0)

        self.min_height = height
        self.height = height

        self.x = x
        self.y = y

        # --- NEW: Shake Physics Variables ---
        self.shake_x = 0.0
        self.shake_y = 0.0
        self.slide_x = 0.0

        self.bg_color = (colors.INACTIVE_BG)
        self.border_color = (colors.INACTIVE_OUTLINE)
        self.text_color = (colors.TEXT_DEFAULT)

        pygame.font.init()
        self.font = font

        self.lines_per_col = 999
        self.columns = 1

        self.set_text(text)

    # --- NEW: Update Shake Physics ---
    def update(self, dx=0.0, dy=0.0, target_slide_x=0.0):
        """Handles both mouse-based shake inertia and smooth UI sliding."""

        # --- 1. Mouse Shake Physics ---
        target_shake_x = -dx * 0.4
        target_shake_y = dy * 0.4

        self.shake_x += (target_shake_x - self.shake_x) * 0.02
        self.shake_y += (target_shake_y - self.shake_y) * 0.02

        # --- 2. Dashboard Slide Physics ---
        self.slide_x += (target_slide_x - self.slide_x) * 0.05

    def set_text(self, new_text):
        # ... (Keep your exact set_text method exactly the same) ...
        self.text = str(new_text)

        if not self.text:
            self.height = self.min_height
            self.current_width = self.base_width
            self.x = self.center_x - (self.current_width / 2.0)
            self.y = self.center_y - (self.height / 2.0)
            self.lines_per_col = 999
            self.columns = 1
            return

        lines = self.text.split('\n')
        line_spacing = self.font.get_height() + 4
        calculated_height = (len(lines) * line_spacing) + 10

        if calculated_height > self.max_height:
            self.lines_per_col = int((self.max_height - 10) // line_spacing)
            if self.lines_per_col <= 0:
                self.lines_per_col = 1
            self.columns = math.ceil(len(lines) / self.lines_per_col)
            self.current_width = self.base_width * self.columns
            self.height = (self.lines_per_col * line_spacing) + 10
        else:
            self.lines_per_col = len(lines) if len(lines) > 0 else 1
            self.columns = 1
            self.current_width = self.base_width
            self.height = max(self.min_height, calculated_height)

        self.x = self.center_x - (self.current_width / 2.0)
        self.y = self.center_y - (self.height / 2.0)

    def draw(self, screen_width, screen_height):
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        gluOrtho2D(0, screen_width, 0, screen_height)

        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()

        # Apply shake/slide translation
        glTranslatef(self.shake_x + self.slide_x, self.shake_y, 0.0)

        glDisable(GL_DEPTH_TEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        # --- 2. Draw Background ---
        glColor4f(*self.bg_color)
        glBegin(GL_QUADS)
        glVertex2f(self.x, self.y)
        glVertex2f(self.x + self.current_width, self.y)
        glVertex2f(self.x + self.current_width, self.y + self.height)
        glVertex2f(self.x, self.y + self.height)
        glEnd()

        # --- 3. Draw Border ---
        glColor4f(*self.border_color)
        glLineWidth(1.5)
        glBegin(GL_LINE_LOOP)
        glVertex2f(self.x, self.y)
        glVertex2f(self.x + self.current_width, self.y)
        glVertex2f(self.x + self.current_width, self.y + self.height)
        glVertex2f(self.x, self.y + self.height)
        glEnd()

        # --- 4. Draw Centered Text in Columns ---
        if self.text:
            lines = self.text.split('\n')
            line_spacing = self.font.get_height() + 1

            # This is our vertical starting point (top of the box)
            top_margin = 5
            base_y_start = self.y + self.height - line_spacing - top_margin

            for i, line in enumerate(lines):
                if not line.strip():  # Skip empty lines
                    continue

                col = i // self.lines_per_col
                row = i % self.lines_per_col

                # 👉 STEP 1: Render surface to find its width
                text_surface = self.font.render(line, True, self.text_color)
                tw = text_surface.get_width()
                th = text_surface.get_height()

                # 👉 STEP 2: Calculate Horizontal Center
                # Start at the column's left edge, add half the column width,
                # then subtract half the text width.
                col_left_edge = self.x + (col * self.base_width)
                current_start_x = col_left_edge + (self.base_width - tw) / 2.0

                # STEP 3: Vertical Position
                current_start_y = base_y_start - (row * line_spacing)

                # Convert surface to OpenGL format
                text_data = pygame.image.tostring(text_surface, "RGBA", True)

                # Move the raster position and draw
                glRasterPos2d(current_start_x, current_start_y)
                glDrawPixels(tw, th, GL_RGBA, GL_UNSIGNED_BYTE, text_data)

        # --- 5. Restore 3D Mode ---
        glEnable(GL_DEPTH_TEST)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE)

        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        glPopMatrix()

class SearchBar:
    def __init__(self, x, y, width, height, font, screen_height):
        # Base Dimensions & Position (Pygame Top-Left Coordinates)
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.screen_height = screen_height

        # Text & State
        self.text = ""
        self.is_active = False
        pygame.font.init()
        self.font = font

        # Collision Rect (Use this in your main loop for MOUSEBUTTONDOWN checks)
        self.rect = pygame.Rect(self.x, self.y, self.width, self.height)

        # --- Shake & Slide Physics Variables ---
        self.shake_x = 0.0
        self.shake_y = 0.0
        self.slide_x = 0.0

        # Colors (Update these to match your `colors` module if needed)
        self.active_bg = (colors.ACTIVE_BG)
        self.inactive_bg = (colors.INACTIVE_BG)
        self.active_outline = (colors.ACTIVE_OUTLINE)
        self.inactive_outline = (colors.INACTIVE_OUTLINE)
        self.text_color = (colors.TEXT_DEFAULT)
        self.placeholder_color = (120, 120, 120, 255)

    def set_active(self, active_state):
        self.is_active = active_state

    def set_text(self, new_text):
        self.text = str(new_text)

    def update(self, dx=0.0, dy=0.0, target_slide_x=0.0):
        """Handles both mouse-based shake inertia and smooth UI sliding."""
        # 1. Mouse Shake Physics
        target_shake_x = -dx * 0.4
        target_shake_y = dy * 0.4

        self.shake_x += (target_shake_x - self.shake_x) * 0.02
        self.shake_y += (target_shake_y - self.shake_y) * 0.02

        # 2. Dashboard Slide Physics
        self.slide_x += (target_slide_x - self.slide_x) * 0.05

        # Update the collision rect's X position so it remains clickable after sliding!
        self.rect.x = self.x + int(self.slide_x)

    def draw(self, screen_width, screen_height):
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        gluOrtho2D(0, screen_width, 0, screen_height)

        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()

        # 👉 Apply BOTH the shake offset and the slide offset to the UI block
        glTranslatef(self.shake_x + self.slide_x, self.shake_y, 0.0)

        glDisable(GL_DEPTH_TEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        # Convert Pygame Y (Top=0) to OpenGL Y (Bottom=0)
        gl_bar_y = screen_height - self.y - self.height

        # --- 1. Draw Background ---
        bg_color = self.active_bg if self.is_active else self.inactive_bg
        glColor4f(*bg_color)
        glBegin(GL_QUADS)
        glVertex2f(self.x, gl_bar_y)
        glVertex2f(self.x + self.width, gl_bar_y)
        glVertex2f(self.x + self.width, gl_bar_y + self.height)
        glVertex2f(self.x, gl_bar_y + self.height)
        glEnd()

        # --- 2. Draw Outline ---
        outline_color = self.active_outline if self.is_active else self.inactive_outline
        glColor4f(*outline_color)
        glLineWidth(2.0)
        glBegin(GL_LINE_LOOP)
        glVertex2f(self.x, gl_bar_y)
        glVertex2f(self.x + self.width, gl_bar_y)
        glVertex2f(self.x + self.width, gl_bar_y + self.height)
        glVertex2f(self.x, gl_bar_y + self.height)
        glEnd()

        # --- 3. Draw Text ---
        display_text = self.text + ("_" if self.is_active else "")
        current_text_color = self.text_color

        if not self.text and not self.is_active:
            display_text = "Click here to search airport (e.g. JFK)..."
            current_text_color = self.placeholder_color

        # Render text to a Pygame surface and blast it to OpenGL (matching TextBox logic)
        text_surface = self.font.render(display_text, True, current_text_color)
        text_data = pygame.image.tostring(text_surface, "RGBA", True)

        # Calculate text position (Centered vertically, slightly offset from left edge)
        text_x = self.x + int(self.width * 0.037)
        text_y = gl_bar_y + int(self.height * 0.28)

        glRasterPos2d(text_x, text_y)
        glDrawPixels(text_surface.get_width(), text_surface.get_height(),
                     GL_RGBA, GL_UNSIGNED_BYTE, text_data)

        # --- 4. Restore 3D Mode ---
        glEnable(GL_DEPTH_TEST)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE)

        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        glPopMatrix()