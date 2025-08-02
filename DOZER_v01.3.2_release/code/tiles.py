import pygame
from settings import * # imports everything from settings.py      

class Tile(pygame.sprite.Sprite):
    def __init__(self, size, color, x, y):
        super().__init__()

        self.image = pygame.Surface((size, size), pygame.SRCALPHA)
        self.image.fill(color)
        self.rect = self.image.get_rect(topleft = (x, y))

        # Draw an outline around the image surface
        # pygame.draw.rect(self.image, (0, 0, 255), self.image.get_rect(), 1)

        self.row_index = (self.rect.y - y_start) // tile_size
        self.col_index = (self.rect.x - x_start) // tile_size

