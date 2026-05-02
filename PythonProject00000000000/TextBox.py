import pygame
from OpenGL.GL import *
from OpenGL.GLU import *
import math

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

        self.bg_color = (0.05, 0.05, 0.05, 0.8)
        self.border_color = (0.4, 0.4, 0.4, 1.0)
        self.text_color = (255, 255, 255, 255)

        pygame.font.init()
        self.font = font

        self.lines_per_col = 999
        self.columns = 1

        self.set_text(text)

    # --- NEW: Update Shake Physics ---
    def update_shake(self, dx, dy):
        """Applies a smooth spring-based inertia effect based on mouse movement."""
        # Multiplier controls the intensity of the sway.
        # Negative dx makes the box lag behind the mouse direction.
        target_x = -dx * 0.4
        # Invert Y because Pygame's Y-axis is flipped compared to OpenGL's Ortho2D
        target_y = dy * 0.4

        # LERP (Linear Interpolation): 0.15 is the spring stiffness.
        # Lower = looser spring, Higher = tighter spring.
        self.shake_x += (target_x - self.shake_x) * 0.02
        self.shake_y += (target_y - self.shake_y) * 0.02

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

        # 👉 THE MAGIC: Apply the offset to the entire UI block instantly
        glTranslatef(self.shake_x, self.shake_y, 0.0)

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

        # --- 4. Draw Text in Columns ---
        if self.text:
            lines = self.text.split('\n')
            line_spacing = self.font.get_height() + 4

            start_x = self.x + 10
            start_y = self.y + self.height - line_spacing - 5

            for i, line in enumerate(lines):
                if not line:
                    continue

                col = i // self.lines_per_col
                row = i % self.lines_per_col

                current_start_x = start_x + (col * self.base_width)
                current_start_y = start_y - (row * line_spacing)

                text_surface = self.font.render(line, True, self.text_color)
                text_data = pygame.image.tostring(text_surface, "RGBA", True)

                glRasterPos2d(current_start_x, current_start_y)
                glDrawPixels(text_surface.get_width(), text_surface.get_height(),
                             GL_RGBA, GL_UNSIGNED_BYTE, text_data)

        # --- 5. Restore 3D Mode ---
        glEnable(GL_DEPTH_TEST)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE)

        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        glPopMatrix()