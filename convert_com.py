import os
import sys
import re
from rdkit import Chem
from rdkit.Chem import rdDetermineBonds

def clean_filename(name):
    # Keep alphanumeric characters, dashes, and underscores
    return re.sub(r'[^a-zA-Z0-9_\-]', '_', name)

def convert_file(com_path):
    base_name = os.path.splitext(com_path)[0]
    sdf_path = f"{base_name}.sdf"
    mol_dir = f"{base_name}_mol_files"
    
    if not os.path.exists(com_path):
        print(f"Error: {com_path} not found.")
        return
        
    print(f"\nProcessing {com_path}...")
    os.makedirs(mol_dir, exist_ok=True)
    
    with open(com_path, 'r') as f:
        content = f.read()
        
    blocks = re.split(r'(?i)--link1--', content)
    pt = Chem.GetPeriodicTable()
    
    sdf_writer = Chem.SDWriter(sdf_path)
    
    processed_count = 0
    for idx, block in enumerate(blocks):
        lines = [line.strip() for line in block.splitlines()]
        title = None
        charge = 0
        coords = []
        
        phase = 0
        for line in lines:
            if not line:
                if phase == 2:
                    break
                continue
            if line.startswith('%') or line.startswith('#'):
                continue
            if phase == 0:
                title = line
                phase = 1
            elif phase == 1:
                parts = line.split()
                if len(parts) >= 2:
                    try:
                        charge = int(parts[0])
                    except ValueError:
                        pass
                phase = 2
            elif phase == 2:
                parts = line.split()
                if len(parts) >= 4:
                    coords.append(parts)
                else:
                    break
                    
        if not title or not coords:
            continue
            
        xyz_lines = [str(len(coords)), title]
        for coord in coords:
            atomic_num = int(coord[0])
            symbol = pt.GetElementSymbol(atomic_num)
            xyz_lines.append(f"{symbol} {coord[1]} {coord[2]} {coord[3]}")
            
        xyz_block = "\n".join(xyz_lines)
        raw_mol = Chem.MolFromXYZBlock(xyz_block)
        if not raw_mol:
            print(f"[{idx+1}] Failed to load XYZ block for {title}")
            continue
            
        try:
            rdDetermineBonds.DetermineBonds(raw_mol, charge=charge)
        except Exception as e:
            print(f"[{idx+1}] Warning: DetermineBonds failed for {title}: {e}")
            
        raw_mol.SetProp("_Name", title)
        
        # Write to SDF
        sdf_writer.write(raw_mol)
        
        # Write to individual MOL
        safe_title = clean_filename(title)
        mol_filename = f"{idx+1:02d}_{safe_title}.mol"
        mol_path = os.path.join(mol_dir, mol_filename)
        try:
            Chem.MolToMolFile(raw_mol, mol_path)
        except Exception as e:
            print(f"[{idx+1}] Failed to write MOL file for {title}: {e}")
            
        print(f"[{idx+1:02d}] Converted: {title}")
        processed_count += 1
        
    sdf_writer.close()
    print(f"Successfully converted {processed_count} molecules.")
    print(f"SDF file: {sdf_path}")
    print(f"MOL directory: {mol_dir}/")

def main():
    if len(sys.argv) > 1:
        for arg in sys.argv[1:]:
            convert_file(arg)
    else:
        # Default files to convert
        default_files = ["ProbeSetGeom_B3LYP631plusGdp.com", "TestSetGeom_B3LYP631plusGdp.com"]
        for f in default_files:
            if os.path.exists(f):
                convert_file(f)

if __name__ == "__main__":
    main()
