import pygame

# Create a sprite for each pixel of plow blade
class Pixel(pygame.sprite.Sprite):
    def __init__(self, color, position):
        super().__init__()
        
        self.image = pygame.Surface((1, 1))
        self.image.fill(color)
        self.rect = self.image.get_rect(topleft = position)
