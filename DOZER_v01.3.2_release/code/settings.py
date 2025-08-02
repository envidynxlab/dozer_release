import numpy as np

### Landscape and domain set-up...

# Fix random state(s) for reproducibility – uncomment to set seed
# r_seed = 19680807
# np.random.seed(r_seed)



# Set domain dimensions and other thresholds...
COLS = 48 # cols (width)
ROWS = 36 # rows (height)

ROWS_DRW = 100

H = 4 # height of initial berm and water level

# Note that this surface is only for steering, and never appears explicitly in the game domain
# Lower Rmax results in 'rounder' deposits
# Lower Vmin results in longer intrusion distances
Rmax = 0.6*H # set max random roughness; higher Rmax results in more contorted washover
Vmin = 0.02 #0.015 # min element volume in sediment surface (v), akin to lag deposition
thresh = 2*Vmin # min water depth through overwash site to initiate activity

# inc_max = 11

danger = 99 # threshold at which game kicks out to 'end screen'

tile_size = 20

# Screen
SCREEN_WIDTH = COLS * tile_size
SCREEN_HEIGHT = ROWS * tile_size

# Frame rate:
FPS = 60

# Interval for data collection (in millisecs):
t_collect = 2500


start_time = 0
score = 0


x_start = 0
y_start = 0

