import pygame
import math
from settings import *
from support import *


class Player(pygame.sprite.Sprite):
    def __init__(self, pos):
        super().__init__()

        self.import_assets()
        self.status = 'idle'
        self.frame_index = 0
        self.previous_status = self.status

        # General setup
        self.image = self.animations[self.status][self.frame_index]
        self.rect = self.image.get_rect(center = pos)

        # For plow blade attributes:
        self.image2 = self.animations['idle_down'][0] # keeps the 'radius' pinned to length of 'plowing' rect 
        self.mask = pygame.mask.from_surface(self.image2)
        mask_size = self.mask.get_size()
        self.W = mask_size[0]
        self.radius = mask_size[1]/2

        # Movement attributes
        self.animation_speed = 2
        self.rotation = 0
        self.velocity = 0
        self.pos = pygame.math.Vector2(self.rect.center)


    def import_assets(self):
        self.animations = {'idle': [], 'idle_down': [], 'driving': [], 'pushing': []}

        for animation in self.animations.keys():
            full_path = '../graphics/player/' + animation
            self.animations[animation] = import_folder(full_path)

    def animate(self, dt):
        self.frame_index += self.animation_speed * dt
        if self.frame_index >= len(self.animations[self.status]):
            self.frame_index = 0
        self.image = self.animations[self.status][int(self.frame_index)]



    # Movement with rotation...
    def input(self):
        keys = pygame.key.get_pressed()

        if keys[pygame.K_LEFT]:
            self.rotation += 1
        if keys[pygame.K_RIGHT]:
            self.rotation += -1

        if keys[pygame.K_UP]:
            self.velocity = 150
            self.status = 'driving'
            if keys[pygame.K_SPACE]:
                self.status = 'pushing'

        elif keys[pygame.K_DOWN]:
            self.velocity = -150
            self.status = 'driving'

        elif keys[pygame.K_SPACE]:
            self.velocity = 0
            self.status = 'idle_down'
            
        else:
            self.velocity = 0


    def get_status(self):
        keys = pygame.key.get_pressed()

        if self.velocity == 0:
          self.status = 'idle'
          
          if keys[pygame.K_SPACE]:
                self.status = 'idle_down'


    def move(self, dt):

        radians = math.radians(self.rotation)
        vertical = math.cos(radians) * self.velocity * dt
        horizontal = math.sin(radians) * self.velocity * dt

        self.pos.y -= vertical
        self.pos.x -= horizontal

        self.rect.centery = round(self.pos.y)
        self.rect.centerx = round(self.pos.x)

        # horizontal bounds
        if self.rect.left <= 0 or self.rect.right >= SCREEN_WIDTH:
            self.rect.clamp_ip(pygame.Rect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT))
            self.pos.x, self.pos.y = self.rect.center

        # vertical bounds
        if self.rect.top <= 0 or self.rect.bottom >= SCREEN_HEIGHT:
            self.rect.clamp_ip(pygame.Rect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT))
            self.pos.x, self.pos.y = self.rect.center
            

    # addresses rotation in place
    def rotate(self):
        self.image = pygame.transform.rotozoom(self.image, self.rotation, 1)
        self.rect = self.image.get_rect(center = self.rect.center)
        self.mask = pygame.mask.from_surface(self.image)


    def plow_LR(self):

        # Calculate the endpoint of dozer "front" vector based on player angle
        angle_rad = (math.pi) / 2 + math.radians(self.rotation)
        x = int(self.rect.centerx + self.radius * math.cos(angle_rad))
        y = int(self.rect.centery - self.radius * math.sin(angle_rad))  # Subtract sin because pygame's y-axis is inverted
        self.A = (x, y)  

        # Calculate vector_B (in two parts)
        # Blade attributes
        B_length = self.W / 2

        self.B_L = (
            int(self.A[0] + B_length * math.cos(math.radians(self.rotation))),
            int(self.A[1] - B_length * math.sin(math.radians(self.rotation))))

        self.B_R = (
            int(self.A[0] + B_length * math.cos(math.radians(self.rotation + 180))),
            int(self.A[1] - B_length * math.sin(math.radians(self.rotation + 180))))

    
    def bresenham_line(self, start, end): # Bresenham Line draws a straight line on a grid...
        x0, y0 = start
        x1, y1 = end

        dx = abs(x1 - x0)
        dy = abs(y1 - y0)

        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1

        err = dx - dy
        points = [(x0, y0)]

        while x0 != x1 or y0 != y1:
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x0 += sx
            if e2 < dx:
                err += dx
                y0 += sy
            points.append((x0, y0))

        return points


    def makepix(self): # where start & end are the endpoints of the pixel line that is the plow blade

        self.line_points = self.bresenham_line(self.B_L, self.B_R)
    

    def update(self, dt):
        self.input()
        self.animate(dt)
        self.get_status()
        self.rotate()
        self.move(dt)
        self.plow_LR() # needs to be called after 'constraint'
        self.makepix() # also needs to be called after 'constraint'
        
        