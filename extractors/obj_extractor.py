def parse_obj_to_model_py(obj_filename, output_file):
    vertices = []
    indices = []

    temp_vertices = []
    temp_texcoords = []

    vertex_dict = {}
    index_counter = 0

    with open(obj_filename, 'r', encoding='utf-8', errors='ignore') as file:
        for line in file:
            if line.startswith('v '):
                parts = line.strip().split()
                x, y, z = map(float, parts[1:4])
                temp_vertices.append((x, y, z))
            elif line.startswith('vt '):
                parts = line.strip().split()
                u, v = map(float, parts[1:3])
                temp_texcoords.append((u, v))
            elif line.startswith('f '):
                face_indices = []
                parts = line.strip().split()[1:]
                for part in parts:
                    vals = part.split('/')
                    v_idx = int(vals[0]) - 1
                    vt_idx = int(vals[1]) - 1 if len(vals) > 1 and vals[1] else None

                    key = (v_idx, vt_idx)
                    if key not in vertex_dict:
                        vx, vy, vz = temp_vertices[v_idx]
                        if vt_idx is not None and vt_idx < len(temp_texcoords):
                            u, v = temp_texcoords[vt_idx]
                        else:
                            u, v = 0.0, 0.0
                        # Using default white color
                        vertices.extend([vx, vy, vz, 1.0, 1.0, 1.0, u, v])
                        vertex_dict[key] = index_counter
                        index_counter += 1

                    face_indices.append(vertex_dict[key])

                if len(face_indices) >= 3:
                    for i in range(1, len(face_indices) - 1):
                        indices.extend([face_indices[0], face_indices[i], face_indices[i + 1]])

    with open(output_file, 'w') as f:
        f.write("vertices = [\n")
        for i in range(0, len(vertices), 8):
            f.write(f"    {vertices[i]:.6f}, {vertices[i+1]:.6f}, {vertices[i+2]:.6f}, "
                    f"{vertices[i+3]:.2f}, {vertices[i+4]:.2f}, {vertices[i+5]:.2f}, "
                    f"{vertices[i+6]:.6f}, {vertices[i+7]:.6f},\n")
        f.write("]\n\n")
        f.write("indices = [\n")
        for i in range(0, len(indices), 3):
            f.write(f"    {indices[i]}, {indices[i+1]}, {indices[i+2]},\n")
        f.write("]\n")

    print(f"✔ Extracted to {output_file} successfully.")

# === Usage ===
if __name__ == "__main__":
    parse_obj_to_model_py("hello.obj", "model.py")
