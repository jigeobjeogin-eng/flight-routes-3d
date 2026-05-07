import pygame
import os
pygame.font.init()
pygame.display.init()
info = pygame.display.Info()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# --- Project Config ---
POINTS_PER_ARC = 10 #line resolution, +50 might take long to load
WINDOW_SIZE = 0 #type zero for fullscreen , for desired size use format the (width , height)
FONT_PATH = os.path.join(BASE_DIR, 'data', 'font.ttf') #switch font.tff with your own font name
EARTH_RADIUS = 3.0
import themes.gold as colors #chose between default, gold, inferno, mint, purple
#-----------------------

















