import pygame
import os

# --- Project Config ---
WINDOW_SIZE = (1280, 720)
EARTH_RADIUS = 3.0
POINTS_PER_ARC = 10 #line resolution
import themes.gold as colors

pygame.font.init()

W, H = WINDOW_SIZE

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_PATH = os.path.join(BASE_DIR, 'data', 'font.ttf')

UI_FONT = pygame.font.Font(FONT_PATH, int(24 * H/1440 ))
AP_FONT = pygame.font.Font(FONT_PATH, int(10 * H/1440))









