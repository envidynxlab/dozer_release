# DOZER (v01.3.2 release)

## About
DOZER is a single-player, arcade-style game motivated by observations of emergency road crews clearing sand from beachfront roads during coastal storms (Lazarus and Goldstein, 2019).
The game is also a fully coupled morphodynamic model, in which plowing actions by the player affect, and are affected by, patterns of storm-driven sediment deposition.
The game can be played for fun, or used as a heuristic tool for insight into the dynamics of deliberate, human intervention in the physical processes of a natural hazard event.
For more details on the physical processes, see the full model description included in this repository.

## This repository contains:
* code to play the game DOZER
* code to analyse game play data
* a detailed model description
* other supporting materials

### Code (this repository):
Lazarus, E (2025) DOZER: code and documentation. _Zenodo_ (model): https://doi.org/10.5281/zenodo.15589917

### License:
* MIT

### Related publications:
* pending

### References
Lazarus ED,  Goldstein EB (2019) Is there a bulldozer in your model? _Journal of Geophysical Research: Earth Surface_, 124, 696–699. https://doi.org/10.1029/2018JF004957

## Requirements
### Important Python packages and libraries used in this version:
### Game/model
* Python 3.11.7
* pygame 2.4.1
* numpy 1.26.4
* pandas 2.2.1
* scipy 1.11.4

### Analytics
* pandas 2.2.1
* numpy 1.26.4
* scipy 1.11.4
* matplotlib 3.8.0
* seaborn 0.12.2
* skimage 0.22.0

## Project structure
Install the main folder ```DOZER_v01.3.2.release``` in your working directory.

The main folder contains the following subfolders:
* audio
* code
* data
* font
* graphics

The ```code``` folder includes ```main.py``` – run this script to play the game. All other scripts are subordinate to this script.

Game play data will be stored in ```data``` folder, which also includes Jupyter notebook for analytics (```DOZER_analytics_release.ipynb```). The option to store game play data can be toggled off in the ```main.py``` script.

Supporting materials
The ```gif``` in this repository is indicative of a typical game.

The ```examples``` folder in this repository includes ready examples of game play data and screengrabs.
