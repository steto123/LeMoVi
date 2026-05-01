import os
import sys
import json
import math
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                             QMessageBox, QSplitter, QStackedWidget, QDialog,
                             QFileDialog, QAction, QMenuBar, QInputDialog)
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QFont, QIcon

try:
    from PyQt5.QtWebEngineWidgets import QWebEngineView
    WEB_ENGINE_AVAILABLE = True
except ImportError:
    QWebEngineView = QWidget
    WEB_ENGINE_AVAILABLE = False

from rdkit import Chem
from rdkit.Chem import AllChem

# Fortgeschrittener 3Dmol.js HTML Wrapper mit Messfunktionen
HTML_3DMOL = """
<!DOCTYPE html>
<html>
<head>
  <script src="3Dmol-min.js"></script>
  <style>
    body { margin: 0; padding: 0; overflow: hidden; background-color: #1e1e1e; font-family: 'Segoe UI', sans-serif;}
    #container { width: 100vw; height: 100vh; position: relative;}
    #info { position: absolute; top: 10px; left: 10px; color: white; background: rgba(0,0,0,0.7); padding: 8px 12px; border-radius: 5px; pointer-events: none; font-size: 13px; border: 1px solid #444;}
  </style>
</head>
<body>
  <div id="container"></div>
  <div id="info">Click atoms for measurements (2: Distance, 3: Angle, 4: Torsion)</div>
  <script>
    var viewer = $3Dmol.createViewer("container", {backgroundColor: "#1e1e1e"});
    var selectedAtoms = [];
    var currentModel = null;
    var showLabels = false;

    var currentSurface = null;
    var currentStyleType = "stick";
    var overlayStates = [];

    function loadMolecule(molBlock, props) {
        viewer.clear();
        overlayStates = [];
        selectedAtoms = [];
        document.getElementById('info').innerHTML = "Molecule loaded. Click atoms for measurements.";
        currentModel = viewer.addModel(molBlock, "mol");
        
        if (props) {
            var atoms = currentModel.selectedAtoms({});
            for(var i=0; i<atoms.length; i++) {
                if (props[i]) {
                    atoms[i].charge = props[i].charge;
                    atoms[i].logp = props[i].logp;
                }
            }
        }
        
        applyStyle(currentStyleType);
        viewer.zoomTo();
        
        // Robuster Klick-Handler für Atome via Viewer
        viewer.setClickable({}, true, function(atom, viewer, event, container) {
            if(atom) {
                handleAtomClick(atom);
            }
        });
        
        viewer.render();
    }

    function addMoleculeOverlay(molBlock, props, colorHex) {
        var model = viewer.addModel(molBlock, "mol");
        if (!currentModel) currentModel = model;
        
        if (props) {
            var atoms = model.selectedAtoms({});
            for(var i=0; i<atoms.length; i++) {
                if (props[i]) {
                    atoms[i].charge = props[i].charge;
                    atoms[i].logp = props[i].logp;
                }
            }
        }
        
        overlayStates.push({visible: true, color: colorHex || ""});
        applyStyle(currentStyleType);
        viewer.zoomTo();
        
        viewer.setClickable({}, true, function(atom, viewer, event, container) {
            if(atom) handleAtomClick(atom);
        });
        
        viewer.render();
    }

    function updateOverlay(index, visible, colorHex) {
        if (overlayStates[index]) {
            overlayStates[index].visible = visible;
            overlayStates[index].color = colorHex;
            applyStyle();
        }
    }

    function applyStyle(styleType) {
        if (styleType) currentStyleType = styleType;
        if (!currentModel) return;
        
        var baseStyle = {};
        if (currentStyleType === "stick") baseStyle = {stick: {radius: 0.15}, sphere: {scale: 0.25}};
        else if (currentStyleType === "sphere") baseStyle = {sphere: {}};
        else if (currentStyleType === "line") baseStyle = {line: {}};
        else if (currentStyleType === "ballstick") baseStyle = {stick: {radius: 0.05}, sphere: {scale: 0.3}};
        
        viewer.setStyle({}, baseStyle);
        
        var models = viewer.models || [];
        for (var i = 1; i < models.length; i++) {
            var m = models[i];
            var state = overlayStates[i - 1];
            if (!state) continue;
            
            if (!state.visible) {
                try { viewer.setStyle({model: m}, {line:{hidden:true}, stick:{hidden:true}, sphere:{hidden:true}}); } catch(e) {}
            } else {
                if (state.color) {
                    var cStyle = JSON.parse(JSON.stringify(baseStyle));
                    if (cStyle.stick) cStyle.stick.color = state.color;
                    if (cStyle.sphere) cStyle.sphere.color = state.color;
                    if (cStyle.line) cStyle.line.color = state.color;
                    try { viewer.setStyle({model: m}, cStyle); } catch(e) {}
                } else {
                    try { viewer.setStyle({model: m}, baseStyle); } catch(e) {}
                }
            }
        }
        
        if (showLabels) updateLabels();
        viewer.render();
    }

    function applySurface(surfaceType) {
        if (!currentModel) return;
        viewer.removeAllSurfaces();
        
        if (surfaceType === "Van der Waals") {
            viewer.addSurface($3Dmol.SurfaceType.VDW, {opacity: 0.85, color: 'white'});
        } else if (surfaceType === "Solvent Accessible") {
            viewer.addSurface($3Dmol.SurfaceType.SAS, {opacity: 0.85, color: 'lightblue'});
        } else if (surfaceType === "Electrostatic Potential") {
            viewer.addSurface($3Dmol.SurfaceType.VDW, {
                opacity: 0.85,
                map: {prop: 'charge', scheme: new $3Dmol.Gradient.RWB(-0.5, 0.5)}
            });
        } else if (surfaceType === "Hydrophobicity (LogP)") {
            viewer.addSurface($3Dmol.SurfaceType.VDW, {
                opacity: 0.85,
                map: {prop: 'logp', scheme: new $3Dmol.Gradient.ROYGB(-0.5, 0.5)}
            });
        }
        viewer.render();
    }

    function toggleLabels(state) {
        showLabels = state;
        updateLabels();
    }

    function updateLabels() {
        viewer.removeAllLabels();
        if (showLabels && currentModel) {
            var atoms = currentModel.selectedAtoms({});
            for (var i = 0; i < atoms.length; i++) {
                var atom = atoms[i];
                var labelText = atom.elem + (atom.serial !== undefined ? atom.serial : (i + 1));
                viewer.addLabel(labelText, {
                    position: {x: atom.x, y: atom.y, z: atom.z}, 
                    backgroundColor: 'black', 
                    fontColor: 'white', 
                    backgroundOpacity: 0.8, 
                    fontSize: 12
                });
            }
        }
        viewer.render();
    }

    function clearMeasurements() {
        selectedAtoms = [];
        viewer.removeAllLabels();
        viewer.removeAllShapes();
        document.getElementById('info').innerHTML = "Measurements cleared. Click atoms.";
        if (showLabels) updateLabels();
        viewer.render();
    }

    function handleAtomClick(atom) {
        if (!atom) return;
        
        // Highlighting des gewählten Atoms (explizite Koordinaten)
        viewer.addSphere({center: {x: atom.x, y: atom.y, z: atom.z}, radius: 0.35, color: 'yellow', opacity: 0.6});
        selectedAtoms.push(atom);
        
        var info = document.getElementById('info');
        var atomName = atom.elem + (atom.serial !== undefined ? atom.serial : selectedAtoms.length);

        if (selectedAtoms.length === 1) {
            info.innerHTML = "Selection 1: " + atomName;
        } else if (selectedAtoms.length === 2) {
            var d = distance(selectedAtoms[0], selectedAtoms[1]).toFixed(3);
            addMeasurementLabel(midpoint(selectedAtoms[0], selectedAtoms[1]), d + " Å");
            info.innerHTML = "Distance: " + d + " Å";
        } else if (selectedAtoms.length === 3) {
            var a = angle(selectedAtoms[0], selectedAtoms[1], selectedAtoms[2]).toFixed(2);
            addMeasurementLabel({x: selectedAtoms[1].x, y: selectedAtoms[1].y, z: selectedAtoms[1].z}, a + "°");
            info.innerHTML = "Angle: " + a + "°";
        } else if (selectedAtoms.length === 4) {
            var t = torsion(selectedAtoms[0], selectedAtoms[1], selectedAtoms[2], selectedAtoms[3]).toFixed(2);
            addMeasurementLabel(midpoint(selectedAtoms[1], selectedAtoms[2]), t + "°");
            info.innerHTML = "Torsion: " + t + "°";
            selectedAtoms = []; // Reset nach Torsion
        }
        viewer.render();
    }

    function addMeasurementLabel(pos, text) {
        viewer.addLabel(text, {
            position: {x: pos.x, y: pos.y, z: pos.z}, 
            backgroundColor: '#0078D4', 
            fontColor: 'white', 
            fontSize: 14, 
            backgroundOpacity: 0.9
        });
    }

    function distance(a, b) {
        return Math.sqrt(Math.pow(a.x-b.x,2) + Math.pow(a.y-b.y,2) + Math.pow(a.z-b.z,2));
    }
    function midpoint(a, b) {
        return {x: (a.x+b.x)/2, y: (a.y+b.y)/2, z: (a.z+b.z)/2};
    }
    function angle(a, b, c) {
        var v1 = {x: a.x-b.x, y: a.y-b.y, z: a.z-b.z};
        var v2 = {x: c.x-b.x, y: c.y-b.y, z: c.z-b.z};
        var dot = v1.x*v2.x + v1.y*v2.y + v1.z*v2.z;
        var m1 = Math.sqrt(v1.x*v1.x + v1.y*v1.y + v1.z*v1.z);
        var m2 = Math.sqrt(v2.x*v2.x + v2.y*v2.y + v2.z*v2.z);
        return Math.acos(Math.max(-1, Math.min(1, dot/(m1*m2)))) * 180 / Math.PI;
    }
    function torsion(a, b, c, d) {
        var v1 = {x: b.x-a.x, y: b.y-a.y, z: b.z-a.z};
        var v2 = {x: c.x-b.x, y: c.y-b.y, z: c.z-b.z};
        var v3 = {x: d.x-c.x, y: d.y-c.y, z: d.z-c.z};
        var n1 = cross(v1, v2);
        var n2 = cross(v2, v3);
        var m1 = Math.sqrt(n1.x*n1.x + n1.y*n1.y + n1.z*n1.z);
        var m2 = Math.sqrt(n2.x*n2.x + n2.y*n2.y + n2.z*n2.z);
        var cos = (n1.x*n2.x + n1.y*n2.y + n1.z*n2.z) / (m1*m2);
        return Math.acos(Math.max(-1, Math.min(1, cos))) * 180 / Math.PI;
    }
    function cross(a, b) {
        return {x: a.y*b.z - a.z*b.y, y: a.z*b.x - a.x*b.z, z: a.x*b.y - a.y*b.x};
    }
  </script>
</body>
</html>
"""


