import pygame
import os
import numpy as np
from OpenGL.GL import *
import traceback

def extract_tex_path(path_parts, base_dir):
    """Extract texture path from MTL file and make it relative to base_dir"""
    # Join all parts to handle paths with spaces
    full_path = ' '.join(path_parts)
    
    # Extract the filename from the path
    filename = os.path.basename(full_path)
    
    # Check if the file exists in texture subdirectory
    texture_dir = os.path.join(base_dir, "marvelTextures")
    tex_path = os.path.join(texture_dir, filename)
    
    if os.path.exists(tex_path):
        return tex_path
    
    # If not found, try base directory
    tex_path = os.path.join(base_dir, filename)
    if os.path.exists(tex_path):
        return tex_path
    
    # If still not found, return the original path for error handling
    return full_path

def get_image_dimensions(filepath):
    """Get the dimensions of an image file"""
    try:
        surface = pygame.image.load(filepath)
        return surface.get_size()
    except Exception as e:
        print(f"Error loading image {filepath}: {e}")
        return (0, 0)

def create_background_quad():
    """Create a quad for rendering a background image that fills the entire frame"""
    # Vertices for a quad that completely fills the screen from corner to corner
    # Format: x, y, z, nx, ny, nz, tx, ty
    vertices = [
        # Position              Normal      Texture
        -1.0, -1.0, -0.999,     0, 0, 1,    0, 0,  # Bottom-left
        1.0, -1.0, -0.999,      0, 0, 1,    1, 0,  # Bottom-right
        1.0, 1.0, -0.999,       0, 0, 1,    1, 1,  # Top-right
        -1.0, 1.0, -0.999,      0, 0, 1,    0, 1   # Top-left
    ]
    
    # Indices for two triangles forming the quad
    indices = [0, 1, 2, 0, 2, 3]
    
    return vertices, indices

def create_aspect_ratio_quad(image_width, image_height, viewport_width, viewport_height, depth=-0.9):
    """Create a quad with the correct aspect ratio for the image and viewport"""
    
    # Calculate image aspect ratio
    image_ratio = image_width / image_height
    
    # Calculate viewport aspect ratio
    viewport_ratio = viewport_width / viewport_height
    
    # Calculate quad dimensions to fit while preserving aspect ratio
    if image_ratio > viewport_ratio:
        # Image is wider than viewport (horizontal letterboxing)
        # Scale to fit width
        quad_width = 1.0
        quad_height = (viewport_ratio / image_ratio)
    else:
        # Image is taller than viewport (vertical letterboxing)
        # Scale to fit height
        quad_width = (image_ratio / viewport_ratio)
        quad_height = 1.0
    
    # Vertices for a quad with proper aspect ratio
    # Format: x, y, z, nx, ny, nz, tx, ty
    vertices = [
        # Position                    Normal      Texture
        -quad_width, -quad_height, depth,  0, 0, 1,    0, 0,  # Bottom-left
        quad_width, -quad_height, depth,   0, 0, 1,    1, 0,  # Bottom-right
        quad_width, quad_height, depth,    0, 0, 1,    1, 1,  # Top-right
        -quad_width, quad_height, depth,   0, 0, 1,    0, 1   # Top-left
    ]
    
    # Indices for two triangles forming the quad
    indices = [0, 1, 2, 0, 2, 3]
    
    return vertices, indices

def parse_mtl(filepath):
    """Parse MTL file and extract texture paths"""
    textures = {
        'diffuse': None,
        'normal': None,
        'roughness': None
    }
    
    # Set base directory for texture loading
    base_dir = os.path.dirname(filepath)
    
    try:
        with open(filepath, 'r') as f:
            for line in f:
                parts = line.strip().split()
                if not parts:
                    continue
                
                # Check for texture maps
                if parts[0] == 'map_Kd':  # Diffuse map
                    textures['diffuse'] = extract_tex_path(parts[1:], base_dir)
                elif parts[0] == 'map_Bump':  # Normal map
                    textures['normal'] = extract_tex_path(parts[1:], base_dir)
                elif parts[0] == 'map_Ns':  # Specular/Roughness map
                    textures['roughness'] = extract_tex_path(parts[1:], base_dir)
    except Exception as e:
        print(f"Error parsing MTL file: {e}")
    
    # If we didn't find the textures in the MTL file, try to find them in texture directory
    texture_dir = os.path.join(base_dir, "marvelTextures")
    
    if textures['diffuse'] is None and os.path.exists(texture_dir):
        for filename in os.listdir(texture_dir):
            if "BaseColor" in filename or "@D." in filename:
                textures['diffuse'] = os.path.join(texture_dir, filename)
            elif "Normal" in filename or "@N." in filename:
                textures['normal'] = os.path.join(texture_dir, filename)
            elif "Roughness" in filename or "@S." in filename:  # S might be specular map
                textures['roughness'] = os.path.join(texture_dir, filename)
    
    return textures
