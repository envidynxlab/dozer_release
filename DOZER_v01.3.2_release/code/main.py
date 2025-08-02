import pygame, sys, time, os
import numpy as np
import pandas as pd

import random

from settings import * # imports everything from settings.py
from morphodynamics import Morphodynamics

from morphodynamics_no_dozer import Morphodynamics_ND

from player import Player
from tiles import Tile
from pixel import Pixel


class Game:
    def __init__(self):

        # SCREEN AND INTRO
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))

        # Display title (version)...
        pygame.display.set_caption('DOZER v01.3.2_release') # barrier volume conservation issue fixed, sand colors adjusted, cleaner; dynamically complete; full analytics

        # CLOCK
        self.clock = pygame.time.Clock()

        # Ground surface:
        self.road_surface = pygame.image.load('../graphics/scene/road_02.png').convert_alpha()
        self.road_surface = pygame.transform.scale_by(self.road_surface, 0.45)
        self.road_surface_rect = self.road_surface.get_rect(topleft = (0, 50))


        # Audio
        self.music = pygame.mixer.Sound('../audio/quantum_2.ogg')
        self.music_channel = pygame.mixer.Channel(1)  # Dedicated channel for the music
        self.music_channel.set_volume(0.2)

        self.plowing_sound = pygame.mixer.Sound('../audio/vgmenuselect_clipped.wav')
        self.plowing_channel = pygame.mixer.Channel(2)  # Dedicated channel for the plowing sound
        self.plowing_channel.set_volume(0.2)

        # # GET READY
        self.initialise()


    def initialise(self):

        # Game IDs for data out...
        self.id_stamp = time.strftime("%Y%m%d-%H%M%S")

        # Fix random state(s) for reproducibility (for repeats of same trial) – comment out for random trials
        # np.random.seed(r_seed) # change in SETTINGS

        self.seed_state = np.random.get_state()[1][0]
        print(f"In INITIALISE, the current seed is: {self.seed_state}")

        # self.trial_tag = np.random.randint(0, 100000)
        self.trial_tag = random.randint(0, 100000)
        print(f"Trial tag is: {self.trial_tag}")

        
        self.tot_time = 0 # total running time
        self.data_flag = False

        # For the INTRO screen (in visual order, top to bottom)
        self.game_active = False
        self.dispatcher = False

        # For END screen and user choices
        self.user_esc = False
        self.save_game = False

        # PLAYER SETUP
        player_sprite = Player((int(SCREEN_WIDTH/2), int(0.75*SCREEN_HEIGHT)))
        self.player = pygame.sprite.GroupSingle(player_sprite)

        # Blade setup
        self.blade_VOL = 0
        self.blade_MAX = 1
        self.blade_vol_all = 0 # for cumulative account of blade volume over time

        # WASHOVER
        self.inc = 1
        self.perc = 1

        self.outside_flag = 0 # initially OFF

        self.inc_timer = 0

        self.counter = 0

        self.washover_event = False
        self.washover_first_flag = False

        self.period_o = 3 # baseline interval between washovers, in seconds
        self.period = self.period_o # initially, set interval to baseline

        self.intact_check = np.ones((1, COLS))

        # Save the state of the random generator
        initial_nprandom_state = np.random.get_state()

        # Prime the DOZER condition:
        self.morphodynamics = Morphodynamics()
        self.morphodynamics.random_sand()
        self.morphodynamics.breach_sites()

        # Restore the random state to ensure the same initial conditions
        np.random.set_state(initial_nprandom_state)

        # Prime the 'NO DOZER' shadow condition:
        self.morphodynamics_nd = Morphodynamics_ND()
        self.morphodynamics_nd.random_sand()
        self.morphodynamics_nd.breach_sites()

        # Access sand attribute from the instance
        self.shape = self.morphodynamics.sand
        self.SV = self.morphodynamics.sand        

        self.tile_size = tile_size
        self.tiles = pygame.sprite.Group()
        self.create_obstacle() # make the tiles
        self.sand_color() # color the sand according to volume


        # Create storage lists (pre arrays):
        self.store_id = []
        self.store_seed = []
        self.store_trial = []
        self.store_Vmin = []
        self.store_thresh = []
        self.store_H = []
        self.run_time = []
        self.dozer_x = []
        self.dozer_y = []
        self.dozer_Qs = []
        self.dozer_Qs_tot = []
        self.washover_vol_doz = []
        self.washover_vol_wo_doz = []
        self.lateral_adjust = []
        self.sand_diff_pos = []
        self.sand_diff_neg = []
        self.danger_score = []
        self.danger_mu = []

        self.berm_nd_mu = []

        self.sand_area_D = []
        self.sand_area_ND = []

        self.pulse = 0
        self.pulse_time = []
        self.pulse_t = []

        self.Qm_D = []
        self.Qm_ND = []

        self.wet_tot_D = []
        self.wet_tot_ND = []

        self.store_W = np.zeros((0, COLS))
        self.store_W_nd = np.zeros((0, COLS))
        self.store_BERM = np.zeros((0, COLS))
        self.store_BERM_nd = np.zeros((0, COLS))

        self.store_Q_M = np.zeros((0, COLS))
        self.store_Q_MOVE = np.zeros((0, COLS))
        self.store_sandy_fill = np.zeros((0, COLS))




    def reset(self):
        # Resets the game, starts a new session
        self.screen.fill('black') # clears the Intro screen
        pygame.display.flip()

        self.initialise()
       

    def title_screen(self):
        # Title text
        self.game_font = pygame.font.Font('../font/Pixeltype.ttf', 150)

        self.game_name = self.game_font.render('DOZER', False, (255,204,0))
        self.game_name_rect = self.game_name.get_rect(center = (SCREEN_WIDTH/2, 175))
    
        # Dozer
        self.player_intro = pygame.image.load('../graphics/player/idle/0.png').convert_alpha()
        self.player_intro = pygame.transform.rotozoom(self.player_intro, -90, 1)
        self.player_intro_rect = self.player_intro.get_rect(center = (SCREEN_WIDTH/2, 300))

        # Instructions text
        self.game_font = pygame.font.Font('../font/Pixeltype.ttf', 72)

        self.game_message1 = self.game_font.render('UP/DOWN for FORWARD/REVERSE', False, (212,170,0))
        self.game_message1_rect = self.game_message1.get_rect(center = (SCREEN_WIDTH/2, 450))

        self.game_message2 = self.game_font.render('LEFT/RIGHT to TURN',False, (212,170,0))
        self.game_message2_rect = self.game_message2.get_rect(center = (SCREEN_WIDTH/2,500))

        self.game_message3 = self.game_font.render('SPACE to PLOW', False, (212,170,0))
        self.game_message3_rect = self.game_message3.get_rect(center = (SCREEN_WIDTH/2,550))

        self.game_message4 = self.game_font.render('press P to PLAY', False, (212,170,0))
        self.game_message4_rect = self.game_message4.get_rect(center = (SCREEN_WIDTH/2,640))

        # Show INTRO screen
        self.screen.blit(self.player_intro, self.player_intro_rect)
        self.screen.blit(self.game_name, self.game_name_rect)
        self.screen.blit(self.game_message1, self.game_message1_rect)
        self.screen.blit(self.game_message2, self.game_message2_rect)
        self.screen.blit(self.game_message3, self.game_message3_rect)
        self.screen.blit(self.game_message4, self.game_message4_rect)
        pygame.display.update()
    

    def end_screen(self):

        if self.music_channel.get_busy():
            self.music_channel.stop()
        if self.plowing_channel.get_busy():
            self.plowing_channel.stop()

        self.overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        self.overlay.fill((25, 25, 25, 10))  # note fourth value sets transparency

        # End text
        self.game_font = pygame.font.Font('../font/Pixeltype.ttf', 96)

        self.end_message1 = self.game_font.render('GAME OVER', False, (255,204,0))
        self.end_message1_rect = self.end_message1.get_rect(center = (SCREEN_WIDTH/2, 200))


        self.game_font = pygame.font.Font('../font/Pixeltype.ttf', 72)
        self.end_message_score = self.game_font.render(f'Units plowed: {int(100*round(self.blade_vol_all, 2))}', False, (255,204,0))
        self.end_message_score_rect = self.end_message_score.get_rect(center = (SCREEN_WIDTH/2, 260))


        self.end_message2 = self.game_font.render('Save your results for science? (Y)', False, (255,255,255))
        self.end_message2_rect = self.end_message2.get_rect(center = (SCREEN_WIDTH/2, 320))

        self.disclaimer_font = pygame.font.Font(None, 36)
        self.disclaimer_font = pygame.font.SysFont('Arial', 24)

        self.disclaimer1 = self.disclaimer_font.render('Game play data are completely anonymous', False, (255,255,255))
        self.disclaimer1_rect = self.disclaimer1.get_rect(center = (SCREEN_WIDTH/2, 360))
        self.disclaimer2 = self.disclaimer_font.render('and only used to analyse and improve the game.', False, (255,255,255))
        self.disclaimer2_rect = self.disclaimer2.get_rect(center = (SCREEN_WIDTH/2, 390))


        self.end_message3 = self.game_font.render('press P to PLAY again',False, (212,170,0))
        self.end_message3_rect = self.end_message3.get_rect(center = (SCREEN_WIDTH/2, 500))

        self.end_message4 = self.game_font.render('press Q to QUIT', False, (212,170,0))
        self.end_message4_rect = self.end_message4.get_rect(center = (SCREEN_WIDTH/2, 550))

        # Show END screen
        self.screen.blit(self.overlay, (0,0))
        self.screen.blit(self.end_message1, self.end_message1_rect)

        self.screen.blit(self.end_message_score, self.end_message_score_rect)

        self.screen.blit(self.end_message2, self.end_message2_rect)
        self.screen.blit(self.disclaimer1, self.disclaimer1_rect)
        self.screen.blit(self.disclaimer2, self.disclaimer2_rect)

        self.screen.blit(self.end_message3, self.end_message3_rect)
        self.screen.blit(self.end_message4, self.end_message4_rect)
        pygame.display.update()


    def end_screen_alt(self):

        if self.music_channel.get_busy():
            self.music_channel.stop()

        self.overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        self.overlay.fill((25, 25, 25, 10))  # fourth value sets transparency

        # End text
        self.game_font = pygame.font.Font('../font/Pixeltype.ttf', 96)

        self.end_message1 = self.game_font.render('GAME OVER', False, (255,204,0))
        self.end_message1_rect = self.end_message1.get_rect(center = (SCREEN_WIDTH/2, 200))


        self.game_font = pygame.font.Font('../font/Pixeltype.ttf', 72)

        self.end_message2 = self.game_font.render('RESULTS SAVED!', False, (0,255,0))
        self.end_message2_rect = self.end_message2.get_rect(center = (SCREEN_WIDTH/2, 340))

        self.end_message3 = self.game_font.render('press P to PLAY again',False, (212,170,0))
        self.end_message3_rect = self.end_message3.get_rect(center = (SCREEN_WIDTH/2,500))

        self.end_message4 = self.game_font.render('press Q to QUIT', False, (212,170,0))
        self.end_message4_rect = self.end_message4.get_rect(center = (SCREEN_WIDTH/2,550))


        # Show END screen
        self.screen.blit(self.overlay, (0,0))
        self.screen.blit(self.end_message1, self.end_message1_rect)
        self.screen.blit(self.end_message2, self.end_message2_rect)
        self.screen.blit(self.end_message3, self.end_message3_rect)
        self.screen.blit(self.end_message4, self.end_message4_rect)
        pygame.display.update()


    def make_plow(self, line_points):

        self.plow_sprites = pygame.sprite.Group()

        for i in range(0, len(line_points), 7):
            point = line_points[i]

            self.pix = Pixel((0, 255, 0), point)
            self.plow_sprites.add(self.pix)


    def create_obstacle(self): # if sand, pink tile; if no sand, black (empty) tile
        n = 0
        for row_index, row in enumerate(self.shape):
            for col_index, col in enumerate(row):
                
                x = x_start + col_index * self.tile_size
                y = y_start + row_index * self.tile_size
                tile = Tile(self.tile_size, (0, 0, 0, 0), x, y)
                tile.id = n + 1
                tile.value = col
                tile.sand_vol = self.SV[row_index, col_index]
                tile.flag = 0
                tile.mover = 0
                tile.intact = -999
                
                self.tiles.add(tile)
                n += 1



    def get_tile(self, row_index, col_index):
        for tile in self.tiles:
            if (tile.row_index, tile.col_index) == (row_index, col_index):
                return tile
        return None


    def tiles_to_numpy_sand(self):
        
        self.tiles_to_sand = np.zeros((ROWS, COLS))

        for tile in self.tiles:
            r_idx = tile.row_index
            c_idx = tile.col_index

            self.tiles_to_sand[r_idx, c_idx] = tile.sand_vol

            
    
    def numpy_sand_to_tiles(self):
        indices = []
        indices = np.argwhere(self.morphodynamics.sand > 0)

        for idx in indices:
            i, j = idx

            tile = self.get_tile(i, j)
            tile.sand_vol = self.morphodynamics.sand[i, j]


    def sand_color(self): # colors sand tile based on volume
        # step through each tile to give it colour
        for tile in self.tiles:

            if tile.sand_vol == 0:
                tile.image.fill((0, 0, 0, 0)) # black is "empty"

            elif 0 < tile.sand_vol <= 0.01:
                tile.image.fill((244, 227, 215)) # lightest

            elif 0.01 < tile.sand_vol <= 0.02:
                tile.image.fill((238, 212, 195))

            elif 0.02 < tile.sand_vol <= 0.03:
                tile.image.fill((233, 198, 175))
            
            elif 0.03 < tile.sand_vol <= 0.05:
                tile.image.fill((227, 184, 155))

            elif 0.05 < tile.sand_vol <= 0.1:
                tile.image.fill((222, 170, 135))

            elif 0.1 < tile.sand_vol <= 0.15:
                tile.image.fill((216, 155, 115))

            elif 0.15 < tile.sand_vol <= 0.2:
                tile.image.fill((211, 141, 95))

            elif 0.2 < tile.sand_vol <= 0.25:
                tile.image.fill((205, 127, 75)) 

            elif tile.sand_vol > 0.25:
                tile.image.fill((200, 113, 55)) # darkest


            # Recolor top line of tiles on the basis of how intact berm is
            if tile.intact >= 0.95:
                tile.image.fill((190, 95, 15)) # max sand (slightly darker than color of darkest washover)

            elif 0.95 > tile.intact >= 0.8:
                tile.image.fill((255, 170, 170)) 

            elif 0.8 > tile.intact >= 0.7:
                tile.image.fill((255, 128, 128)) 

            elif 0.7 > tile.intact >= 0.6:
                tile.image.fill((255, 85, 85))

            elif 0.6 > tile.intact >= 0.5:
                tile.image.fill((255, 42, 42))

            elif 0.5 > tile.intact >= 0.4:
                tile.image.fill((255, 0, 0)) 

            elif 0.4 > tile.intact >= 0.2:
                tile.image.fill((170, 0, 0))
            
            elif 0.2 > tile.intact >= 0:
                tile.image.fill((128, 0, 0)) 

            
            if tile.flag == 1: # means this tile is "on" the plow blade (active collision)
                tile.image.fill((204, 0, 255))
                tile.flag = 0 # reset flag


    def mover_vis(self):

        indices = []
        indices = np.argwhere(self.morphodynamics.temp_move_vis > 0)

        for idx in indices:
            i, j = idx

            tile = self.get_tile(i, j)
            tile.image.fill((0, 204, 255)) # light blue "overwash"



    def intact_vis(self): # visualise how intact the barrier is...effectively a visual score bar

        indices = [(0, j) for j in range(COLS)]

        for idx in indices:
            i, j = idx

            tile = self.get_tile(i, j)

            if self.morphodynamics.berm[0, j] == 0:

                intact = 0
                tile.intact = intact
            
            else:

                excess = tile.sand_vol - self.perc*Vmin

                if excess > 0:

                    intact = (self.morphodynamics.berm[0, j] + excess)/H
                    tile.intact = intact # updates "intact" value for first row of tiles

                else:

                    intact = (self.morphodynamics.berm[0, j])/H
                    tile.intact = intact


            self.intact_check[0, j] = intact


    def plow_collision_check(self):
    # Check for collision between plow sprite and block sprites
        if self.player.sprite.status == 'pushing':

            # 'collisions' is a dictionary where keys are sprites from the first group
            # and values are lists of sprites from the second group that collided with the key sprite.
            collisions = pygame.sprite.groupcollide(self.plow_sprites, self.tiles, False, False)

            if collisions:
                
                unique_tiles = {}  # Dictionary to store unique tiles and their sand volume

                for plow_sprite, tile_list in collisions.items():
                    for tile in tile_list: # step through each tile in list
                        if tile not in unique_tiles: # if tile isn't already in the unique list...
                            unique_tiles[tile] = tile.id # add it, and pull its id

                            if self.blade_VOL > 0:
                                tile.flag = 1
                            
                            if tile.sand_vol > 0 and self.blade_VOL < self.blade_MAX: # if sand and capacity on blade...
                                self.blade_VOL += tile.sand_vol # add sand to blade volume
                                tile.sand_vol = 0 # empty that tile

                                if self.blade_VOL > self.blade_MAX: # if adding sand exceeds the blade capacity...
                                    over = self.blade_VOL - self.blade_MAX # find out by how much
                                    self.blade_VOL = self.blade_MAX # set blade volume to max
                                    tile.sand_vol = over # leave behind the difference
                                

        if self.player.sprite.status == 'idle_down' and self.blade_VOL > 0:

            collisions = pygame.sprite.groupcollide(self.plow_sprites, self.tiles, False, False)

            if collisions:
                
                unique_tiles = {}  # Dictionary to store unique tiles and their sand volume

                for plow_sprite, tile_list in collisions.items():
                    for tile in tile_list: # step through each tile in list
                        if tile not in unique_tiles: # if tile isn't already in the unique list...
                            tile.flag = 1
                

    def deposit_check(self):
        
        if self.player.sprite.previous_status == 'pushing' and self.player.sprite.status != 'pushing':
            if self.player.sprite.status != 'idle_down':
        
                if self.blade_VOL > 0:

                    overlap = pygame.sprite.groupcollide(self.plow_sprites, self.tiles, False, False)
                    if overlap:
                        depo_tiles = {}
                        under = 0
                        for plow_sprite, tile_list in overlap.items():
                            for tile in tile_list:
                                if tile not in depo_tiles:
                                    depo_tiles[tile] = tile.id
                                    under += tile.sand_vol
                                
                        Qdepo = (self.blade_VOL + under) / len(depo_tiles) 
                        for tile, sand_vol in depo_tiles.items():
                            tile.sand_vol = Qdepo # makes a block, like "bumping" a ragged pile for smooth top

                        self.blade_vol_all += self.blade_VOL
                        self.blade_VOL = 0
        
        elif self.player.sprite.previous_status == 'idle_down' and self.player.sprite.status != 'idle_down':

            if self.player.sprite.status != 'pushing':

                    if self.blade_VOL > 0:

                        overlap = pygame.sprite.groupcollide(self.plow_sprites, self.tiles, False, False)
                        if overlap:
                            depo_tiles = {}
                            under = 0
                            for plow_sprite, tile_list in overlap.items():
                                for tile in tile_list:
                                    if tile not in depo_tiles:
                                        depo_tiles[tile] = tile.id
                                        under += tile.sand_vol
                                    
                            Qdepo = (self.blade_VOL + under) / len(depo_tiles) 
                            for tile, sand_vol in depo_tiles.items():
                                tile.sand_vol = Qdepo # makes a block, like "bumping" a ragged pile for smooth top

                            self.blade_vol_all += self.blade_VOL
                            self.blade_VOL = 0


    def display_units(self):
        self.game_font = pygame.font.Font('../font/Pixeltype.ttf', 48)

        self.units_score = self.game_font.render(f'Units plowed: {int(100*round(self.blade_vol_all, 2))}', False, (255,204,0))
        self.units_score_rect = self.units_score.get_rect(midleft = (25, SCREEN_HEIGHT-70))

        self.bg_rect_plowed = self.units_score_rect.inflate(20, 20)  # Adjust padding as needed
        pygame.draw.rect(self.screen, (0, 0, 0), self.bg_rect_plowed)
        self.screen.blit(self.units_score, self.units_score_rect)

        self.bg_rect_danger = self.units_score.get_rect(midleft = (25, SCREEN_HEIGHT-30))
        self.bg_rect_danger = self.bg_rect_danger.inflate(20, 20)
        pygame.draw.rect(self.screen, (0, 0, 0), self.bg_rect_danger)



        # Colors the 'Danger' score according to min of colorbar (dune berm) at top of screen:
        if int(100*round(1 - self.intact_check.min(), 2)) <= 10:
            self.berm_score = self.game_font.render(f'Danger: {int(100*round(1 - self.intact_check.min(), 2))}', False, (2, 158, 115))

        elif 10 < int(100*round(1 - self.intact_check.min(), 2)) <= 20:
            self.berm_score = self.game_font.render(f'Danger: {int(100*round(1 - self.intact_check.min(), 2))}', False, (255, 170, 170))

        elif 20 < int(100*round(1 - self.intact_check.min(), 2)) <= 30:
            self.berm_score = self.game_font.render(f'Danger: {int(100*round(1 - self.intact_check.min(), 2))}', False, (255, 128, 128))

        elif 30 < int(100*round(1 - self.intact_check.min(), 2)) <= 40:
            self.berm_score = self.game_font.render(f'Danger: {int(100*round(1 - self.intact_check.min(), 2))}', False, (255, 85, 85))

        elif 40 < int(100*round(1 - self.intact_check.min(), 2)) <= 50:
            self.berm_score = self.game_font.render(f'Danger: {int(100*round(1 - self.intact_check.min(), 2))}', False, (255, 42, 42))

        elif 50 < int(100*round(1 - self.intact_check.min(), 2)) <= 60:
            self.berm_score = self.game_font.render(f'Danger: {int(100*round(1 - self.intact_check.min(), 2))}', False, (255, 0, 0))

        elif 60 < int(100*round(1 - self.intact_check.min(), 2)) <= 80:
            self.berm_score = self.game_font.render(f'Danger: {int(100*round(1 - self.intact_check.min(), 2))}', False, (220, 0, 0))
        
        elif 80 < int(100*round(1 - self.intact_check.min(), 2)):
            self.berm_score = self.game_font.render(f'Danger: {int(100*round(1 - self.intact_check.min(), 2))}', False, (180, 0, 0))

        self.berm_score_rect = self.units_score.get_rect(midleft = (25, SCREEN_HEIGHT-30))
        self.screen.blit(self.berm_score, self.berm_score_rect)



    def data_gather(self):
        
        self.store_id.append([self.id_stamp])
        self.store_seed.append([self.seed_state])
        self.store_trial.append([self.trial_tag])

        self.store_Vmin.append([Vmin])
        self.store_thresh.append([thresh])
        self.store_H.append([H])

        self.run_time.append([round(self.tot_time, 2)])
        self.dozer_x.append([self.player.sprite.rect.centerx])
        self.dozer_y.append([self.player.sprite.rect.centery])
        self.dozer_Qs.append([round(self.blade_VOL, 3)])
        self.dozer_Qs_tot.append([round(self.blade_vol_all, 3)])
        self.washover_vol_doz.append([round(self.morphodynamics.sand[1:].sum(), 3)])
        self.washover_vol_wo_doz.append([round(self.morphodynamics_nd.sand[1:].sum(), 3)])
        self.lateral_adjust.append([round(self.morphodynamics.lateral, 3)])

        sand_diff = self.morphodynamics.sand - self.morphodynamics_nd.sand # difference between two sand domains at each collection step
        self.sand_diff_pos.append([np.sum(sand_diff[sand_diff > 0])]) # only the positive differences (D - ND)
        self.sand_diff_neg.append([np.sum(sand_diff[sand_diff < 0])]) # only the negative differences (D - ND)

        self.danger_score.append([int(100*round(1 - self.intact_check.min(), 2))])
        self.danger_mu.append([100*round(1 - self.intact_check.mean(), 2)])

        self.berm_nd_mu.append([100*round(1 - self.morphodynamics_nd.berm.mean()/H, 2)])

        self.pulse_t.append([self.pulse])


        # Calc area of sand
        mask_A_D = self.morphodynamics.sand.copy()
        mask_A_D[mask_A_D > 0] = 1
        A_D = mask_A_D.sum()
        
        mask_A_ND = self.morphodynamics_nd.sand.copy()
        mask_A_ND[mask_A_ND > 0] = 1
        A_ND = mask_A_ND.sum()
        
        self.sand_area_D.append([A_D])
        self.sand_area_ND.append([A_ND])


        # Define the directory and filename
        folder_path = "../data"  # Desired folder path – here: relative path, one dir up
        self.capture_time = time.strftime("%Y%m%d-%H%M%S")

        # Ensure the folder exists
        os.makedirs(folder_path, exist_ok=True)

        # Save the DOZER'd sand array:
        self.temp_sand_dozer = pd.DataFrame(self.morphodynamics.sand)
        file_name1 = f"{self.capture_time}_trial{self.trial_tag}_temp_sand_D.csv"
        file_path1 = os.path.join(folder_path, file_name1)
        self.temp_sand_dozer.to_csv(file_path1, index=False)

        # Save the NO DOZER'd sand array:
        self.temp_sand_no_dozer = pd.DataFrame(self.morphodynamics_nd.sand)
        file_name2 = f"{self.capture_time}_trial{self.trial_tag}_temp_sand_ND.csv"
        file_path2 = os.path.join(folder_path, file_name2)
        self.temp_sand_no_dozer.to_csv(file_path2, index=False)

        # Snap a screenshot:
        file_name3 = f"{self.capture_time}_trial{self.trial_tag}_screenshot.png"
        file_path3 = os.path.join(folder_path, file_name3)
        pygame.image.save(self.screen, file_path3)




    def allometry_data_collect_v2(self):

        self.pulse = round(self.tot_time, 2)
        self.pulse_time.append([self.pulse])
        
        self.Qm_D.append([self.morphodynamics.Qmove.sum()])
        self.Qm_ND.append([self.morphodynamics_nd.Qmove.sum()])

        ###### Capture 'move' (overwash) surface for allometry calcs...
        self.wet_tot_D.append([self.morphodynamics.wet])
        self.wet_tot_ND.append([self.morphodynamics_nd.wet])

        
        # Define the directory and filename
        folder_path = "../data"  # Desired folder path – here: relative path, one dir up
        self.capture_time = time.strftime("%Y%m%d-%H%M%S")

        # Ensure the folder exists
        os.makedirs(folder_path, exist_ok=True)

        # Save the DOZER'd overwash pattern:
        self.overwash_footprint_D = pd.DataFrame(self.morphodynamics.store_tmv) # capture cumulative 'temp_move_vis'
        file_name1 = f"{self.capture_time}_trial{self.trial_tag}_ow_footprint_D.csv"
        file_path1 = os.path.join(folder_path, file_name1)
        self.overwash_footprint_D.to_csv(file_path1, index=False)

        # Save the NO DOZER'd overwash pattern:
        self.overwash_footprint_ND = pd.DataFrame(self.morphodynamics_nd.store_tmv)
        file_name2 = f"{self.capture_time}_trial{self.trial_tag}_ow_footprint_ND.csv"
        file_path2 = os.path.join(folder_path, file_name2)
        self.overwash_footprint_ND.to_csv(file_path2, index=False)

        # Save the DOZER'd sand array:
        self.ow_sand_dozer = pd.DataFrame(self.morphodynamics.sand)
        file_name3 = f"{self.capture_time}_trial{self.trial_tag}_ow_sand_D.csv"
        file_path3 = os.path.join(folder_path, file_name3)
        self.ow_sand_dozer.to_csv(file_path3, index=False)

        # Save the NO DOZER'd sand array:
        self.ow_sand_no_dozer = pd.DataFrame(self.morphodynamics_nd.sand)
        file_name4 = f"{self.capture_time}_trial{self.trial_tag}_ow_sand_ND.csv"
        file_path4 = os.path.join(folder_path, file_name4)
        self.ow_sand_no_dozer.to_csv(file_path4, index=False)



    def data_export(self):

        self.store_id = np.asarray(self.store_id)
        self.store_seed = np.asarray(self.store_seed)
        self.store_trial = np.asarray(self.store_trial)
        self.run_time = np.asarray(self.run_time)
        self.dozer_x = np.asarray(self.dozer_x)
        self.dozer_y = np.asarray(self.dozer_y)
        self.dozer_Qs = np.asarray(self.dozer_Qs)
        self.dozer_Qs_tot = np.asarray(self.dozer_Qs_tot)
        self.washover_vol_doz = np.asarray(self.washover_vol_doz)
        self.washover_vol_wo_doz = np.asarray(self.washover_vol_wo_doz)
        self.lateral_adjust = np.asarray(self.lateral_adjust)
        self.sand_diff_pos = np.asarray(self.sand_diff_pos)
        self.sand_diff_neg = np.asarray(self.sand_diff_neg)
        self.danger_score = np.asarray(self.danger_score)
        self.danger_mu = np.asarray(self.danger_mu)

        self.berm_nd_mu = np.asarray(self.berm_nd_mu)
        self.pulse_t = np.array(self.pulse_t)
    
        self.pulse_time = np.asarray(self.pulse_time)
        self.Qm_D = np.asarray(self.Qm_D)
        self.Qm_ND = np.asarray(self.Qm_ND)


        self.wet_tot_D = np.asarray(self.wet_tot_D)
        self.wet_tot_ND = np.asarray(self.wet_tot_ND)


        self.sand_area_D = np.asarray(self.sand_area_D)
        self.sand_area_ND = np.asarray(self.sand_area_ND)
        

        ### remember to amend column for washover w/out DOZER...zeros in that for now
        columns = ['datetime_id','randseed', 'trial', 'Vmin', 'threshold', 'H', 'run_time', 'dozer_x', 'dozer_y', 'dozer_Qs', 'dozer_Qs_tot',
                   'washover_V_D', 'washover_V_ND', 'washover_A_D', 'washover_A_ND', 'lateral_disp',
                   'danger_score', 'crest_mu_D', 'crest_mu_ND', 'pulse_time']
        self.data_deck = np.concatenate((self.store_id,
                                         self.store_seed,
                                         self.store_trial,
                                         self.store_Vmin,
                                         self.store_thresh,
                                         self.store_H,
                                         self.run_time,
                                         self.dozer_x,
                                         self.dozer_y,
                                         self.dozer_Qs,
                                         self.dozer_Qs_tot,
                                         self.washover_vol_doz,
                                         self.washover_vol_wo_doz,
                                         self.sand_area_D,
                                         self.sand_area_ND,
                                         self.lateral_adjust,
                                         self.danger_score,
                                         self.danger_mu,
                                         self.berm_nd_mu,
                                         self.pulse_t),
                                         axis=1)

        self.data_for_export = pd.DataFrame(self.data_deck, columns=columns)

        columns2 = ['pulse_time', 'Qm_D', 'Qm_ND', 'wet_D', 'wet_ND']
        self.Qm_deck = np.concatenate((self.pulse_time,
                                         self.Qm_D,
                                         self.Qm_ND,
                                         self.wet_tot_D,
                                         self.wet_tot_ND),
                                         axis = 1)
        self.Qm_deck_out = pd.DataFrame(self.Qm_deck, columns=columns2)


        # print(self.data_for_export) # just to check...

        # Define the directory and filename
        folder_path = "../data"  # Desired folder path – here: relative path, one dir up
        file_name = f"{self.id_stamp}_trial{self.trial_tag}_gamedata.csv"

        # Ensure the folder exists
        os.makedirs(folder_path, exist_ok=True)
        
        # Create the full file path
        file_path = os.path.join(folder_path, file_name)
        
        # Save the DataFrame to a CSV file
        self.data_for_export.to_csv(file_path, index = False)
        print(f"Data exported to {file_path}")

        # Save the DOZER'd sand array:
        self.final_sand_dozer = pd.DataFrame(self.morphodynamics.sand)
        second_file_name = f"{self.id_stamp}_trial{self.trial_tag}_final_sand_D.csv"
        second_file_path = os.path.join(folder_path, second_file_name)
        self.final_sand_dozer.to_csv(second_file_path, index=False)
        print(f"Final sand DOZER data exported to {second_file_path}")

        # Save the NO DOZER sand array:
        self.final_sand_no_dozer = pd.DataFrame(self.morphodynamics_nd.sand)
        third_file_name = f"{self.id_stamp}_trial{self.trial_tag}_final_sand_ND.csv"
        third_file_path = os.path.join(folder_path, third_file_name)
        self.final_sand_no_dozer.to_csv(third_file_path, index=False)
        print(f"Final sand NO DOZER data exported to {third_file_path}")

        # Save the "move" timeseries
        fourth_file_name = f"{self.id_stamp}_trial{self.trial_tag}_Qmove_series.csv"
        fourth_file_path = os.path.join(folder_path, fourth_file_name)

        self.Qm_deck_out.to_csv(fourth_file_path, index = False)
        print(f"Qm series data exported to {fourth_file_path}")


        # Save the DOZER berm and waterline:
        self.store_WATER = pd.DataFrame(self.store_W)
        self.store_WATER_ND = pd.DataFrame(self.store_W_nd)

        self.store_CREST = pd.DataFrame(self.store_BERM)
        self.store_CREST_ND = pd.DataFrame(self.store_BERM_nd)

        self.store_Qm = pd.DataFrame(self.store_Q_M)
        self.store_Qmove = pd.DataFrame(self.store_Q_MOVE)
        self.iso_throats = pd.DataFrame(self.morphodynamics.isolated_throats)
        self.store_PLOWED_FRONT = pd.DataFrame(self.store_sandy_fill)

        self.forcing = pd.DataFrame(self.morphodynamics.forcing_pattern)

        file_nameA = f"{self.capture_time}_trial{self.trial_tag}_waterlines_D.csv"
        file_pathA = os.path.join(folder_path, file_nameA)
        self.store_WATER.to_csv(file_pathA, index=False)

        file_nameB = f"{self.capture_time}_trial{self.trial_tag}_temp_berms_D.csv"
        file_pathB = os.path.join(folder_path, file_nameB)
        self.store_CREST.to_csv(file_pathB, index=False)

        file_nameC = f"{self.capture_time}_trial{self.trial_tag}_waterlines_ND.csv"
        file_pathC = os.path.join(folder_path, file_nameC)
        self.store_WATER_ND.to_csv(file_pathC, index=False)

        file_nameD = f"{self.capture_time}_trial{self.trial_tag}_temp_berms_ND.csv"
        file_pathD = os.path.join(folder_path, file_nameD)
        self.store_CREST_ND.to_csv(file_pathD, index=False)

        file_nameE = f"{self.capture_time}_trial{self.trial_tag}_forcing_pattern.csv"
        file_pathE = os.path.join(folder_path, file_nameE)
        self.forcing.to_csv(file_pathE, index=False)

    
    def sound_check(self):

        if self.player.sprite.status == 'pushing' and self.blade_VOL > 0:
            if not self.plowing_channel.get_busy():
                self.plowing_channel.play(self.plowing_sound, loops = -1)  # Loop the sound
        else:
            self.plowing_channel.stop()





    ############
    # RUN METHOD
    def run(self):
            
            prev_time = time.time()


            # Timer for data capture
            data_timer = pygame.USEREVENT + 1

            while True:

                if self.game_active == False and self.dispatcher == False and self.user_esc == False:
                    # Run the title screen:
                    self.title_screen()

                    for event in pygame.event.get():

                        if event.type == pygame.KEYDOWN and event.key == pygame.K_p: # press P to Play...
                            self.game_active = True
                            prev_time = time.time() # resets dt // clears the clock so that 'inc_timer' does not exceed 'period'
                            pygame.time.set_timer(data_timer, t_collect) # t in milliseconds
                            self.data_first = True


                        if event.type == pygame.KEYDOWN and event.key == pygame.K_q: # press Q to quit...
                            pygame.quit()
                            sys.exit()
                        
                        # Allow player to exit from INTRO screen:
                        if event.type == pygame.QUIT:
                            pygame.quit()
                            sys.exit()


                elif self.dispatcher or self.user_esc:
                    
                    self.game_active = False

                    if not self.save_game:
                    # Run end screen:
                        self.end_screen()

                        for event in pygame.event.get():

                            if event.type == pygame.KEYDOWN and event.key == pygame.K_y: # if Y to save game play...
                                self.save_game = True
                                self.data_export()
                            
                            if event.type == pygame.KEYDOWN and event.key == pygame.K_p: # PLAY AGAIN
                                    print('User hit PLAY AGAIN')
                                    self.reset()

                            # Give player an out...
                            if event.type == pygame.KEYDOWN and event.key == pygame.K_q: # press Q to quit...
                                pygame.quit()
                                sys.exit()
                            
                            # Allow player to exit from INTRO screen:
                            if event.type == pygame.QUIT:
                                pygame.quit()
                                sys.exit()


                    if self.save_game:
                        # Run alternative end screen:
                        self.end_screen_alt()

                        for event in pygame.event.get():

                            # Allow user to play again:
                            if event.type == pygame.KEYDOWN and event.key == pygame.K_p: # PLAY AGAIN
                                # print('User hit PLAY')
                                self.reset()

                            # Give player an out...
                            if event.type == pygame.KEYDOWN and event.key == pygame.K_q: # press Q to Quit...
                                pygame.quit()
                                sys.exit()
                            
                            # Allow player to exit from end screen:
                            if event.type == pygame.QUIT:
                                pygame.quit()
                                sys.exit()


                else: # play starts

                    # Music starts when game starts
                    if self.game_active:
                        if not self.music_channel.get_busy():
                            self.music_channel.play(self.music, loops = -1)  # Loop the sound
                    else:
                        self.music_channel.stop()


                    dt = time.time() - prev_time # dt with time.time() for smooth, stable motion
                    prev_time = time.time()

                    self.tot_time += dt # total running time

                    if self.data_first:
                        print('FIRST data collect')
                        self.data_gather() # captures initial 't = 0' state
                        self.data_first = False


                    # Increment timer
                    self.inc_timer += dt

                    # Data collection, and ensure player has an out back to main screen when game is running...
                    for event in pygame.event.get():

                        # Data collection at regular interval (t_collect) while game is running...
                        if event.type == data_timer:
                            print('Data collect!')
                            self.data_gather()
                            print('Time is: ', self.tot_time)


                        # Ensure player has an out...
                        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE: # if user hits ESC
                            self.user_esc = True
                            print('ESC data collect!')
                            self.data_gather() # take data at the end of play
                            self.game_active = False

                        if event.type == pygame.QUIT:
                            pygame.quit() 
                            sys.exit()
                        

                    # Run the updates:
                    self.screen.fill('black') # clears the screen

                    self.player.update(dt)
                    self.make_plow(self.player.sprite.line_points)



                    # OVERWASH EVENTS
                    if int(self.inc_timer) == self.period:
                        
                        self.washover_event = True
                        self.outside_flag = 1 # flip ON
                        self.morphodynamics.inside_flag = 1 # flip ON
                        self.morphodynamics_nd.inside_flag = 1 # flip ON

                        # If first cycle of washover:
                        if self.inc == 1 and not self.washover_first_flag:
                            
                            self.washover_first_flag = True # trip flag to prevent cycling...

                            self.morphodynamics.overwash_conditions(self.perc, self.inc) # initialise morphodynamics conditions
                            self.morphodynamics_nd.overwash_conditions(self.perc, self.inc) # initialise morphodynamics conditions


                    if self.outside_flag == 1: # meaning run the overwash routine

                        # if self.perc <= inc_max:

                            if self.morphodynamics.inside_flag == 1:

                                self.tiles_to_numpy_sand()
                                self.morphodynamics.couple(self.tiles_to_sand)
                                self.morphodynamics.update(self.inc)
                                self.mover_vis()

                                # run 'no DOZER' condition in parallel
                                self.morphodynamics_nd.update(self.inc)


                            if self.morphodynamics.inside_flag == 0:

                                self.morphodynamics.make_washover()
                                self.morphodynamics_nd.make_washover() # run 'no DOZER' condition in parallel
                                self.numpy_sand_to_tiles()

                                self.allometry_data_collect_v2()


                                self.store_W = np.vstack((self.store_W, self.morphodynamics.waterline))
                                self.store_BERM = np.vstack((self.store_BERM, self.morphodynamics.throat_temp))

                                self.store_W_nd = np.vstack((self.store_W_nd, self.morphodynamics_nd.waterline))
                                self.store_BERM_nd = np.vstack((self.store_BERM_nd, self.morphodynamics_nd.throat_temp))


                                self.outside_flag = 0 # flip OFF
                                self.washover_event = False

                                print('percent: ', 10*self.perc)

                                # Reset increment timer
                                self.perc += 1
                                self.inc += 1
                                self.inc_timer = 0

                                # Set period of next overwash pulse
                                self.period = self.period_o + np.random.randint(0, 7) # makes overwash happen on a random interval between 3 and 10 seconds

                                self.morphodynamics.overwash_conditions(self.perc, self.inc) # set up for next perc/inc
                                self.morphodynamics_nd.overwash_conditions(self.perc, self.inc) # set up for next perc/inc in 'no DOZER' condtion


                    # Blit road surface to screen:
                    self.screen.fill('black')
                    self.screen.blit(self.road_surface, self.road_surface_rect)

                    self.tiles.draw(self.screen)
                    self.player.draw(self.screen)

                    self.plow_collision_check()
                    self.deposit_check()

                    self.sound_check()

                    self.intact_vis()
                    self.sand_color()


                    self.player.sprite.previous_status = self.player.sprite.status

                    self.display_units()

                    
                    if int(100*round(1 - self.intact_check.min(), 2)) >= danger:
                        self.data_gather() # record details of final game state
                        self.game_active = False
                        self.dispatcher = True                        


                    pygame.display.update()


                    self.clock.tick(FPS)

#########
# Run it:
if __name__ == '__main__':
           
    pygame.init()

    game = Game()
    game.run()
