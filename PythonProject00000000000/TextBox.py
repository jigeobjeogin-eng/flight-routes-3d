import pygame
from OpenGL.GL import *
from OpenGL.GLU import *


class TextBox:
    def __init__(self, x, y, width, height, text="", font_size=16):
        """
        Note: OpenGL coordinates start with (0,0) at the BOTTOM-LEFT of the screen.
        """
        self.x = x
        self.width = width

        # --- NEW: Center Anchor Logic ---
        # Find the absolute vertical center of the box based on your initial placement
        self.center_y = y + (height / 2.0)

        self.min_height = height
        self.height = height
        self.y = y

        # UI Styling
        self.bg_color = (0.05, 0.05, 0.05, 0.8)  # Dark grey, 80% opaque
        self.border_color = (0.4, 0.4, 0.4, 1.0)
        self.text_color = (255, 255, 255, 255)

        pygame.font.init()
        self.font = pygame.font.SysFont('Consolas', font_size)

        # Call set_text to calculate initial height and center the Y coordinate
        self.set_text(text)

    def set_text(self, new_text):
        """Update the text dynamically and resize the box from the center."""
        self.text = str(new_text)

        if not self.text:
            self.height = self.min_height
        else:
            lines = self.text.split('\n')
            line_spacing = self.font.get_height() + 4

            # Calculate required height: (number of lines * spacing) + 10px padding
            calculated_height = (len(lines) * line_spacing) + 10

            self.height = max(self.min_height, calculated_height)

        # --- NEW: Apply the Centered Growth ---
        # By setting the bottom edge (Y) to exactly half the height below the center,
        # the box naturally extends equally in both directions.
        self.y = self.center_y - (self.height / 2.0)

    def draw(self, screen_width, screen_height):
        # --- 1. Switch to 2D Orthographic Mode ---
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

        # --- 2. Draw Background ---
        glColor4f(*self.bg_color)
        glBegin(GL_QUADS)
        glVertex2f(self.x, self.y)
        glVertex2f(self.x + self.width, self.y)
        glVertex2f(self.x + self.width, self.y + self.height)
        glVertex2f(self.x, self.y + self.height)
        glEnd()

        # --- 3. Draw Border ---
        glColor4f(*self.border_color)
        glLineWidth(1.5)
        glBegin(GL_LINE_LOOP)
        glVertex2f(self.x, self.y)
        glVertex2f(self.x + self.width, self.y)
        glVertex2f(self.x + self.width, self.y + self.height)
        glVertex2f(self.x, self.y + self.height)
        glEnd()

        # --- 4. Draw Text (Handles multiline \n) ---
        if self.text:
            lines = self.text.split('\n')
            line_spacing = self.font.get_height() + 4

            # Start near the top-left of the box
            start_x = self.x + 10
            start_y = self.y + self.height - line_spacing - 5

            for i, line in enumerate(lines):
                if not line:
                    continue
                text_surface = self.font.render(line, True, self.text_color)
                text_data = pygame.image.tostring(text_surface, "RGBA", True)

                # Move raster position down for each new line
                glRasterPos2d(start_x, start_y - (i * line_spacing))
                glDrawPixels(text_surface.get_width(), text_surface.get_height(),
                             GL_RGBA, GL_UNSIGNED_BYTE, text_data)

        # --- 5. Restore 3D Mode ---
        glEnable(GL_DEPTH_TEST)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE)

        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        glPopMatrix()