import trimesh
import math

def extract_glb_to_model_py(glb_file, output_file):
    scene = trimesh.load(glb_file, force='scene')

    all_vertices = []
    all_indices = []
    vertex_offset = 0

    # Create rotation matrices
    rotation_z = trimesh.transformations.rotation_matrix(
        angle=math.radians(-90),  # Rotate -90° around Z (to move base to center)
        direction=[0, 0, 1],
        point=[0, 0, 0]
    )

    rotation_x = trimesh.transformations.rotation_matrix(
        angle=math.radians(180),  # Rotate 90° around X (to make it stand up)
        direction=[1, 0, 0],
        point=[0, 0, 0]
    )

    # Combine rotations: first Z, then X
    combined_rotation = trimesh.transformations.concatenate_matrices(rotation_z, rotation_x)

    for name, geometry in scene.geometry.items():
        geometry.apply_transform(combined_rotation)

        vertices = geometry.vertices
        colors = geometry.visual.vertex_colors[:, :3] / 255.0 if geometry.visual.kind == 'vertex' else [[1.0, 1.0, 1.0]] * len(vertices)
        texcoords = geometry.visual.uv if geometry.visual.uv is not None else [[0.0, 0.0]] * len(vertices)

        for i in range(len(vertices)):
            vx, vy, vz = vertices[i]
            r, g, b = colors[i] if len(colors) > i else (1.0, 1.0, 1.0)
            u, v = texcoords[i] if len(texcoords) > i else (0.0, 0.0)
            all_vertices.extend([vx, vy, vz, r, g, b, u, v])

        indices = geometry.faces.flatten()
        all_indices.extend(indices + vertex_offset)
        vertex_offset += len(vertices)

    with open(output_file, 'w') as f:
        f.write("vertices = [\n")
        for i in range(0, len(all_vertices), 8):
            f.write(f"    {all_vertices[i]:.6f}, {all_vertices[i+1]:.6f}, {all_vertices[i+2]:.6f}, "
                    f"{all_vertices[i+3]:.2f}, {all_vertices[i+4]:.2f}, {all_vertices[i+5]:.2f}, "
                    f"{all_vertices[i+6]:.6f}, {all_vertices[i+7]:.6f},\n")
        f.write("]\n\n")
        f.write("indices = [\n")
        for i in range(0, len(all_indices), 3):
            f.write(f"    {all_indices[i]}, {all_indices[i+1]}, {all_indices[i+2]},\n")
        f.write("]\n")

    print(f"✔ Extracted GLB to {output_file} with fixed orientation.")

# === Usage ===
if __name__ == "__main__":
    extract_glb_to_model_py("higokumaru__honkai_impact_3rd.glb", "model.py")
