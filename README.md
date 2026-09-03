# Marvel3D

A real-time 3D model viewer built with **Python, PyOpenGL, and Pygame**, featuring interactive Marvel-inspired character models with dynamic lighting, glow effects, and animated backgrounds.

## Overview

Marvel3D renders two textured 3D models side by side — a Marvel character and Wolverine — loaded directly from `.obj`/`.mtl` files. It uses a custom OpenGL rendering pipeline with diffuse, normal, and roughness texture mapping, a soft shadow/glow system, and a fully interactive camera. The scene opens with a cinematic zoom-in intro and supports animated (GIF/video) backgrounds behind the models.

## Features

- 🎨 **Custom OpenGL shader pipeline** — diffuse, normal, and roughness texture mapping per model
- 🌀 **Interactive camera** — mouse-drag rotation, scroll-to-zoom, and keyboard tilt controls
- ✨ **Dynamic glow effects** — cycle through multiple glow colors and adjust intensity live
- 🎬 **Cinematic intro animation** — smooth zoom-in on launch
- 🖼️ **Animated backgrounds** — supports static images, GIFs, and video files as scene backdrops
- 🔄 **Auto-spin mode** — models rotate automatically, togglable at any time
- 📦 **Custom OBJ/MTL parser** — loads and centers arbitrary `.obj` models with associated materials

## Controls

| Input | Action |
|---|---|
| Mouse drag | Rotate both models manually |
| Mouse wheel | Zoom in / out |
| `Space` | Toggle auto-spin |
| `←` / `→` | Change auto-spin direction |
| `↑` / `↓` | Tilt models up / down |
| `Z` / `X` | Tilt models side to side |
| `B` | Cycle background image |
| `G` / `H` | Decrease / increase glow intensity |
| `N` | Cycle glow color |
| `Esc` | Exit |

## Tech Stack

- **[Pygame](https://www.pygame.org/)** — window/context management and input handling
- **[PyOpenGL](http://pyopengl.sourceforge.net/)** — low-level 3D rendering
- **[PyGLM](https://github.com/Zuzu-Typ/PyGLM)** — matrix/vector math for transforms, camera, and projection
- **[NumPy](https://numpy.org/)** — numerical operations on vertex/frame data
- **[imageio](https://imageio.readthedocs.io/)** & **[Pillow](https://python-pillow.org/)** — GIF and video decoding for animated backgrounds

## Getting Started

### Prerequisites

- Python 3.x
- A GPU/driver combo with OpenGL support

### Installation

```bash
git clone https://github.com/elleyen6/marvel3D.git
cd marvel3D
pip install pygame PyOpenGL PyOpenGL_accelerate PyGLM numpy imageio pillow
```

### Run

```bash
python main.py
```

## Notes

- Textures are matched automatically from the `map_Kd` / `map_Bump` / `map_Ns` entries in each `.mtl` file, falling back to a keyword search (`BaseColor`, `Normal`, `Roughness`) inside the corresponding texture folder if the MTL paths don't resolve.
- Model geometry is automatically centered and normalized on load, so custom `.obj` files of different scales can be dropped in with minimal changes.

*A personal project exploring real-time 3D rendering fundamentals with Python and OpenGL.*