from PyQt5.QtWidgets import QComboBox, QCheckBox, QTableWidget, QTableWidgetItem, QHeaderView

class KetcherDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Draw Molecule - Ketcher")
        self.resize(1100, 750)
        self.setWindowIcon(QIcon(os.path.join(os.path.dirname(__file__), "icon.png")))
        self.layout = QVBoxLayout(self)
        
        if not WEB_ENGINE_AVAILABLE:
            self.layout.addWidget(QLabel("Error: PyQtWebEngine is not installed."))
            return

        self.web_view = QWebEngineView()
        self.web_view.titleChanged.connect(self.on_title)
        
        pth = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ketcher", "standalone", "index.html").replace("\\", "/")
        self.web_view.setUrl(QUrl(f"file:///{pth}"))
        self.layout.addWidget(self.web_view)
        
        self.button_box = QHBoxLayout()
        self.ok_btn = QPushButton("Apply Structure")
        self.ok_btn.setStyleSheet("background-color: #0078D4; color: white; padding: 8px 20px; font-weight: bold; border-radius: 4px;")
        self.ok_btn.clicked.connect(self.request_smiles)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setStyleSheet("padding: 8px 20px; border-radius: 4px;")
        self.cancel_btn.clicked.connect(self.reject)
        
        self.button_box.addStretch()
        self.button_box.addWidget(self.cancel_btn)
        self.button_box.addWidget(self.ok_btn)
        self.layout.addLayout(self.button_box)
        
        self.smiles = ""

    def request_smiles(self):
        js = "window.ketcher.getSmiles().then(s => { document.title = 'SMILES_' + s; }).catch(e => { alert(e); });"
        self.web_view.page().runJavaScript(js)
            
    def on_title(self, title):
        if title.startswith("SMILES_"):
            self.smiles = title[7:]
            self.accept()

