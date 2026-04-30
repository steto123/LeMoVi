import os
import sys
import json
import math
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                             QMessageBox, QSplitter, QStackedWidget, QDialog)
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

    function loadMolecule(molBlock) {
        viewer.clear();
        selectedAtoms = [];
        document.getElementById('info').innerHTML = "Molecule loaded. Click atoms for measurements.";
        currentModel = viewer.addModel(molBlock, "mol");
        applyStyle("stick");
        viewer.zoomTo();
        
        // Robuster Klick-Handler für Atome via Viewer
        viewer.setClickable({}, true, function(atom, viewer, event, container) {
            if(atom) {
                handleAtomClick(atom);
            }
        });
        
        viewer.render();
    }

    function applyStyle(styleType) {
        if (!currentModel) return;
        var style = {};
        if (styleType === "stick") style = {stick: {radius: 0.15}, sphere: {scale: 0.25}};
        else if (styleType === "sphere") style = {sphere: {}};
        else if (styleType === "line") style = {line: {}};
        else if (styleType === "ballstick") style = {stick: {radius: 0.05}, sphere: {scale: 0.3}};
        
        viewer.setStyle({}, style);
        if (showLabels) updateLabels();
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


from PyQt5.QtWidgets import QComboBox, QCheckBox

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
            QMainWindow { background-color: #1e1e1e; }
            QLabel { color: #ffffff; font-family: 'Segoe UI'; }
            QLineEdit { background-color: #2d2d2d; color: white; border: 1px solid #444; padding: 6px; border-radius: 4px; }
            QPushButton { background-color: #333; color: white; border: none; padding: 8px 16px; border-radius: 4px; font-family: 'Segoe UI'; }
            QPushButton:hover { background-color: #444; }
            QComboBox { background-color: #333; color: white; border: 1px solid #444; padding: 5px; border-radius: 4px; }
            QComboBox QAbstractItemView { background-color: #333; color: white; selection-background-color: #0078D4; border: 1px solid #444; }
            QCheckBox { color: white; }
            #OptimizeBtn { background-color: #0078D4; font-weight: bold; }
            #OptimizeBtn:hover { background-color: #0086f0; }
            #ClearBtn { background-color: #c42b1c; }
            #ClearBtn:hover { background-color: #e81123; }
        """)

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
        
        self.label_cb = QCheckBox("Atom Labels")
        self.label_cb.toggled.connect(self.toggle_labels)
        ctrl_bar.addWidget(self.label_cb)
        
        ctrl_bar.addStretch()
        
        self.clear_meas_btn = QPushButton("Clear Measurements")
        self.clear_meas_btn.setObjectName("ClearBtn")
        self.clear_meas_btn.clicked.connect(self.clear_measurements)
        ctrl_bar.addWidget(self.clear_meas_btn)
        
        main_layout.addLayout(ctrl_bar)

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
        mol_block = Chem.MolToMolBlock(mol)
        js = f"loadMolecule({json.dumps(mol_block)});"
        self.web_view.page().runJavaScript(js)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MolViewer3D()
    window.show()
    sys.exit(app.exec_())

