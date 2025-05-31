import pygame
from pygame.locals import *
from OpenGL.GL import *
import glm
import config
import os
from shader import create_shader_program, load_texture, create_background_shader, create_shadow_texture
from model_loader import create_model_from_data
import numpy as np
import imageio

# Try to import PIL for better GIF handling
try:
    from PIL import Image, ImageSequence
    has_pillow = True
    print("PIL/Pillow loaded successfully - Enhanced GIF support enabled")
except ImportError:
    has_pillow = False
    print("PIL/Pillow not found - Using fallback GIF support")

# def create_circular_base(radius, segments, height=-0.02):
#     """Create a circular base/shadow beneath the statue"""
#     vertices = []
#     indices = []
    
#     # Center vertex
#     vertices.extend([0, height, 0, 0, 1, 0, 0.5, 0.5])
#     center_idx = 0
    
#     # Create circle vertices
#     for i in range(segments):
#         angle = 2.0 * np.pi * i / segments
#         x = radius * np.cos(angle)
#         z = radius * np.sin(angle)
        
#         # Position, normal, texture coords
#         vertices.extend([x, height, z, 0, 1, 0, 0.5 + 0.5 * np.cos(angle), 0.5 + 0.5 * np.sin(angle)])
        
#         # Create triangle indices
#         if i < segments - 1:
#             indices.extend([center_idx, i + 1, i + 2])
#         else:
#             indices.extend([center_idx, i + 1, 1])  # Connect back to first vertex
            
#     return vertices, indices

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

def get_image_dimensions(filepath):
    """Get the dimensions of an image file"""
    try:
        surface = pygame.image.load(filepath)
        return surface.get_size()
    except Exception as e:
        print(f"Error loading image {filepath}: {e}")
        return (0, 0)

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
        import traceback
        traceback.print_exc()
        # Create a default magenta surface
        surface = pygame.Surface((64, 64))
        surface.fill((255, 0, 255))
        return [surface], 100

def load_video(filepath):
    """Load a video file and return its frames"""
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
        import traceback
        traceback.print_exc()
        
        # Create a default surface indicating video loading failed
        surface = pygame.Surface((400, 300))
        surface.fill((64, 64, 64))  # Dark gray instead of magenta
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
        import traceback
        traceback.print_exc()
        # Create a default magenta surface
        surface = pygame.Surface((64, 64))
        surface.fill((255, 0, 255))
        return [surface], 100

