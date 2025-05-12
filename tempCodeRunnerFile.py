from OpenGL.GL import *

vertex_shader_src = """
#version 330 core
layout (location = 0) in vec3 aPos;
layout (location = 1) in vec3 aColor;
uniform mat4 model;  
uniform mat4 projection;
uniform mat4 view;

out vec3 FragPos;
out vec3 Color;
void main()
{
    FragPos = vec3(model * vec4(aPos, 1.0));
    Color = aColor;
    gl_Position = projection *  view * model * vec4(aPos, 1.0);
}
"""

fragment_shader_src = """
#version 330 core
out vec4 FragColor;
in vec3 FragPos;
in vec3 Color;

uniform vec3 lightPos;
uniform vec3 viewPos;
void main()
{
    vec3 ambient = 0.3 * Color;

    vec3 norm = normalize(vec3(0.0, 0.0, 1.0));  // Approx. normal
    vec3 lightDir = normalize(lightPos - FragPos);
    float diff = max(dot(norm, lightDir), 0.0);
    vec3 diffuse = diff * Color;

    vec3 viewDir = normalize(viewPos - FragPos);
    vec3 reflectDir = reflect(-lightDir, norm);
    float spec = pow(max(dot(viewDir, reflectDir), 0.0), 32);
    vec3 specular = 0.5 * spec * vec3(1.0);

    vec3 result = ambient + diffuse + specular;
    FragColor = vec4(result, 1.0);
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
