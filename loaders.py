import os
import pygame
import numpy as np
import traceback
from OpenGL.GL import *

try:
    from PIL import Image, ImageSequence
    has_pillow = True
    print("PIL/Pillow loaded successfully - Enhanced GIF support enabled")
except ImportError:
    has_pillow = False
    print("PIL/Pillow not found - Using fallback GIF support")

try:
    import imageio
    has_imageio = True
    print("ImageIO loaded successfully - Video support enabled")
except ImportError:
    has_imageio = False
    print("ImageIO not properly configured - Video support disabled")


def load_obj(filename):
    """Load basic OBJ file with vertices and normals"""
    vertices = []
    normals = []
    texcoords = []
    faces = []
    
    with open(filename, 'r') as f:
        for line in f:
            if line.startswith('#'): 
                continue
                
            values = line.split()
            if not values: 
                continue
                
            if values[0] == 'v':
                # Vertex coordinates
                vertices.append([float(values[1]), float(values[2]), float(values[3])])
            elif values[0] == 'vn':
                # Vertex normals
                normals.append([float(values[1]), float(values[2]), float(values[3])])
            elif values[0] == 'vt':
                # Texture coordinates
                texcoords.append([float(values[1]), float(values[2])])
            elif values[0] == 'f':
                # Faces
                face = []
                # Parse f v1/vt1/vn1 v2/vt2/vn2 v3/vt3/vn3 ...
                for v in values[1:]:
                    w = v.split('/')
                    # OBJ file indices start at 1, so we subtract 1
                    face.append([
                        int(w[0]) - 1 if w[0] else 0,  # vertex
                        int(w[1]) - 1 if len(w) > 1 and w[1] else 0,  # texcoord
                        int(w[2]) - 1 if len(w) > 2 and w[2] else 0,  # normal
                    ])
                faces.append(face)
    
    print(f"Loaded {len(vertices)} vertices, {len(normals)} normals, {len(texcoords)} texcoords, {len(faces)} faces")
    
    # Find model bounds to center it
    min_coords = [float('inf'), float('inf'), float('inf')]
    max_coords = [float('-inf'), float('-inf'), float('-inf')]
    for v in vertices:
        for i in range(3):
            min_coords[i] = min(min_coords[i], v[i])
            max_coords[i] = max(max_coords[i], v[i])
    
    # Calculate center and dimensions
    center = [(min_coords[i] + max_coords[i]) / 2 for i in range(3)]
    dimensions = [max_coords[i] - min_coords[i] for i in range(3)]
    max_dimension = max(dimensions)
    
    print(f"Model dimensions: {dimensions}, Center: {center}")
    
    # Convert to format suitable for OpenGL
    vertex_data = []
    indices = []
    
    # Dictionary to track unique vertices
    unique_vertices = {}
    index_count = 0
    
    for face in faces:
        # For triangle fans, we need to triangulate
        for i in range(1, len(face)-1):
            # Process vertices: v0, vi, vi+1 for each face
            for j in [0, i, i+1]:
                # Get vertex information 
                v_idx, vt_idx, vn_idx = face[j]
                
                # Create a unique vertex key
                key = (v_idx, vt_idx, vn_idx)
                
                if key not in unique_vertices:
                    # If vertex doesn't exist yet, add it
                    v = vertices[v_idx]
                    
                    # Center and normalize vertices
                    centered_v = [(v[i] - center[i]) / max_dimension for i in range(3)]
                    
                    # Normal (default if not specified)
                    n = normals[vn_idx] if vn_idx < len(normals) else [0, 0, 1]
                    
                    # Texcoord (default if not specified)
                    t = texcoords[vt_idx] if vt_idx < len(texcoords) and len(texcoords) > 0 else [0, 0]
                    
                    # Add vertex data (position, normal, texcoord)
                    vertex_data.extend([centered_v[0], centered_v[1], centered_v[2], n[0], n[1], n[2], t[0], t[1]])
                    
                    # Store the new index
                    unique_vertices[key] = index_count
                    index_count += 1
                
                # Add the index
                indices.append(unique_vertices[key])
    
    return vertex_data, indices


def load_animated_gif(filepath):
    """Load an animated GIF and return its frames using Pillow (PIL)"""
    try:
        # Open the GIF file
        gif = Image.open(filepath)
        frames = []
        durations = []
        
        # Convert each frame to a Pygame surface
        for frame in ImageSequence.Iterator(gif):
            # Convert PIL Image to RGBA mode
            frame_rgba = frame.convert("RGBA")
            
            # Create a Pygame surface from the PIL image
            frame_size = frame_rgba.size
            pygame_surface = pygame.Surface(frame_size, pygame.SRCALPHA)
            
            # Get pixel data and copy to surface
            pixel_data = frame_rgba.tobytes()
            pygame_surface.get_buffer().write(pixel_data)
            
            frames.append(pygame_surface)
            
            # Get frame duration if available
            try:
                duration = frame.info.get('duration', 100)  # In milliseconds
                durations.append(duration)
            except:
                durations.append(100)  # Default to 100ms
        
        # Calculate average frame duration
        avg_duration = sum(durations) // len(durations) if durations else 100
        
        print(f"Successfully loaded GIF with {len(frames)} frames, avg duration: {avg_duration}ms")
        return frames, avg_duration
    except Exception as e:
        print(f"Error loading GIF {filepath}: {e}")
        traceback.print_exc()
        # Create a default magenta surface
        surface = pygame.Surface((64, 64))
        surface.fill((255, 0, 255))
        return [surface], 100