class MolViewer3D(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LeMoVi - Lehnin Molecule Visualizer")
        self.resize(1250, 850)
        self.setWindowIcon(QIcon(os.path.join(os.path.dirname(__file__), "icon.png")))
        self.setup_ui()

    def setup_ui(self):
        self.setStyleSheet("""
            QMainWindow, QDialog, QMessageBox { background-color: #1e1e1e; color: white; }
            QLabel { color: #ffffff; font-family: 'Segoe UI'; }
            QLineEdit { background-color: #2d2d2d; color: white; border: 1px solid #444; padding: 6px; border-radius: 4px; }
            QPushButton { background-color: #333; color: white; border: none; padding: 8px 16px; border-radius: 4px; font-family: 'Segoe UI'; }
            QPushButton:hover { background-color: #444; }
            QComboBox { background-color: #333; color: white; border: 1px solid #444; padding: 5px; border-radius: 4px; }
            QComboBox QAbstractItemView { background-color: #333; color: white; selection-background-color: #0078D4; border: 1px solid #444; }
            QCheckBox { color: white; spacing: 5px; }
            QCheckBox::indicator { width: 16px; height: 16px; background-color: #333; border: 1px solid #555; border-radius: 3px; }
            QCheckBox::indicator:checked { background-color: #0078D4; border: 1px solid #0078D4; }
            #OptimizeBtn { background-color: #0078D4; font-weight: bold; }
            #OptimizeBtn:hover { background-color: #0086f0; }
            #ClearBtn { background-color: #c42b1c; }
            #ClearBtn:hover { background-color: #e81123; }
        """)

        self.create_menu()

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)

        # Top Bar (Input & General Actions)
        top_bar = QHBoxLayout()
        self.smiles_input = QLineEdit()
        self.smiles_input.setPlaceholderText("Enter SMILES or Draw...")
        
        self.draw_btn = QPushButton("🖌 Draw")
        self.draw_btn.clicked.connect(self.open_ketcher)
        
        self.method_combo = QComboBox()
        self.method_combo.addItems(["MMFF94 (RDKit)", "xTB (GFN2)"])
        
        self.opt_btn = QPushButton("Optimize")
        self.opt_btn.setObjectName("OptimizeBtn")
        self.opt_btn.clicked.connect(self.optimize_structure)
        
        top_bar.addWidget(QLabel("SMILES:"))
        top_bar.addWidget(self.smiles_input)
        top_bar.addWidget(self.draw_btn)
        top_bar.addWidget(QLabel("Method:"))
        top_bar.addWidget(self.method_combo)
        top_bar.addWidget(self.opt_btn)
        main_layout.addLayout(top_bar)

        # Control Bar (3D Specific)
        ctrl_bar = QHBoxLayout()
        
        ctrl_bar.addWidget(QLabel("Representation:"))
        self.style_combo = QComboBox()
        self.style_combo.addItems(["Sticks & Spheres", "Spheres (CPK)", "Wireframe", "Ball & Stick"])
        self.style_combo.currentTextChanged.connect(self.change_style)
        ctrl_bar.addWidget(self.style_combo)
        
        ctrl_bar.addWidget(QLabel("Surface:"))
        self.surface_combo = QComboBox()
        self.surface_combo.addItems(["None", "Van der Waals", "Solvent Accessible", "Electrostatic Potential", "Hydrophobicity (LogP)"])
        self.surface_combo.currentTextChanged.connect(self.change_surface)
        ctrl_bar.addWidget(self.surface_combo)
        
        self.label_cb = QCheckBox("Atom Labels")
        self.label_cb.toggled.connect(self.toggle_labels)
        ctrl_bar.addWidget(self.label_cb)
        
        ctrl_bar.addStretch()
        
        self.clear_meas_btn = QPushButton("Clear Measurements")
        self.clear_meas_btn.setObjectName("ClearBtn")
        self.clear_meas_btn.clicked.connect(self.clear_measurements)
        ctrl_bar.addWidget(self.clear_meas_btn)
        
        main_layout.addLayout(ctrl_bar)

        # Overlay Control Bar
        self.overlay_table = QTableWidget(0, 3)
        self.overlay_table.setHorizontalHeaderLabels(["Overlay", "Sichtbar", "Farbe"])
        self.overlay_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.overlay_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.overlay_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Interactive)
        self.overlay_table.setColumnWidth(2, 120)
        self.overlay_table.setFixedHeight(120)
        self.overlay_table.verticalHeader().setVisible(False)
        self.overlay_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.overlay_table.setSelectionMode(QTableWidget.NoSelection)
        self.overlay_table.setVisible(False)
        
        # Gallery Bar
        self.gallery_widget = QWidget()
        gallery_layout = QHBoxLayout(self.gallery_widget)
        gallery_layout.setContentsMargins(0, 5, 0, 5)
        
        self.prev_btn = QPushButton("◀ Previous Molecule")
        self.prev_btn.clicked.connect(self.prev_molecule)
        self.next_btn = QPushButton("Next Molecule ▶")
        self.next_btn.clicked.connect(self.next_molecule)
        self.gallery_label = QLabel("Molecule 1 / 1")
        self.gallery_label.setAlignment(Qt.AlignCenter)
        self.gallery_label.setStyleSheet("font-weight: bold;")
        
        gallery_layout.addStretch()
        gallery_layout.addWidget(self.prev_btn)
        gallery_layout.addWidget(self.gallery_label)
        gallery_layout.addWidget(self.next_btn)
        gallery_layout.addStretch()
        
        self.gallery_widget.setVisible(False)
        
        main_layout.addWidget(self.gallery_widget)
        main_layout.addWidget(self.overlay_table)

        # Main View (3D)
        self.web_view = QWebEngineView()
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.web_view.setHtml(HTML_3DMOL, QUrl.fromLocalFile(base_dir + "/"))
        main_layout.addWidget(self.web_view)
        
        self.statusBar().showMessage("Ready")
        self.statusBar().setStyleSheet("color: #aaa; background-color: #111;")

    def open_ketcher(self):
        if not WEB_ENGINE_AVAILABLE:
            QMessageBox.critical(self, "Error", "WebEngine not available.")
            return
        dialog = KetcherDialog(self)
        if dialog.exec_() == QDialog.Accepted and dialog.smiles:
            self.smiles_input.setText(dialog.smiles)
            self.optimize_structure()

    def change_style(self, text):
        style_map = {
            "Sticks & Spheres": "stick",
            "Spheres (CPK)": "sphere",
            "Wireframe": "line",
            "Ball & Stick": "ballstick"
        }
        js = f"applyStyle('{style_map.get(text, 'stick')}');"
        self.web_view.page().runJavaScript(js)

    def change_surface(self, text):
        js = f"applySurface('{text}');"
        self.web_view.page().runJavaScript(js)

    def toggle_labels(self, state):
        js = f"toggleLabels({'true' if state else 'false'});"
        self.web_view.page().runJavaScript(js)

    def clear_measurements(self):
        js = "clearMeasurements();"
        self.web_view.page().runJavaScript(js)

    def optimize_structure(self):
        smiles = self.smiles_input.text().strip()
        if not smiles: return
        method = self.method_combo.currentText()

        try:
            self.statusBar().showMessage(f"Processing SMILES for {method}...")
            mol = Chem.MolFromSmiles(smiles)
            if not mol: raise ValueError("Invalid SMILES code")

            mol = Chem.AddHs(mol)
            params = AllChem.ETKDGv3()
            params.randomSeed = 42
            if AllChem.EmbedMolecule(mol, params) == -1:
                AllChem.EmbedMolecule(mol, randomSeed=42)

            if "MMFF94" in method:
                self.statusBar().showMessage("Generating 3D coordinates & Optimization (MMFF)...")
                AllChem.MMFFOptimizeMolecule(mol)
                self.update_viewer(mol)
                self.statusBar().showMessage("Optimization (MMFF94) completed.")
            else:
                self.run_xtb(mol)
            
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))
            self.statusBar().showMessage("Error bei der Optimierung.")

    def run_xtb(self, mol):
        import subprocess
        import tempfile
        self.statusBar().showMessage("Running xTB Optimization... (this may take a while)")
        
        # Check for xtb
        xtb_exe = os.path.join(os.path.dirname(os.path.abspath(__file__)), "xtb", "xtb.exe")
        if not os.path.exists(xtb_exe):
            QMessageBox.critical(self, "xTB not found", f"Bitte laden Sie xTB herunter und entpacken Sie es nach:\\n{xtb_exe}")
            self.statusBar().showMessage("xTB Optimization aborted.")
            return

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                input_xyz = os.path.join(tmpdir, "input.xyz")
                Chem.MolToXYZFile(mol, input_xyz)
                
                cmd = [xtb_exe, "input.xyz", "--opt"]
                subprocess.run(cmd, cwd=tmpdir, check=True, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
                    
                xtbopt_xyz = os.path.join(tmpdir, "xtbopt.xyz")
                if not os.path.exists(xtbopt_xyz):
                    raise ValueError("No optimized structure found.")
                    
                with open(xtbopt_xyz, "r") as f:
                    lines = f.readlines()
                
                conf = mol.GetConformer()
                for i, line in enumerate(lines[2:]):
                    parts = line.split()
                    if len(parts) >= 4:
                        x, y, z = map(float, parts[1:4])
                        conf.SetAtomPosition(i, (x, y, z))
                        
                self.update_viewer(mol)
                self.statusBar().showMessage("Optimization (xTB) completed.")
        except Exception as e:
            QMessageBox.critical(self, "xTB Error", f"xTB ist fehlgeschlagen:\\n{str(e)}")
            self.statusBar().showMessage("xTB Error.")

    def update_viewer(self, mol):
        self.current_mol = mol
        self.overlay_table.setRowCount(0)
        self.overlay_table.setVisible(False)
        try:
            from rdkit.Chem import Crippen
            AllChem.ComputeGasteigerCharges(mol)
            logp_contribs = Crippen.CrippenContribs(mol)
        except Exception as e:
            print("Warning: Could not compute properties:", e)
            logp_contribs = [(0,0)] * mol.GetNumAtoms()

        props = []
        for i, atom in enumerate(mol.GetAtoms()):
            charge = 0.0
            logp = 0.0
            try:
                charge = float(atom.GetProp("_GasteigerCharge"))
                if math.isnan(charge) or math.isinf(charge): charge = 0.0
            except:
                pass
            try:
                logp = logp_contribs[i][0]
            except:
                pass
            props.append({"charge": charge, "logp": logp})

        mol_block = Chem.MolToMolBlock(mol)
        js = f"loadMolecule({json.dumps(mol_block)}, {json.dumps(props)});"
        self.web_view.page().runJavaScript(js)
        self.change_surface(self.surface_combo.currentText())

    def create_menu(self):
        menubar = self.menuBar()
        menubar.setStyleSheet("background-color: #2d2d2d; color: white;")
        file_menu = menubar.addMenu("Datei")

        pubchem_action = QAction("PubChem Search...", self)
        pubchem_action.triggered.connect(self.pubchem_search)
        file_menu.addAction(pubchem_action)

        import_action = QAction("Import Molecule...", self)
        import_action.triggered.connect(self.import_molecule)
        file_menu.addAction(import_action)

        overlay_action = QAction("Overlay Molecule...", self)
        overlay_action.triggered.connect(self.overlay_molecule)
        file_menu.addAction(overlay_action)

        export_action = QAction("Export Molecule...", self)
        export_action.triggered.connect(self.export_molecule)
        file_menu.addAction(export_action)

    def import_molecule(self):
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Import Molecule", "", 
            "Supported Formats (*.mol *.sdf *.pdb *.smi);;MDL MOL (*.mol);;SDF (*.sdf);;PDB (*.pdb);;SMILES (*.smi)", 
            options=options
        )
        if file_name:
            try:
                mol = None
                self.sdf_molecules = []
                self.sdf_index = 0
                ext = os.path.splitext(file_name)[1].lower()
                if ext == '.mol':
                    mol = Chem.MolFromMolFile(file_name, removeHs=False)
                elif ext == '.sdf':
                    suppl = Chem.SDMolSupplier(file_name, removeHs=False)
                    self.sdf_molecules = [m for m in suppl if m is not None]
                    if self.sdf_molecules:
                        mol = self.sdf_molecules[0]
                elif ext == '.pdb':
                    mol = Chem.MolFromPDBFile(file_name, removeHs=False)
                elif ext == '.smi':
                    with open(file_name, 'r') as f:
                        smi = f.readline().strip().split()[0]
                    mol = Chem.MolFromSmiles(smi)
                    if mol:
                        mol = Chem.AddHs(mol)
                        AllChem.EmbedMolecule(mol)
                    
                if mol is None:
                    QMessageBox.warning(self, "Import Error", "Could not read molecule from file.")
                    return
                
                if len(self.sdf_molecules) > 1:
                    self.gallery_widget.setVisible(True)
                    self.gallery_label.setText(f"Molecule 1 / {len(self.sdf_molecules)}")
                else:
                    self.gallery_widget.setVisible(False)
                    
                try:
                    smi_text = Chem.MolToSmiles(Chem.RemoveHs(mol))
                    self.smiles_input.setText(smi_text)
                except:
                    pass
                self.update_viewer(mol)
                self.statusBar().showMessage(f"Imported {os.path.basename(file_name)}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to import:\n{str(e)}")

    def prev_molecule(self):
        if hasattr(self, 'sdf_molecules') and len(self.sdf_molecules) > 1:
            self.sdf_index = (self.sdf_index - 1) % len(self.sdf_molecules)
            mol = self.sdf_molecules[self.sdf_index]
            self.gallery_label.setText(f"Molecule {self.sdf_index + 1} / {len(self.sdf_molecules)}")
            try:
                smi_text = Chem.MolToSmiles(Chem.RemoveHs(mol))
                self.smiles_input.setText(smi_text)
            except: pass
            self.update_viewer(mol)

    def next_molecule(self):
        if hasattr(self, 'sdf_molecules') and len(self.sdf_molecules) > 1:
            self.sdf_index = (self.sdf_index + 1) % len(self.sdf_molecules)
            mol = self.sdf_molecules[self.sdf_index]
            self.gallery_label.setText(f"Molecule {self.sdf_index + 1} / {len(self.sdf_molecules)}")
            try:
                smi_text = Chem.MolToSmiles(Chem.RemoveHs(mol))
                self.smiles_input.setText(smi_text)
            except: pass
            self.update_viewer(mol)

    def export_molecule(self):
        if not hasattr(self, 'current_mol') or self.current_mol is None:
            QMessageBox.warning(self, "Export Error", "No molecule to export. Please load or optimize a molecule first.")
            return
            
        options = QFileDialog.Options()
        file_name, filter_used = QFileDialog.getSaveFileName(
            self, "Export Molecule", "", 
            "MDL MOL (*.mol);;SDF (*.sdf);;PDB (*.pdb);;SMILES (*.smi)", 
            options=options
        )
        if file_name:
            try:
                ext = os.path.splitext(file_name)[1].lower()
                if not ext:
                    if "MOL" in filter_used: ext = ".mol"
                    elif "SDF" in filter_used: ext = ".sdf"
                    elif "PDB" in filter_used: ext = ".pdb"
                    elif "SMILES" in filter_used: ext = ".smi"
                    file_name += ext

                if ext == '.mol':
                    Chem.MolToMolFile(self.current_mol, file_name)
                elif ext == '.sdf':
                    writer = Chem.SDWriter(file_name)
                    writer.write(self.current_mol)
                    writer.close()
                elif ext == '.pdb':
                    Chem.MolToPDBFile(self.current_mol, file_name)
                elif ext == '.smi':
                    with open(file_name, 'w') as f:
                        f.write(Chem.MolToSmiles(self.current_mol))
                else:
                    QMessageBox.warning(self, "Export Error", "Unsupported format for export.")
                    return
                    
                self.statusBar().showMessage(f"Exported to {os.path.basename(file_name)}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to export:\n{str(e)}")

    def pubchem_search(self):
        import urllib.request
        import urllib.parse
        import ssl
        name, ok = QInputDialog.getText(self, "PubChem Search", "Enter molecule name (e.g. Aspirin):")
        if ok and name.strip():
            try:
                self.statusBar().showMessage(f"Searching PubChem for '{name}'...")
                url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{urllib.parse.quote(name.strip())}/property/IsomericSMILES/TXT"
                req = urllib.request.Request(url, headers={'User-Agent': 'LeMoVi/1.0'})
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                with urllib.request.urlopen(req, context=ctx) as response:
                    smiles = response.read().decode('utf-8').strip()
                if smiles:
                    smiles = smiles.split('\n')[0].strip()
                    self.smiles_input.setText(smiles)
                    self.optimize_structure()
            except Exception as e:
                QMessageBox.warning(self, "PubChem Error", f"Could not find molecule '{name}'.\n(Error: {e})")
                self.statusBar().showMessage("PubChem Search failed.")

    def update_overlay_state(self, row):
        cb_widget = self.overlay_table.cellWidget(row, 1)
        if not cb_widget: return
        cb = cb_widget.findChild(QCheckBox)
        visible = cb.isChecked() if cb else True
        
        combo = self.overlay_table.cellWidget(row, 2)
        color_text = combo.currentText() if combo else "Default"
        
        color_map = {"Default": "", "Cyan": "cyan", "Magenta": "magenta", "Yellow": "yellow", "Green": "green", "Orange": "orange"}
        color_hex = color_map.get(color_text, "")
        
        js = f"updateOverlay({row}, {'true' if visible else 'false'}, '{color_hex}');"
        self.web_view.page().runJavaScript(js)

    def overlay_molecule(self):
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Overlay Molecule", "", 
            "Supported Formats (*.mol *.sdf *.pdb *.smi);;MDL MOL (*.mol);;SDF (*.sdf);;PDB (*.pdb);;SMILES (*.smi)", 
            options=options
        )
        if file_name:
            try:
                mol = None
                ext = os.path.splitext(file_name)[1].lower()
                if ext == '.mol':
                    mol = Chem.MolFromMolFile(file_name, removeHs=False)
                elif ext == '.sdf':
                    suppl = Chem.SDMolSupplier(file_name, removeHs=False)
                    for m in suppl:
                        if m is not None:
                            mol = m
                            break
                elif ext == '.pdb':
                    mol = Chem.MolFromPDBFile(file_name, removeHs=False)
                elif ext == '.smi':
                    with open(file_name, 'r') as f:
                        smi = f.readline().strip().split()[0]
                    mol = Chem.MolFromSmiles(smi)
                    if mol:
                        mol = Chem.AddHs(mol)
                        AllChem.EmbedMolecule(mol)
                    
                if mol is None:
                    QMessageBox.warning(self, "Import Error", "Could not read molecule from file.")
                    return
                
                self.add_overlay(mol, file_name)
                self.statusBar().showMessage(f"Overlayed {os.path.basename(file_name)}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to overlay:\n{str(e)}")

    def add_overlay(self, mol, file_name):
        try:
            from rdkit.Chem import Crippen
            AllChem.ComputeGasteigerCharges(mol)
            logp_contribs = Crippen.CrippenContribs(mol)
        except Exception as e:
            logp_contribs = [(0,0)] * mol.GetNumAtoms()

        props = []
        for i, atom in enumerate(mol.GetAtoms()):
            charge = 0.0
            logp = 0.0
            try:
                charge = float(atom.GetProp("_GasteigerCharge"))
                if math.isnan(charge) or math.isinf(charge): charge = 0.0
            except: pass
            try:
                logp = logp_contribs[i][0]
            except: pass
            props.append({"charge": charge, "logp": logp})

        colors = ["cyan", "magenta", "yellow", "green", "orange"]
        row = self.overlay_table.rowCount()
        default_color = colors[row % len(colors)]

        mol_block = Chem.MolToMolBlock(mol)
        js = f"addMoleculeOverlay({json.dumps(mol_block)}, {json.dumps(props)}, '{default_color}');"
        self.web_view.page().runJavaScript(js)
        
        self.overlay_table.insertRow(row)
        self.overlay_table.setItem(row, 0, QTableWidgetItem(os.path.basename(file_name)))
        
        cb = QCheckBox()
        cb.setChecked(True)
        cb.toggled.connect(lambda state, r=row: self.update_overlay_state(r))
        cb_widget = QWidget()
        cb_layout = QHBoxLayout(cb_widget)
        cb_layout.addWidget(cb)
        cb_layout.setAlignment(Qt.AlignCenter)
        cb_layout.setContentsMargins(0,0,0,0)
        self.overlay_table.setCellWidget(row, 1, cb_widget)
        
        combo = QComboBox()
        combo.addItems(["Default", "Cyan", "Magenta", "Yellow", "Green", "Orange"])
        idx = combo.findText(default_color.capitalize())
        if idx >= 0: combo.setCurrentIndex(idx)
        combo.currentTextChanged.connect(lambda text, r=row: self.update_overlay_state(r))
        self.overlay_table.setCellWidget(row, 2, combo)
        
        self.overlay_table.setVisible(True)

        import urllib.request

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MolViewer3D()
    window.show()
    sys.exit(app.exec_())