def main():
    # Try to import imageio for GIF/video support
    try:
        # Check if imageio is available (already imported at the top)
        has_imageio = True
        print("ImageIO loaded successfully - Video support enabled")
    except Exception:
        has_imageio = False
        print("ImageIO not properly configured - Video support disabled")

    pygame.init()
    # Use the exact dimensions from config
    display = (config.DISPLAY_WIDTH, config.DISPLAY_HEIGHT)
    screen = pygame.display.set_mode(display, DOUBLEBUF | OPENGL)
    pygame.display.set_caption("Marvel 3D Viewer")

    # Set background to black so any gaps will be black
    glClearColor(0, 0, 0, 1)
    
    # Enable depth test and blending
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

    # Create main shader program for 3D model
    shader_program = create_shader_program()
    
    # Create background shader program
    bg_shader_program = create_background_shader()
    
    # Use main shader program initially
    glUseProgram(shader_program)

    model_loc = glGetUniformLocation(shader_program, "model")
    projection_loc = glGetUniformLocation(shader_program, "projection")
    view_loc = glGetUniformLocation(shader_program, "view")
    light_loc = glGetUniformLocation(shader_program, "lightPos")
    view_pos_loc = glGetUniformLocation(shader_program, "viewPos")
    use_textures_loc = glGetUniformLocation(shader_program, "useTextures")
    
    # Get glow effect uniform locations
    glow_intensity_loc = glGetUniformLocation(shader_program, "glowIntensity")
    glow_color_loc = glGetUniformLocation(shader_program, "glowColor")
    
    # Set initial glow parameters
    glow_intensity = 0.0 
    glow_color = [0.1, 0.4, 0.9]  # Green glow for Hulk
    
    # Set glow uniforms
    glUniform1f(glow_intensity_loc, glow_intensity)
    glUniform3f(glow_color_loc, *glow_color)

    # Adjust FOV for better view
    projection = glm.perspective(glm.radians(45), display[0] / display[1], 0.1, 100.0)
    
    # Camera and zoom settings
    initial_camera_distance = 15.0  # Start far away
    target_camera_distance = 5.0    # Target distance to zoom to (increased to see both models)
    camera_distance = initial_camera_distance  # Current camera distance
    min_camera_distance = 2.0       # Increased minimum distance
    max_camera_distance = 8.0       # Increased maximum distance
    zoom_speed = 0.5
    
    # Animation settings
    is_intro_animation = True
    intro_animation_speed = 0.02  # Lower values make the animation slower
    
    # Compute initial view matrix
    view = glm.lookAt(glm.vec3(0, 0.0, camera_distance), glm.vec3(0, 0.0, 0), glm.vec3(0, 1, 0))
    view_pos = glm.vec3(0, 0.0, camera_distance)
    
    # Adjust light position for better illumination
    light_pos = glm.vec3(2, 2, 2)

    glUniformMatrix4fv(projection_loc, 1, GL_FALSE, glm.value_ptr(projection))
    glUniformMatrix4fv(view_loc, 1, GL_FALSE, glm.value_ptr(view))
    glUniform3f(light_loc, *light_pos)
    glUniform3f(view_pos_loc, *view_pos)

    # Load background image texture
    try:
        bg_images = ['backgroundPictures/bg4.gif']
        current_bg_index = 0
        
        # Check if the file exists
        bg_filename = bg_images[current_bg_index]
        if not os.path.exists(bg_filename):
            print(f"ERROR: Background file not found: {bg_filename}")
            # Try with absolute path
            full_path = os.path.join(os.getcwd(), bg_filename)
            print(f"Trying with full path: {full_path}")
            if os.path.exists(full_path):
                bg_filename = full_path
            else:
                print(f"ERROR: Still can't find background file at {full_path}")
        
        # Check if it's an animated file (gif/video)
        is_animated = bg_filename.lower().endswith(('.gif', '.mp4', '.avi', '.mov'))
        
        # Variables for animation
        bg_frames = []
        bg_frame_time = 100  # Default frame time in milliseconds
        bg_current_frame = 0
        bg_last_frame_time = pygame.time.get_ticks()
        
        if is_animated and (has_imageio or has_pillow):
            print(f"Loading animated background: {bg_filename}")
            # Handle animated backgrounds
            if bg_filename.lower().endswith('.gif') and has_pillow:
                bg_frames, bg_frame_time = load_animated_gif(bg_filename)
            elif bg_filename.lower().endswith('.gif') and has_imageio:
                bg_frames, bg_frame_time = load_animated_gif_imageio(bg_filename)
            else:  # Video file
                bg_frames, bg_frame_time = load_video(bg_filename)
                
            # Load the first frame as texture
            if bg_frames:
                surface = bg_frames[0]
                tex_data = pygame.image.tostring(surface, "RGBA", 1)
                width, height = surface.get_size()
                
                # Create OpenGL texture
                bg_texture = glGenTextures(1)
                glBindTexture(GL_TEXTURE_2D, bg_texture)
                
                # Set texture parameters
                glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
                glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
                glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
                glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
                
                # Upload texture data
                glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0, GL_RGBA, GL_UNSIGNED_BYTE, tex_data)
                
                print(f"Loaded animated background: {bg_filename} ({len(bg_frames)} frames)")
            else:
                # Fallback to static texture if frames couldn't be loaded
                is_animated = False
                print(f"Falling back to static loading for: {bg_filename}")
                bg_texture = load_texture(bg_filename)
        else:
            # Handle static image backgrounds
            is_animated = False
            print(f"Loading static background: {bg_filename}")
            bg_texture = load_texture(bg_filename)
            
        print(f"Loaded background texture: {bg_filename} (ID: {bg_texture})")
    except Exception as e:
        print(f"Error loading background texture: {e}")
        import traceback
        traceback.print_exc()
        bg_texture = None
        bg_images = []
        current_bg_index = 0
        is_animated = False
        bg_frames = []

    # Create background quad that fills the exact display dimensions
    bg_vertices, bg_indices = create_background_quad()
    bg_VAO, bg_EBO, bg_count = create_model_from_data(bg_vertices, bg_indices)

    # Load Venus de Milo from OBJ file and textures from MTL file
    try:
        print("Loading Marvel model...")
        obj_path = 'marvel.obj'
        mtl_path = 'marvel.mtl'
        
        # Load textures from MTL file
        textures = parse_mtl(mtl_path)
        print(f"Found Marvel textures: {textures}")
        
        # Load textures into OpenGL
        marvel_texture_ids = {}
        marvel_has_textures = False
        
        # Textures/colors
        if textures['diffuse']:
            marvel_texture_ids['diffuse'] = load_texture(textures['diffuse'])
            marvel_has_textures = True
            print(f"Loaded Marvel diffuse texture: {textures['diffuse']}")
        
        if textures['normal']:
            marvel_texture_ids['normal'] = load_texture(textures['normal'])
            print(f"Loaded Marvel normal texture: {textures['normal']}")
        
        if textures['roughness']:
            marvel_texture_ids['roughness'] = load_texture(textures['roughness'])
            print(f"Loaded Marvel roughness texture: {textures['roughness']}")
        
        # Now load the Marvel model vertices and indices
        marvel_vertices, marvel_indices = load_obj(obj_path)
        marvel_VAO, marvel_EBO, marvel_count = create_model_from_data(marvel_vertices, marvel_indices)
        
        print("Loading Wolverine model...")
        wolverine_obj_path = 'wolverine.obj'
        wolverine_mtl_path = 'wolverine.mtl'
        
        # Load Wolverine textures from MTL file
        wolverine_textures = parse_mtl(wolverine_mtl_path)
        print(f"Found Wolverine textures: {wolverine_textures}")
        
        # Load Wolverine textures into OpenGL
        wolverine_texture_ids = {}
        wolverine_has_textures = False
        
        # Check for Wolverine texture in wolverineTextures folder
        wolverine_texture_path = 'wolverineTextures/mat1_c.jpg'
        if os.path.exists(wolverine_texture_path):
            wolverine_texture_ids['diffuse'] = load_texture(wolverine_texture_path)
            wolverine_has_textures = True
            print(f"Loaded Wolverine diffuse texture: {wolverine_texture_path}")
        
        # Load the Wolverine model vertices and indices
        wolverine_vertices, wolverine_indices = load_obj(wolverine_obj_path)
        wolverine_VAO, wolverine_EBO, wolverine_count = create_model_from_data(wolverine_vertices, wolverine_indices)
        
        # Set use_textures flag for Marvel initially
        glUniform1i(use_textures_loc, int(marvel_has_textures))
        
        # Create circular shadow/base
        # base_radius = 0.6  # Adjust size as needed
        # base_vertices, base_indices = create_circular_base(base_radius, 32)
        # base_VAO, base_EBO, base_count = create_model_from_data(base_vertices, base_indices)
        
        # Create shadow texture
        shadow_texture = create_shadow_texture(size=512, inner_color=(5, 5, 5, 100), outer_color=(35, 35, 35, 5))
        
    except Exception as e:
        print(f"Error loading models: {e}")
        import traceback
        traceback.print_exc()
        pygame.quit()
        return

    clock = pygame.time.Clock()
    
    # Rotation angles
    y_angle = 0.0  # For spinning around Y axis
    x_angle = 0.0  # For tilting up/down
    z_angle = 0.0  # For tilting side to side
    
    # Auto-spin settings
    auto_spin = False
    spin_direction = 1  # 1 for clockwise, -1 for counter-clockwise
    auto_spin_speed = 0.8  # Degrees per frame
    
    # Speed settings
    spin_speed = 2.0
    mouse_sensitivity = 0.5
    
    # Mouse tracking variables
    mouse_dragging = False
    last_mouse_pos = [0, 0]
    screen_center = [display[0] // 2, display[1] // 2]
    
    # Glow effect control variables
    n_key_pressed = False
    current_glow_preset = 0
    
    pygame.mouse.set_visible(True)
    
    print("Controls:")
    print("- Two models are displayed: Marvel (left) and Wolverine (right)")
    print("- Both models automatically spin when program starts")
    print("- Mouse wheel: Zoom in and out")
    print("- Left/Right arrow keys: Change spin direction")
    print("- Mouse drag: Manually rotate both models (temporarily stops auto-spin)")
    print("- Up/Down arrow keys: Tilt both models up/down")
    print("- Z/X keys: Tilt both models side to side")
    print("- Space bar: Toggle auto-spin on/off")
    print("- B key: Change background image")
    print("- G/H keys: Decrease/Increase glow intensity")
    print("- N key: Change glow color")
    print("- ESC: Exit")

    # Main game loop
    running = True
    while running:
        # Track if the mouse was used this frame
        mouse_used = False
        view_changed = False

        for event in pygame.event.get():
            if event.type == QUIT:
                running = False
            elif event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                    running = False
                elif event.key == K_SPACE:
                    # Toggle auto-spin
                    auto_spin = not auto_spin
                    print(f"Auto-spin {'enabled' if auto_spin else 'disabled'}")
                elif event.key == K_b and bg_images:
                    # Change background image
                    current_bg_index = (current_bg_index + 1) % len(bg_images)
                    
                    # Delete old texture
                    if bg_texture:
                        glDeleteTextures(1, [bg_texture])
                    
                    # Load new texture
                    try:
                        bg_filename = bg_images[current_bg_index]
                        print(f"Attempting to load: {bg_filename}")
                        
                        # Make sure the file exists
                        if not os.path.exists(bg_filename):
                            print(f"WARNING: File not found: {bg_filename}")
                            
                        is_animated = bg_filename.lower().endswith(('.gif', '.mp4', '.avi', '.mov'))
                        
                        if is_animated and (has_imageio or has_pillow):
                            # Handle animated backgrounds
                            if bg_filename.lower().endswith('.gif') and has_pillow:
                                bg_frames, bg_frame_time = load_animated_gif(bg_filename)
                            elif bg_filename.lower().endswith('.gif') and has_imageio:
                                bg_frames, bg_frame_time = load_animated_gif_imageio(bg_filename)
                            else:  # Video file
                                bg_frames, bg_frame_time = load_video(bg_filename)
                                
                            # Reset animation variables
                            bg_current_frame = 0
                            bg_last_frame_time = pygame.time.get_ticks()
                            
                            # Load the first frame as texture
                            if bg_frames:
                                surface = bg_frames[0]
                                tex_data = pygame.image.tostring(surface, "RGBA", 1)
                                width, height = surface.get_size()
                                
                                # Create OpenGL texture
                                bg_texture = glGenTextures(1)
                                glBindTexture(GL_TEXTURE_2D, bg_texture)
                                
                                # Set texture parameters
                                glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
                                glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
                                glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
                                glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
                                
                                # Upload texture data
                                glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0, GL_RGBA, GL_UNSIGNED_BYTE, tex_data)
                                
                                print(f"Loaded animated background: {bg_filename} ({len(bg_frames)} frames)")
                            else:
                                # Fallback to static texture if frames couldn't be loaded
                                is_animated = False
                                bg_frames = []
                                bg_texture = load_texture(bg_filename)
                                print(f"Falling back to static loading for: {bg_filename}")
                        else:
                            # Handle static image backgrounds
                            is_animated = False
                            bg_frames = []
                            bg_texture = load_texture(bg_filename)
                        
                        print(f"Changed background to: {bg_filename}")
                    except Exception as e:
                        print(f"Error loading background texture: {e}")
                        import traceback
                        traceback.print_exc()
                        bg_texture = None
                        is_animated = False
                        bg_frames = []
            elif event.type == MOUSEWHEEL:
                # Handle mouse wheel for zooming
                camera_distance -= event.y * zoom_speed
                # Clamp to min/max distance
                camera_distance = max(min_camera_distance, min(max_camera_distance, camera_distance))
                view_changed = True
            elif event.type == MOUSEBUTTONDOWN:
                if event.button == 1:  # Left mouse button
                    mouse_dragging = True
                    last_mouse_pos = event.pos
                    # Temporarily disable auto-spin while dragging
                    auto_spin = False
            elif event.type == MOUSEBUTTONUP:
                if event.button == 1:  # Left mouse button
                    mouse_dragging = False
            elif event.type == MOUSEMOTION:
                if mouse_dragging:
                    # Calculate mouse movement delta
                    delta_x = event.pos[0] - last_mouse_pos[0]
                    delta_y = event.pos[1] - last_mouse_pos[1]
                    
                    # Update rotation based on mouse movement
                    y_angle += delta_x * mouse_sensitivity
                    x_angle += delta_y * mouse_sensitivity
                    
                    last_mouse_pos = event.pos
                    mouse_used = True

        # Get keyboard state for additional controls
        keys = pygame.key.get_pressed()
        
        # Change spin direction with left/right keys
        if keys[K_LEFT]:
            spin_direction = -1  # Counter-clockwise
            auto_spin = True
        if keys[K_RIGHT]:
            spin_direction = 1  # Clockwise
            auto_spin = True
            
        # Tilt model up/down with up/down keys
        if keys[K_UP]:
            x_angle += spin_speed
        if keys[K_DOWN]:
            x_angle -= spin_speed
            
        # Tilt side to side with Z/X keys
        if keys[K_z]:
            z_angle += spin_speed
        if keys[K_x]:
            z_angle -= spin_speed

        # Apply auto-spin if enabled and mouse not being used
        if auto_spin and not mouse_used:
            y_angle += auto_spin_speed * spin_direction
        
        # Handle intro animation (smooth zoom-in)
        if is_intro_animation:
            # Smoothly zoom in to the target distance
            if camera_distance > target_camera_distance:
                # Smooth interpolation for natural feel
                camera_distance -= (camera_distance - target_camera_distance) * intro_animation_speed
                
                # If we're close enough to the target, end the animation
                if abs(camera_distance - target_camera_distance) < 0.1:
                    camera_distance = target_camera_distance
                    is_intro_animation = False
                
                # Update view matrix for the new camera distance
                view = glm.lookAt(glm.vec3(0, 0.0, camera_distance), glm.vec3(0, 0.0, 0), glm.vec3(0, 1, 0))
                view_pos = glm.vec3(0, 0.0, camera_distance)
                glUniformMatrix4fv(view_loc, 1, GL_FALSE, glm.value_ptr(view))
                glUniform3f(view_pos_loc, *view_pos)
            else:
                is_intro_animation = False
            
        # Update view matrix if camera distance changed by mouse wheel
        elif view_changed:
            view = glm.lookAt(glm.vec3(0, 0.0, camera_distance), glm.vec3(0, 0.0, 0), glm.vec3(0, 1, 0))
            view_pos = glm.vec3(0, 0.0, camera_distance)
            glUniformMatrix4fv(view_loc, 1, GL_FALSE, glm.value_ptr(view))
            glUniform3f(view_pos_loc, *view_pos)

        # Change glow intensity with G/H keys
        if keys[K_g]:
            glow_intensity = max(0.0, glow_intensity - 0.01)
            glUniform1f(glow_intensity_loc, glow_intensity)
            print(f"Glow intensity: {glow_intensity:.2f}")
        if keys[K_h]:
            glow_intensity = min(1.0, glow_intensity + 0.01)
            glUniform1f(glow_intensity_loc, glow_intensity)
            print(f"Glow intensity: {glow_intensity:.2f}")
            
        # Change glow color with N key (cycle through presets)
        if keys[K_n] and not n_key_pressed:
            n_key_pressed = True
            # Cycle through different glow colors
            glow_presets = [
                [0.1, 0.4, 0.9],  # Blue
                [0.2, 0.8, 0.1],  # Green
                [0.9, 0.2, 0.1],  # Red
                [0.8, 0.6, 0.1],  # Yellow
                [0.7, 0.2, 0.7]   # Purple
            ]
            current_glow_preset = (current_glow_preset + 1) % len(glow_presets)
            glow_color = glow_presets[current_glow_preset]
            glUniform3f(glow_color_loc, *glow_color)
            print(f"Glow color: {glow_color}")
        elif not keys[K_n]:
            n_key_pressed = False

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        
        # Draw background first (ensure it's always behind everything)
        if bg_texture:
            # Switch to background shader
            glUseProgram(bg_shader_program)
            
            # Disable depth testing temporarily to ensure background is drawn
            glDisable(GL_DEPTH_TEST)
            
            # Bind the background texture
            glActiveTexture(GL_TEXTURE0)
            glBindTexture(GL_TEXTURE_2D, bg_texture)
            
            # Set the background texture uniform
            bg_tex_loc = glGetUniformLocation(bg_shader_program, "backgroundTexture")
            if bg_tex_loc != -1:
                glUniform1i(bg_tex_loc, 0)
            else:
                print("Warning: Could not find backgroundTexture uniform location")
            
            # Draw the background quad
            glBindVertexArray(bg_VAO)
            glDrawElements(GL_TRIANGLES, bg_count, GL_UNSIGNED_INT, None)
            
            # Re-enable depth testing
            glEnable(GL_DEPTH_TEST)
            
            # Switch back to main shader program
            glUseProgram(shader_program)
        
        # Activate textures for statue
        if marvel_has_textures:
            # Diffuse map - texture unit 0
            if 'diffuse' in marvel_texture_ids:
                glActiveTexture(GL_TEXTURE0)
                glBindTexture(GL_TEXTURE_2D, marvel_texture_ids['diffuse'])
                glUniform1i(glGetUniformLocation(shader_program, "diffuseMap"), 0)
            
            # Normal map - texture unit 1
            if 'normal' in marvel_texture_ids:
                glActiveTexture(GL_TEXTURE1)
                glBindTexture(GL_TEXTURE_2D, marvel_texture_ids['normal'])
                glUniform1i(glGetUniformLocation(shader_program, "normalMap"), 1)
            
            # Roughness map - texture unit 2
            if 'roughness' in marvel_texture_ids:
                glActiveTexture(GL_TEXTURE2)
                glBindTexture(GL_TEXTURE_2D, marvel_texture_ids['roughness'])
                glUniform1i(glGetUniformLocation(shader_program, "roughnessMap"), 2)

        # Create model matrix for Marvel statue (positioned on the left)
        marvel_model_matrix = glm.mat4(3.0)
        
        # Apply scaling
        marvel_model_matrix = glm.scale(marvel_model_matrix, glm.vec3(3.0, 3.0, 3.0))
        
        # Position Marvel on the left side
        marvel_model_matrix = glm.translate(marvel_model_matrix, glm.vec3(-0.4, 0, 0))
            
        # Apply rotations from mouse and keyboard
        marvel_model_matrix = glm.rotate(marvel_model_matrix, glm.radians(y_angle), glm.vec3(0, 1, 0))
        marvel_model_matrix = glm.rotate(marvel_model_matrix, glm.radians(x_angle), glm.vec3(1, 0, 0))
        marvel_model_matrix = glm.rotate(marvel_model_matrix, glm.radians(z_angle), glm.vec3(0, 0, 1))

        # Set use_textures flag for Marvel
        glUniform1i(use_textures_loc, int(marvel_has_textures))

        # Pass the Marvel model matrix to the shader
        glUniformMatrix4fv(model_loc, 1, GL_FALSE, glm.value_ptr(marvel_model_matrix))

        # Draw the Marvel statue
        glBindVertexArray(marvel_VAO)
        glDrawElements(GL_TRIANGLES, marvel_count, GL_UNSIGNED_INT, None)
        
        # Now draw the Wolverine model on the right side
        if wolverine_has_textures:
            # Activate Wolverine textures
            if 'diffuse' in wolverine_texture_ids:
                glActiveTexture(GL_TEXTURE0)
                glBindTexture(GL_TEXTURE_2D, wolverine_texture_ids['diffuse'])
                glUniform1i(glGetUniformLocation(shader_program, "diffuseMap"), 0)
        
        # Create model matrix for Wolverine statue (positioned on the right)
        wolverine_model_matrix = glm.mat4(1.0)
        
        # Apply scaling
        wolverine_model_matrix = glm.scale(wolverine_model_matrix, glm.vec3(3.0, 3.0, 3.0))
        
        # Position Wolverine on the right side
        wolverine_model_matrix = glm.translate(wolverine_model_matrix, glm.vec3(0.4, 0, 0))
            
        # Apply rotations from mouse and keyboard
        wolverine_model_matrix = glm.rotate(wolverine_model_matrix, glm.radians(y_angle), glm.vec3(0, 1, 0))
        wolverine_model_matrix = glm.rotate(wolverine_model_matrix, glm.radians(x_angle), glm.vec3(1, 0, 0))
        wolverine_model_matrix = glm.rotate(wolverine_model_matrix, glm.radians(z_angle), glm.vec3(0, 0, 1))

        # Set use_textures flag for Wolverine
        glUniform1i(use_textures_loc, int(wolverine_has_textures))

        # Pass the Wolverine model matrix to the shader
        glUniformMatrix4fv(model_loc, 1, GL_FALSE, glm.value_ptr(wolverine_model_matrix))

        # Draw the Wolverine statue
        glBindVertexArray(wolverine_VAO)
        glDrawElements(GL_TRIANGLES, wolverine_count, GL_UNSIGNED_INT, None)
        
        # Draw the shadow/base for Marvel (left side)
        # Use texture for shadow
        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, shadow_texture)
        glUniform1i(use_textures_loc, 1)
        glUniform1i(glGetUniformLocation(shader_program, "diffuseMap"), 0)
        
        # Create base model matrix for Marvel (keep rotation around Y axis only)
        # marvel_base_model = glm.mat4(1.0)
        # marvel_base_model = glm.scale(marvel_base_model, glm.vec3(2.0, 1.0, 2.0))  # Wider but not taller
        # marvel_base_model = glm.translate(marvel_base_model, glm.vec3(-1.0, 0, 0))  # Position on left
        # marvel_base_model = glm.rotate(marvel_base_model, glm.radians(y_angle), glm.vec3(0, 1, 0))
        
        # Position shadow slightly above the floor to avoid z-fighting
        # marvel_base_model = glm.translate(marvel_base_model, glm.vec3(0, -0.98, 0))
        
        # glUniformMatrix4fv(model_loc, 1, GL_FALSE, glm.value_ptr(marvel_base_model))
        
        # Draw the Marvel base
        # glBindVertexArray(base_VAO)
        # glDrawElements(GL_TRIANGLES, base_count, GL_UNSIGNED_INT, None)
        
        # Draw the shadow/base for Wolverine (right side)
        # Create base model matrix for Wolverine (keep rotation around Y axis only)
        wolverine_base_model = glm.mat4(1.0)
        wolverine_base_model = glm.scale(wolverine_base_model, glm.vec3(2.0, 1.0, 2.0))  # Wider but not taller
        wolverine_base_model = glm.translate(wolverine_base_model, glm.vec3(1.0, 0, 0))  # Position on right
        wolverine_base_model = glm.rotate(wolverine_base_model, glm.radians(y_angle), glm.vec3(0, 1, 0))
        
        # Position shadow slightly above the floor to avoid z-fighting
        # wolverine_base_model = glm.translate(wolverine_base_model, glm.vec3(0, -0.98, 0))
        
        glUniformMatrix4fv(model_loc, 1, GL_FALSE, glm.value_ptr(wolverine_base_model))
        
        # Draw the Wolverine base
        # glBindVertexArray(base_VAO)
        # glDrawElements(GL_TRIANGLES, base_count, GL_UNSIGNED_INT, None)
        
        # Reset texture usage for next frame
        glUniform1i(use_textures_loc, int(marvel_has_textures))

        # Update animated background if needed
        if is_animated and bg_frames:
            current_time = pygame.time.get_ticks()
            if current_time - bg_last_frame_time > bg_frame_time:
                bg_last_frame_time = current_time
                bg_current_frame = (bg_current_frame + 1) % len(bg_frames)
                
                # Update texture with new frame
                surface = bg_frames[bg_current_frame]
                tex_data = pygame.image.tostring(surface, "RGBA", 1)
                width, height = surface.get_size()
                
                # Bind texture and update
                glBindTexture(GL_TEXTURE_2D, bg_texture)
                glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0, GL_RGBA, GL_UNSIGNED_BYTE, tex_data)

        pygame.display.flip()
        clock.tick(config.FPS)

    # Cleanup
    if 'marvel_texture_ids' in locals():
        for tex_id in marvel_texture_ids.values():
            glDeleteTextures(1, [tex_id])
    
    if 'wolverine_texture_ids' in locals():
        for tex_id in wolverine_texture_ids.values():
            glDeleteTextures(1, [tex_id])
    
    if 'shadow_texture' in locals():
        glDeleteTextures(1, [shadow_texture])
        
    if 'bg_texture' in locals() and bg_texture:
        glDeleteTextures(1, [bg_texture])

    glDeleteVertexArrays(1, [marvel_VAO])
    glDeleteBuffers(1, [marvel_EBO])
    glDeleteVertexArrays(1, [wolverine_VAO])
    glDeleteBuffers(1, [wolverine_EBO])
    # glDeleteVertexArrays(1, [base_VAO])
    # glDeleteBuffers(1, [base_EBO])
    glDeleteVertexArrays(1, [bg_VAO])
    glDeleteBuffers(1, [bg_EBO])
    glDeleteProgram(shader_program)
    glDeleteProgram(bg_shader_program)
    pygame.quit()

if __name__ == "__main__":
    main()
