import pygame
from pygame.locals import *
from OpenGL.GL import *
import glm
import config
from shader import create_shader_program
from model_loader import create_model_from_data
import model

def main():
    pygame.init()
    display = (config.DISPLAY_WIDTH, config.DISPLAY_HEIGHT)
    pygame.display.set_mode(display, DOUBLEBUF | OPENGL)

    glEnable(GL_DEPTH_TEST)
    glClearColor(*config.BACKGROUND_COLOR)

    shader_program = create_shader_program()
    glUseProgram(shader_program)

    model_loc = glGetUniformLocation(shader_program, "model")
    projection_loc = glGetUniformLocation(shader_program, "projection")
    view_loc = glGetUniformLocation(shader_program, "view")
    light_loc = glGetUniformLocation(shader_program, "lightPos")
    view_pos_loc = glGetUniformLocation(shader_program, "viewPos")

    projection = glm.perspective(glm.radians(80), display[0] / display[1], 0.1, 100.0)
    view = glm.lookAt(glm.vec3(0, 2.0, 15.0), glm.vec3(0, 1.0, 0), glm.vec3(0, 1, 0))
    view_pos = glm.vec3(0, 2.0, 15.0)
    light_pos = glm.vec3(0, 0, 0)

    glUniformMatrix4fv(projection_loc, 1, GL_FALSE, glm.value_ptr(projection))
    glUniformMatrix4fv(view_loc, 1, GL_FALSE, glm.value_ptr(view))
    glUniform3f(light_loc, *light_pos)
    glUniform3f(view_pos_loc, *view_pos)

    VAO, EBO, count = create_model_from_data(model.vertices, model.indices)

    clock = pygame.time.Clock()
    angle_y = 0.0
    angle_x = 0.0
    rotation_speed_mouse = 0.3
    rotation_speed_key = 1.5

    pygame.event.set_grab(True)
    pygame.mouse.set_visible(False)

    running = True
    while running:
        keys = pygame.key.get_pressed()

        # Arrow keys
        if keys[K_LEFT]:
            angle_y -= rotation_speed_key
        if keys[K_RIGHT]:
            angle_y += rotation_speed_key

        for event in pygame.event.get():
            if event.type == QUIT:
                running = False
            if event.type == KEYDOWN and event.key == K_ESCAPE:
                running = False

        # Mouse motion (when left button is held)
        if pygame.mouse.get_pressed()[0]:
            rel = pygame.mouse.get_rel()
            angle_y += rel[0] * rotation_speed_mouse
            angle_x += rel[1] * rotation_speed_mouse
        else:
            pygame.mouse.get_rel()  # Reset

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        model_matrix = glm.mat4(1.0)
        model_matrix = glm.rotate(model_matrix, glm.radians(angle_y), glm.vec3(0.0, 1.0, 0.0))
        model_matrix = glm.rotate(model_matrix, glm.radians(angle_x), glm.vec3(1.0, 0.0, 0.0))
        glUniformMatrix4fv(model_loc, 1, GL_FALSE, glm.value_ptr(model_matrix))

        glBindVertexArray(VAO)
        glDrawElements(GL_TRIANGLES, count, GL_UNSIGNED_INT, None)

        pygame.display.flip()
        clock.tick(config.FPS)

    glDeleteVertexArrays(1, [VAO])
    glDeleteBuffers(1, [EBO])
    glDeleteProgram(shader_program)
    pygame.quit()

if __name__ == "__main__":
    main()
