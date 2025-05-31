from OpenGL.GL import *
import pygame
import os

vertex_shader_src = """
#version 330 core
layout (location = 0) in vec3 aPos;
layout (location = 1) in vec3 aNormal;
layout (location = 2) in vec2 aTexCoord;

uniform mat4 model;  
uniform mat4 projection;
uniform mat4 view;

out vec3 FragPos;
out vec3 Normal;
out vec2 TexCoord;

void main()
{
    FragPos = vec3(model * vec4(aPos, 1.0));
    Normal = mat3(transpose(inverse(model))) * aNormal;
    TexCoord = aTexCoord;
    gl_Position = projection * view * model * vec4(aPos, 1.0);
}
"""

fragment_shader_src = """
#version 330 core
out vec4 FragColor;

in vec3 FragPos;
in vec3 Normal;
in vec2 TexCoord;

uniform vec3 lightPos;
uniform vec3 viewPos;
uniform sampler2D diffuseMap;
uniform sampler2D normalMap;
uniform sampler2D roughnessMap;
uniform bool useTextures;

// Glow effect parameters
uniform float glowIntensity = 0.3;  // Intensity of the glow
uniform vec3 glowColor = vec3(0.2, 0.8, 0.1);  // Green glow color for Hulk

void main()
{
    // Sample textures
    vec4 diffuseColor = useTextures ? texture(diffuseMap, TexCoord) : vec4(0.90, 0.85, 0.75, 1.0);
    float roughness = useTextures ? texture(roughnessMap, TexCoord).r : 0.5;
    
    // Ambient light
    float ambientStrength = 0.3;
    vec3 ambient = ambientStrength * diffuseColor.rgb;
    
    // Directional light
    vec3 norm = normalize(Normal);
    vec3 lightDir = normalize(lightPos - FragPos);
    float diff = max(dot(norm, lightDir), 0.0);
    vec3 diffuse = diff * diffuseColor.rgb;
    
    // Specular highlights (adjust based on roughness)
    vec3 viewDir = normalize(viewPos - FragPos);
    vec3 reflectDir = reflect(-lightDir, norm);
    float shininess = (1.0 - roughness) * 128.0;
    float spec = pow(max(dot(viewDir, reflectDir), 0.0), shininess);
    vec3 specular = (0.5 * spec) * vec3(1.0 - roughness);
    
    // Add a secondary fill light from the opposite side
    vec3 fillLightDir = normalize(vec3(-lightPos.x, lightPos.y, -lightPos.z));
    float fillDiff = max(dot(norm, fillLightDir), 0.0) * 0.3; // 30% strength
    vec3 fillLight = fillDiff * diffuseColor.rgb;
    
    // Calculate rim lighting for glow effect (stronger at edges)
    float rim = 1.0 - max(dot(viewDir, norm), 0.0);
    rim = smoothstep(0.3, 1.0, rim);  // Adjusted for wider rim
    vec3 glow = rim * glowIntensity * glowColor * 1.5;  // Increased intensity
    
    // Calculate fresnel effect (stronger at edges of model)
    float fresnelPower = 3.0;  // Increased for more dramatic effect
    float fresnel = pow(1.0 - max(dot(viewDir, norm), 0.0), fresnelPower);
    vec3 fresnelGlow = fresnel * glowColor * glowIntensity * 2.0;  // Increased intensity
    
    // Add subtle energy field effect
    float energyField = sin(FragPos.x * 10.0 + FragPos.y * 10.0 + FragPos.z * 10.0) * 0.5 + 0.5;
    energyField = pow(energyField, 3.0) * 0.15 * glowIntensity;
    
    // Add pulsing effect
    float time = gl_FragCoord.x * 0.01 + gl_FragCoord.y * 0.01;
    float pulse = (sin(time) * 0.5 + 0.5) * 0.5 * glowIntensity;
    
    // Combine all lighting components including glow
    vec3 result = ambient + diffuse + specular + fillLight;
    
    // Add glow on top of regular lighting
    result += glow + fresnelGlow;
    
    // Add energy field and pulse
    result += energyField * glowColor + pulse * glowColor * fresnel;
    
    // Ensure we don't exceed maximum brightness
    result = min(result, vec3(1.0));
    
    FragColor = vec4(result, diffuseColor.a);
}
"""

# Background shader sources
background_vertex_shader_src = """
#version 330 core
layout (location = 0) in vec3 aPos;
layout (location = 1) in vec3 aNormal;
layout (location = 2) in vec2 aTexCoord;

out vec2 TexCoord;

void main()
{
    TexCoord = aTexCoord;
    gl_Position = vec4(aPos, 1.0);
}
"""

background_fragment_shader_src = """
#version 330 core
out vec4 FragColor;
in vec2 TexCoord;

uniform sampler2D backgroundTexture;

void main()
{
    FragColor = texture(backgroundTexture, TexCoord);
}
"""

