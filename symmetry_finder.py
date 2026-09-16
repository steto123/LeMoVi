import numpy as np
from rdkit import Chem

def get_coords_and_masses(mol):
    conf = mol.GetConformer()
    coords = []
    masses = []
    elements = []
    for atom in mol.GetAtoms():
        pos = conf.GetAtomPosition(atom.GetIdx())
        coords.append([pos.x, pos.y, pos.z])
        masses.append(atom.GetMass())
        elements.append(atom.GetSymbol())
    return np.array(coords), np.array(masses), elements

def normalize(v):
    norm = np.linalg.norm(v)
    if norm < 1e-6:
        return v
    return v / norm

def rotation_matrix(axis, theta):
    axis = normalize(axis)
    x, y, z = axis
    cos_t = np.cos(theta)
    sin_t = np.sin(theta)
    R = np.array([
        [cos_t + x*x*(1-cos_t),   x*y*(1-cos_t) - z*sin_t, x*z*(1-cos_t) + y*sin_t],
        [y*x*(1-cos_t) + z*sin_t, cos_t + y*y*(1-cos_t),   y*z*(1-cos_t) - x*sin_t],
        [z*x*(1-cos_t) - y*sin_t, z*y*(1-cos_t) + x*sin_t, cos_t + z*z*(1-cos_t)]
    ])
    return R

def reflection_matrix(normal):
    n = normalize(normal)
    R = np.eye(3) - 2.0 * np.outer(n, n)
    return R

def is_symmetry_matrix(coords, elements, M, tol=0.2):
    matched = [False] * len(coords)
    for i, c in enumerate(coords):
        c_trans = M @ c
        found = False
        for j, c_ref in enumerate(coords):
            if elements[i] == elements[j] and not matched[j]:
                if np.linalg.norm(c_trans - c_ref) < tol:
                    matched[j] = True
                    found = True
                    break
        if not found:
            return False
    return True

def get_inertia_axes(coords, masses):
    if len(coords) < 2:
        return [np.array([1., 0., 0.]), np.array([0., 1., 0.]), np.array([0., 0., 1.])]
    I = np.zeros((3, 3))
    for c, m in zip(coords, masses):
        x, y, z = c
        I[0, 0] += m * (y**2 + z**2)
        I[1, 1] += m * (x**2 + z**2)
        I[2, 2] += m * (x**2 + y**2)
        I[0, 1] -= m * x * y
        I[1, 0] -= m * x * y
        I[0, 2] -= m * x * z
        I[2, 0] -= m * x * z
        I[1, 2] -= m * y * z
        I[2, 1] -= m * y * z
    
    try:
        evals, evecs = np.linalg.eigh(I)
        return [evecs[:, 0], evecs[:, 1], evecs[:, 2]]
    except:
        return [np.array([1., 0., 0.]), np.array([0., 1., 0.]), np.array([0., 0., 1.])]

def get_candidate_axes(coords, masses):
    candidates = []
    # Inertia axes
    for ax in get_inertia_axes(coords, masses):
        candidates.append(normalize(ax))
    
    # Atom vectors
    for c in coords:
        if np.linalg.norm(c) > 0.1:
            candidates.append(normalize(c))
            
    # Midpoints and differences
    n_atoms = len(coords)
    for i in range(n_atoms):
        for j in range(i + 1, n_atoms):
            c1, c2 = coords[i], coords[j]
            mid = c1 + c2
            if np.linalg.norm(mid) > 0.1:
                candidates.append(normalize(mid))
            diff = c1 - c2
            if np.linalg.norm(diff) > 0.1:
                candidates.append(normalize(diff))
                
    # Cross products of base candidates
    base_candidates = list(candidates)
    for i in range(len(base_candidates)):
        for j in range(i + 1, len(base_candidates)):
            cross = np.cross(base_candidates[i], base_candidates[j])
            if np.linalg.norm(cross) > 0.1:
                candidates.append(normalize(cross))
                
    # Filter unique (up to direction sign)
    unique = []
    for c in candidates:
        is_new = True
        for u in unique:
            if abs(np.dot(c, u)) > 0.98:
                is_new = False
                break
        if is_new:
            unique.append(c)
    return unique

