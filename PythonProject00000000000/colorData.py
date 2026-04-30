# colors.py — Global Transportation Tree Color Palette
# All colors are defined as (R, G, B) or (R, G, B, A) tuples normalized to [0.0, 1.0]



# BACKGROUND

BACKGROUND = (0 ,0, 0,1 )
# --- UI / Search Bar ---
BAR_ACTIVE_BG       = (0.15, 0.15, 0.15, 0.9)   # Search box background when typing
BAR_INACTIVE_BG     = (0.05, 0.05, 0.05, 0.8)   # Search box background when idle
BAR_ACTIVE_OUTLINE  = (0.0,  0.7,  1.0,  1.0)   # Glowing blue border when active
BAR_INACTIVE_OUTLINE= (0.4,  0.4,  0.4,  1.0)   # Grey border when inactive
TEXT_DEFAULT        = (255,  255,  255,  255)    # White label text (0–255 range, Pygame)

# --- Earth / Globe ---
EARTH_CORE          = (0.0,  0.0,  0.0)         # Pitch-black occlusion sphere
SPHERE              = (0.0,  0.0,  0.0)         # Back-face fade shield (black, dynamic alpha)

# --- Borders ---
BORDER_LINE         = (0.7,  0.2,  0.1,  0.9)   # Reddish country border lines

# --- Flight Routes / Particles ---
ROUTE_GLOW          = (0.0,  0.7,  1.0,  0.3)   # Base cyan-blue route particle color
                                                  # (g and b channels are scaled by hover_glow at runtime)

# --- Airport Hub Dots ---
HUB_DOT             = (1.0,  1.0,  1.0,  1.0)   # Pure white hub points

# --- Labels ---
LABEL_TINT          = (1,    1,    1,    1)      # White tint applied to label textures
LABEL_TEXT_FG       = (255,  255,  255)          # Pygame font foreground (0–255)
LABEL_TEXT_BG       = (0,    0,    0)            # Pygame font background (0–255)