def load_animated_gif_imageio(filepath):
    """Load an animated GIF and return its frames using imageio (fallback method)"""
    try:
        # Read the GIF file
        gif = imageio.mimread(filepath)
        frames = []
        for frame in gif:
            # Convert directly to surface without using surfarray
            width, height = frame.shape[1], frame.shape[0]
            surface = pygame.Surface((width, height), pygame.SRCALPHA)
            for y in range(height):
                for x in range(width):
                    r, g, b = frame[y, x, 0], frame[y, x, 1], frame[y, x, 2]
                    a = 255  # Alpha is fully opaque if not present
                    if frame.shape[2] > 3:  # If there's an alpha channel
                        a = frame[y, x, 3]
                    surface.set_at((x, y), (r, g, b, a))
            frames.append(surface)
        
        print(f"Successfully loaded GIF with imageio: {len(frames)} frames")
        # Return the frames and timing information
        return frames, 100  # Assume 100ms per frame by default
    except Exception as e:
        print(f"Error loading GIF with imageio {filepath}: {e}")
        traceback.print_exc()
        # Create a default magenta surface
        surface = pygame.Surface((64, 64))
        surface.fill((255, 0, 255))
        return [surface], 100


def load_video(filepath):
    """Load a video file and return its frames"""
    if not has_imageio:
        print("ImageIO not available - Video support disabled")
        surface = pygame.Surface((400, 300))
        surface.fill((64, 64, 64))  # Dark gray instead of magenta
        return [surface], 100
        
    try:
        print(f"Attempting to load video: {filepath}")
        
        # Check if file exists first
        if not os.path.exists(filepath):
            print(f"Video file not found: {filepath}")
            raise FileNotFoundError(f"Video file not found: {filepath}")
        
        # Open the video file
        try:
            video = imageio.get_reader(filepath)
            print("Video reader opened successfully")
        except Exception as reader_error:
            print(f"Failed to open video: {reader_error}")
            raise reader_error
        
        # Get FPS information
        try:
            meta_data = video.get_meta_data()
            fps = meta_data.get('fps', 30)
            print(f"Video metadata: {meta_data}")
        except Exception as meta_error:
            print(f"Could not get metadata: {meta_error}")
            fps = 30  # Default FPS if metadata is not available
            
        frame_time = int(1000 / fps)  # Convert to milliseconds
        
        print(f"Video FPS: {fps}, Frame time: {frame_time}ms")
        
        # Extract frames (load all frames, but downsample if needed for memory management)
        frames = []
        frame_count = 0
        max_frames = 1000  # Allow up to 1000 frames (about 33 seconds at 30fps)
        frame_skip = 1     # Skip frames if video is too long
        
        # Calculate frame skip if video is very long
        try:
            total_frames = video.count_frames()
            if total_frames > max_frames:
                frame_skip = total_frames // max_frames
                print(f"Video has {total_frames} frames, will skip every {frame_skip} frames")
        except:
            print("Could not determine total frame count, loading all frames")
        
        try:
            for i, frame in enumerate(video):
                # Skip frames if needed to manage memory
                if frame_skip > 1 and i % frame_skip != 0:
                    continue
                
                try:
                    # Convert frame to RGB if it's not already
                    if len(frame.shape) == 3:
                        if frame.shape[2] == 4:  # RGBA
                            rgb_frame = frame[:, :, :3]  # Remove alpha channel
                        else:
                            rgb_frame = frame
                    else:
                        print(f"Unexpected frame shape: {frame.shape}")
                        continue
                    
                    # Create pygame surface
                    height, width = rgb_frame.shape[:2]
                    surface = pygame.Surface((width, height))
                    
                    # Convert numpy array to pygame surface
                    # Transpose the array to match pygame's format (width, height, channels)
                    rgb_frame_transposed = np.transpose(rgb_frame, (1, 0, 2))
                    pygame.surfarray.blit_array(surface, rgb_frame_transposed)
                    
                    frames.append(surface)
                    frame_count += 1
                    
                    if frame_count % 50 == 0:  # Progress indicator every 50 loaded frames
                        print(f"Loaded {frame_count} frames (source frame {i+1})...")
                        
                except Exception as frame_error:
                    print(f"Error processing frame {i}: {frame_error}")
                    continue
                    
        except Exception as iteration_error:
            print(f"Error iterating through video frames: {iteration_error}")
        
        video.close()
        
        if not frames:
            print("No frames were successfully loaded from video")
            raise Exception("No frames could be loaded from video")
        
        # Adjust frame time based on frame skipping
        actual_frame_time = frame_time * frame_skip
        
        print(f"Successfully loaded video with {len(frames)} frames at {fps} fps (skipping {frame_skip-1} frames, effective fps: {fps/frame_skip:.1f})")
        return frames, actual_frame_time
        
    except Exception as e:
        print(f"Error loading video {filepath}: {e}")
        traceback.print_exc()
        
        # Create a default surface indicating video loading failed
        surface = pygame.Surface((400, 300))
        surface.fill((64, 64, 64))  # Dark gray instead of magenta
        return [surface], 100