def compile_shader(shader_type, source):
    shader = glCreateShader(shader_type)
    glShaderSource(shader, source)
    glCompileShader(shader)

    if glGetShaderiv(shader, GL_COMPILE_STATUS) != GL_TRUE:
        raise RuntimeError(glGetShaderInfoLog(shader).decode())

    return shader

def create_shader_program():
    vertex_shader = compile_shader(GL_VERTEX_SHADER, vertex_shader_src)
    fragment_shader = compile_shader(GL_FRAGMENT_SHADER, fragment_shader_src)

    shader_program = glCreateProgram()
    glAttachShader(shader_program, vertex_shader)
    glAttachShader(shader_program, fragment_shader)
    glLinkProgram(shader_program)

    if glGetProgramiv(shader_program, GL_LINK_STATUS) != GL_TRUE:
        raise RuntimeError(glGetProgramInfoLog(shader_program).decode())

    glDeleteShader(vertex_shader)
    glDeleteShader(fragment_shader)

    return shader_program

def create_background_shader():
    """Create a simple shader program just for rendering the background"""
    vertex_shader = compile_shader(GL_VERTEX_SHADER, background_vertex_shader_src)
    fragment_shader = compile_shader(GL_FRAGMENT_SHADER, background_fragment_shader_src)
    
    shader_program = glCreateProgram()
    glAttachShader(shader_program, vertex_shader)
    glAttachShader(shader_program, fragment_shader)
    glLinkProgram(shader_program)
    
    # Check for linking errors
    success = glGetProgramiv(shader_program, GL_LINK_STATUS)
    if not success:
        print("ERROR::SHADER::PROGRAM::LINKING_FAILED")
        print(glGetProgramInfoLog(shader_program).decode())
    
    # Delete the shaders as they're linked into our program now and no longer necessary
    glDeleteShader(vertex_shader)
    glDeleteShader(fragment_shader)
    
    return shader_program

def load_texture(filepath):
    """Load texture from file using Pygame"""
    if not os.path.exists(filepath):
        print(f"Warning: Texture file not found: {filepath}")
        # Create a default texture (checkerboard)
        surface = pygame.Surface((64, 64))
        surface.fill((200, 200, 200))
        for x in range(32):
            for y in range(32):
                if (x < 16 and y < 16) or (x >= 16 and y >= 16):
                    pygame.draw.rect(surface, (100, 100, 100), (x*2, y*2, 2, 2))
    else:
        try:
            surface = pygame.image.load(filepath)
            print(f"Successfully loaded image: {filepath}, size: {surface.get_size()}")
        except pygame.error as e:
            print(f"Error loading texture {filepath}: {e}")
            # Create a default texture
            surface = pygame.Surface((64, 64))
            surface.fill((255, 0, 255))  # Use magenta for error
    
    # Convert to RGBA if needed
    if surface.get_bitsize() < 32:
        surface = surface.convert_alpha()
    
    # Get texture data
    tex_data = pygame.image.tostring(surface, "RGBA", 1)
    width, height = surface.get_size()
    
    # Create OpenGL texture
    tex_id = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, tex_id)
    
    # Check if this is a background texture by looking at the filename
    is_background = 'bg' in os.path.basename(filepath).lower()
    
    # Set texture parameters for both regular textures and backgrounds
    # These settings work well for all types of textures
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    
    # Upload texture data
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0, GL_RGBA, GL_UNSIGNED_BYTE, tex_data)
    
    # Generate mipmaps for model textures only
    if not is_background:
        glGenerateMipmap(GL_TEXTURE_2D)
    
    print(f"Created OpenGL texture with ID: {tex_id}")
    return tex_id

def create_shadow_texture(size=256, outer_color=(50, 50, 50, 5), inner_color=(10, 10, 10, 100)):
    """Create a circular gradient texture for the shadow/base"""
    surface = pygame.Surface((size, size), pygame.SRCALPHA)
    
    # Calculate center and max radius
    center = (size // 2, size // 2)
    max_radius = size // 2
    
    # Draw gradient
    for radius in range(max_radius, -1, -1):
        # Calculate alpha based on radius (darker in center, lighter outside)
        ratio = radius / max_radius
        # Invert the ratio to make center darker
        inverted_ratio = 1 - ratio
        alpha = int(inner_color[3] * (inverted_ratio**2) + outer_color[3] * (ratio**2))
        
        # Calculate color at this radius - blend between inner and outer colors
        color = (
            int(inner_color[0] * (inverted_ratio) + outer_color[0] * ratio),
            int(inner_color[1] * (inverted_ratio) + outer_color[1] * ratio),
            int(inner_color[2] * (inverted_ratio) + outer_color[2] * ratio),
            alpha
        )
        
        # Draw circle
        pygame.draw.circle(surface, color, center, radius)
    
    # Convert surface to texture
    tex_data = pygame.image.tostring(surface, "RGBA", 1)
    
    # Create OpenGL texture
    tex_id = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, tex_id)
    
    # Set texture parameters
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    
    # Upload texture data
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, size, size, 0, GL_RGBA, GL_UNSIGNED_BYTE, tex_data)
    
    return tex_id
