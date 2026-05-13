# FLIGHT ROUTES 3D

<img width="2559" height="1439" alt="pic2" src="https://github.com/user-attachments/assets/7a5f26a6-5f74-4fd1-8d30-0ef70f484913" />

This program allows you to inspect and search flight routes and airports by displaying a OpenGL particle simulated sphere. 
You can superficially see the air traffic network displayed by cool UI.

## Description



TAB - to switch between roam mode and search mode.
<br>
Mouse Scroll - Zoom in & out
<br>
B - Show/Hide borders 
<br>
N - show/Hide Labels

## Settings and Configuration

Config file :  transportation/src/program/config.py
<br>
```commandline
POINTS_PER_ARC = 10 
WINDOW_SIZE = 0 
FONT_PATH = os.path.join(BASE_DIR, 'data', 'font.ttf') 
import program.themes.default as colors 
```
POINTS_PER_ARC determines line resolution, higher values will take the program
longer to load.

For fullscreen, use WINDOW_SIZE = 0, else use format (width, height).

For switching UI theme, simply change the last line 
```commandline
import program.themes.gold as colors 
```
Themes: default, gold, inferno, mint, purple

## DEPENDENCIES
PYTHON 3.13

Run a terminal and run the commands below inside /flight-routes-3d-main
<br>
<br>
Linux
```commandline
python3 -m venv venv && source venv/bin/activate
```
```commandline
pip install -e . && run-app
```
Windows
```commandline
python -m venv venv; .\venv\Scripts\Activate.ps1
```
```commandline
pip install -e .; run-app
```

















