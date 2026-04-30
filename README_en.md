# LeMoVi - Lehnin Molecule Visualizer

This project allows the input of chemical structures via the **Ketcher** 2D editor, performs geometry optimization (using **RDKit** or **xTB**), and displays the result interactively in **3D** (3Dmol.js).

## Startup
1. Run `create_portable_python.bat` to create the necessary Python environment (only needed once).
2. Start the program with `start.bat`.

## Features
- **2D Input**: Full Ketcher editor integrated.
- **Geometry Optimization**: 
  - Fast molecular mechanics optimization (**MMFF94** via RDKit).
  - Precise semi-empirical quantum chemical optimization (**GFN2-xTB**) (see Setup below).
- **Visualization**: Interactive 3D view (Fully offline capable). Choice of Sticks, CPK, Wireframe, or Ball & Stick.
- **Interactive Measurements**: Click atoms in the 3D view to measure them:
  - 2 Atoms = Bond length / Distance (Å)
  - 3 Atoms = Bond angle (°)
  - 4 Atoms = Torsion / Dihedral angle (°)
- **Surface Visualization**: Calculation and visualization of molecular surfaces:
  - **Van der Waals (VDW)** and **Solvent Accessible Surface (SAS)**.
  - **Electrostatic Potential (ESP)**: Color mapping based on Gasteiger partial charges (Red = negative, Blue = positive).
  - **Hydrophobicity (LogP)**: Visualization of polar and lipophilic regions based on Crippen LogP contributions.

## xTB Integration (Optional)
To use xTB optimization, the external binary must be provided:
1. Download the current Windows version of xTB (`xtb-X.X.X-windows-x86_64.zip`): [Grimme-Lab xTB Releases](https://github.com/grimme-lab/xtb/releases)
2. Extract the file.
3. Create a new subfolder named `xtb` in the `LeMoVi` directory.
4. Copy the executable file `xtb.exe` into this folder. The path must be: `LeMoVi\xtb\xtb.exe`
5. The program will now automatically detect xTB when selected in the dropdown menu.

## Requirements
The program is designed as a portable application and requires an installed Python environment in the `portable_python` subfolder (created by the script).
Required libraries:
- PyQt5
- PyQtWebEngine
- rdkit