def find_symmetry(mol):
    """
    Analyzes the point group and returns symmetry elements for drawing.
    Returns:
      {
         "point_group": str,
         "center_of_mass": [x, y, z],
         "axes": [{"n": int, "vector": [x,y,z], "label": str}],
         "planes": [{"normal": [x,y,z], "label": str}],
         "inversion": bool
      }
    """
    coords, masses, elements = get_coords_and_masses(mol)
    if len(coords) == 0:
        return {"point_group": "C1", "center_of_mass": [0,0,0], "axes": [], "planes": [], "inversion": False}
        
    com = np.average(coords, axis=0, weights=masses)
    coords_centered = coords - com
    
    # 1. Check linearity
    is_linear = True
    if len(coords_centered) > 1:
        first_vec = normalize(coords_centered[0])
        for c in coords_centered[1:]:
            if np.linalg.norm(c) > 0.1:
                proj = abs(np.dot(normalize(c), first_vec))
                if proj < 0.98:
                    is_linear = False
                    break
    else:
        is_linear = False
        
    # Check inversion center
    has_inversion = is_symmetry_matrix(coords_centered, elements, -np.eye(3))
    
    # Find candidate axes and planes
    candidates = get_candidate_axes(coords_centered, masses)
    
    # Search proper rotation axes C_n (n = 8 down to 2)
    axes_found = [] # list of (n, axis_vector)
    for c_ax in candidates:
        highest_n = 1
        for n in range(8, 1, -1):
            is_cn = True
            for k in range(1, n):
                R = rotation_matrix(c_ax, 2 * np.pi * k / n)
                if not is_symmetry_matrix(coords_centered, elements, R):
                    is_cn = False
                    break
            if is_cn:
                highest_n = n
                break
        if highest_n > 1:
            axes_found.append((highest_n, c_ax))
            
    # Remove duplicate/anti-parallel axes and keep highest n
    unique_axes = []
    for n, ax in sorted(axes_found, key=lambda x: x[0], reverse=True):
        is_new = True
        for un, uax in unique_axes:
            if abs(np.dot(ax, uax)) > 0.98:
                is_new = False
                break
        if is_new:
            unique_axes.append((n, ax))
            
    # Search reflection planes (using candidate axes as normal vectors)
    planes_found = []
    for c_ax in candidates:
        M = reflection_matrix(c_ax)
        if is_symmetry_matrix(coords_centered, elements, M):
            planes_found.append(c_ax)
            
    unique_planes = []
    for pl in planes_found:
        is_new = True
        for upl in unique_planes:
            if abs(np.dot(pl, upl)) > 0.98:
                is_new = False
                break
        if is_new:
            unique_planes.append(pl)
            
    # Classify point group
    point_group = "C1"
    
    if is_linear:
        if has_inversion:
            point_group = "Dinfh"
        else:
            point_group = "Cinfv"
    else:
        if unique_axes:
            principal_n, principal_axis = unique_axes[0]
        else:
            principal_n, principal_axis = 1, None
            
        c3_axes = [ax for n, ax in unique_axes if n == 3]
        c4_axes = [ax for n, ax in unique_axes if n == 4]
        c5_axes = [ax for n, ax in unique_axes if n == 5]
        
        if len(c3_axes) >= 4:
            if len(c5_axes) > 0:
                point_group = "Ih" if unique_planes else "I"
            elif len(c4_axes) > 0:
                point_group = "Oh" if unique_planes else "O"
            else:
                if len(unique_planes) >= 6:
                    point_group = "Td"
                elif has_inversion:
                    point_group = "Th"
                else:
                    point_group = "T"
        else:
            if principal_n > 1:
                perp_c2_count = 0
                for n, ax in unique_axes:
                    if n == 2 and abs(np.dot(ax, principal_axis)) < 0.15:
                        perp_c2_count += 1
                        
                has_perp_c2 = (perp_c2_count >= principal_n) or (principal_n == 2 and perp_c2_count >= 1)
                
                has_h_plane = False
                v_plane_count = 0
                for pl in unique_planes:
                    dot = abs(np.dot(pl, principal_axis))
                    if dot > 0.98:
                        has_h_plane = True
                    elif dot < 0.15:
                        v_plane_count += 1
                        
                if has_perp_c2:
                    if has_h_plane:
                        point_group = f"D{principal_n}h"
                    elif v_plane_count >= principal_n:
                        point_group = f"D{principal_n}d"
                    else:
                        point_group = f"D{principal_n}"
                else:
                    if has_h_plane:
                        point_group = f"C{principal_n}h"
                    elif v_plane_count >= principal_n:
                        point_group = f"C{principal_n}v"
                    else:
                        has_s2n = False
                        s_order = 2 * principal_n
                        S_M = reflection_matrix(principal_axis) @ rotation_matrix(principal_axis, np.pi / principal_n)
                        if is_symmetry_matrix(coords_centered, elements, S_M):
                            has_s2n = True
                        if has_s2n:
                            point_group = f"S{s_order}"
                        else:
                            point_group = f"C{principal_n}"
            else:
                if unique_planes:
                    point_group = "Cs"
                elif has_inversion:
                    point_group = "Ci"
                else:
                    point_group = "C1"
                    
    axes_out = []
    for n, ax in unique_axes:
        axes_out.append({
            "n": int(n),
            "vector": ax.tolist(),
            "label": f"C{n} axis"
        })
        
    planes_out = []
    for pl in unique_planes:
        planes_out.append({
            "normal": pl.tolist(),
            "label": "Spiegelebene (mirror plane)"
        })
        
    return {
        "point_group": point_group,
        "center_of_mass": com.tolist(),
        "axes": axes_out,
        "planes": planes_out,
        "inversion": bool(has_inversion)
    }
