import pygame
from os import walk

def import_folder(path):
    surface_list = []

    for _, _, img_files in walk(path):
        for image in img_files:
            if image[0] != '.': # works around hidden files and takes only the real image files
                full_path = path + '/' + image
                image_surf = pygame.image.load(full_path).convert_alpha()
                image_surf = pygame.transform.rotozoom(image_surf,0,0.5) # scales the dozer from original art
                surface_list.append(image_surf)

    return surface_list