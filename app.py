import os
import sys
import json
import math
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                             QMessageBox, QSplitter, QStackedWidget, QDialog,
                             QFileDialog, QAction, QMenuBar, QInputDialog,
                             QSplashScreen, QListWidget, QListWidgetItem,
                             QComboBox, QCheckBox, QColorDialog, QGroupBox, QFrame)
from PyQt5.QtCore import Qt, QUrl, QSettings
from PyQt5.QtGui import QFont, QIcon, QPixmap, QPainter, QColor

try:
    from PyQt5.QtWebEngineWidgets import QWebEngineView
    WEB_ENGINE_AVAILABLE = True
except ImportError:
    QWebEngineView = QWidget
    WEB_ENGINE_AVAILABLE = False

from rdkit import Chem
from rdkit.Chem import AllChem
from orca_ui import OrcaSetupDialog, OrcaJobManagerWidget

__version__ = "22.07.2026"

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
    #method-badge { position: absolute; top: 10px; right: 10px; color: #4fc3f7; background: rgba(0,0,0,0.75); padding: 6px 12px; border-radius: 5px; pointer-events: none; font-size: 13px; border: 1px solid #2b5b84; font-weight: bold; display: none;}
  </style>
</head>
<body>
  <div id="container"></div>
  <div id="info">Click atoms for measurements (2: Distance, 3: Angle, 4: Torsion)</div>
  <div id="method-badge"></div>
  <script>
    var viewer = $3Dmol.createViewer("container", {backgroundColor: "#1e1e1e"});
    if (viewer) {
        viewer.getBackgroundColor = function() {
            return (viewer.bgColor !== undefined) ? viewer.bgColor : "#1e1e1e";
        };
        viewer.png = function() {
            if (typeof viewer.pngURI === "function") {
                return viewer.pngURI();
            }
            var canvas = (typeof viewer.getCanvas === "function") ? viewer.getCanvas() : null;
            return canvas ? canvas.toDataURL("image/png") : "";
        };
    }
    var selectedAtoms = [];
    var currentModel = null;
    var showLabels = false;
    var orbitalShapes = [];

    function setMethodBadge(text) {
        var el = document.getElementById('method-badge');
        if (text && text.trim() !== "") {
            el.innerHTML = text;
            el.style.display = "block";
        } else {
            el.style.display = "none";
        }
    }

    var highlightSphere = null;
    function highlightAtom(atomIndex) {
        if (!currentModel) return;
        if (highlightSphere) {
            viewer.removeShape(highlightSphere);
            highlightSphere = null;
        }
        if (atomIndex === null || atomIndex === undefined || atomIndex < 0) {
            viewer.render();
            return;
        }
        var atoms = currentModel.selectedAtoms({index: atomIndex});
        if (atoms.length > 0) {
            var atom = atoms[0];
            highlightSphere = viewer.addSphere({
                center: {x: atom.x, y: atom.y, z: atom.z},
                radius: 0.45,
                color: '#ff3333',
                opacity: 0.7
            });
            viewer.render();
        }
    }

    var currentSurface = null;
    var currentStyleType = "stick";
    var overlayStates = [];

    function loadMolecule(molBlock, props) {
        viewer.clear();
        overlayStates = [];
        selectedAtoms = [];
        highlightSphere = null;
        symmetryShapes = {};
        document.getElementById('info').innerHTML = "Molecule loaded. Click atoms for measurements.";
        currentModel = viewer.addModel(molBlock, "mol");
        
        if (props) {
            var atoms = currentModel.selectedAtoms({});
            for(var i=0; i<atoms.length; i++) {
                if (props[i]) {
                    atoms[i].charge = props[i].charge;
                    atoms[i].logp = props[i].logp;
                    atoms[i].mr = props[i].mr;
                    atoms[i].hbond = props[i].hbond;
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
                    atoms[i].mr = props[i].mr;
                    atoms[i].hbond = props[i].hbond;
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
        } else if (surfaceType === "Molecular Surface (Connolly)") {
            viewer.addSurface($3Dmol.SurfaceType.MS, {opacity: 0.85, color: '#e6e6e6'});
        } else if (surfaceType === "Electrostatic Potential") {
            viewer.addSurface($3Dmol.SurfaceType.MS, {
                opacity: 0.85,
                map: {prop: 'charge', scheme: new $3Dmol.Gradient.RWB(-0.5, 0.5)}
            });
        } else if (surfaceType === "Hydrophobicity (LogP)") {
            viewer.addSurface($3Dmol.SurfaceType.MS, {
                opacity: 0.85,
                map: {prop: 'logp', scheme: new $3Dmol.Gradient.ROYGB(-0.5, 0.5)}
            });
        } else if (surfaceType === "Polarizability (MR)") {
            viewer.addSurface($3Dmol.SurfaceType.MS, {
                opacity: 0.85,
                map: {prop: 'mr', scheme: new $3Dmol.Gradient.ROYGB(0, 2.5)}
            });
        } else if (surfaceType === "Hydrogen Bonding") {
            viewer.addSurface($3Dmol.SurfaceType.MS, {
                opacity: 0.85,
                map: {prop: 'hbond', scheme: new $3Dmol.Gradient.RWB(-1, 1)}
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
        
        // Notify Python about the clicked atom index
        document.title = "CLICKED_ATOM_" + atom.index;
        setTimeout(function() {
            document.title = "LeMoVi Viewer";
        }, 50);
        
        // Highlighting des gewählten Atoms (explizite Koordinaten)
        viewer.addSphere({center: {x: atom.x, y: atom.y, z: atom.z}, radius: 0.35, color: 'yellow', opacity: 0.8});
        selectedAtoms.push(atom);
        
        var info = document.getElementById('info');
        var atomName = atom.elem + (atom.serial !== undefined ? atom.serial : selectedAtoms.length);

        if (selectedAtoms.length === 1) {
            info.innerHTML = "Selection 1: " + atomName;
        } else if (selectedAtoms.length === 2) {
            var d = distance(selectedAtoms[0], selectedAtoms[1]).toFixed(3);
            addMeasurementLabel(midpoint(selectedAtoms[0], selectedAtoms[1]), d + " Å");
            drawMeasurementLine(selectedAtoms[0], selectedAtoms[1]);
            info.innerHTML = "Distance: " + d + " Å";
        } else if (selectedAtoms.length === 3) {
            var a = angle(selectedAtoms[0], selectedAtoms[1], selectedAtoms[2]).toFixed(2);
            // Label leicht versetzt vom zentralen Atom, damit es nicht direkt im Atom verschwindet
            addMeasurementLabel({x: selectedAtoms[1].x, y: selectedAtoms[1].y + 0.6, z: selectedAtoms[1].z}, a + "°");
            drawMeasurementLine(selectedAtoms[1], selectedAtoms[2]);
            info.innerHTML = "Angle: " + a + "°";
        } else if (selectedAtoms.length === 4) {
            var t = torsion(selectedAtoms[0], selectedAtoms[1], selectedAtoms[2], selectedAtoms[3]).toFixed(2);
            addMeasurementLabel(midpoint(selectedAtoms[1], selectedAtoms[2]), t + "°");
            drawMeasurementLine(selectedAtoms[2], selectedAtoms[3]);
            info.innerHTML = "Torsion: " + t + "°";
            selectedAtoms = []; // Reset nach Torsion
        }
        viewer.render();
    }

    function drawMeasurementLine(a, b) {
        // Zeichnet einen gut sichtbaren Zylinder zwischen den Atomen
        viewer.addCylinder({
            start: {x: a.x, y: a.y, z: a.z},
            end: {x: b.x, y: b.y, z: b.z},
            radius: 0.08,
            color: '#FF00FF', // Magenta als starke Kontrastfarbe
            dashed: true
        });
    }

    function addMeasurementLabel(pos, text) {
        viewer.addLabel(text, {
            position: {x: pos.x, y: pos.y, z: pos.z}, 
            backgroundColor: '#0078D4', 
            fontColor: 'white', 
            fontSize: 14, 
            backgroundOpacity: 0.9,
            borderThickness: 1,
            borderColor: 'white'
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

    var symmetryShapes = {};
    
    function drawSymmetryAxis(id, x1, y1, z1, x2, y2, z2, color, label) {
        clearSymmetryElement(id);
        
        var shapes = [];
        var cyl = viewer.addCylinder({
            start: {x: x1, y: y1, z: z1},
            end: {x: x2, y: y2, z: z2},
            radius: 0.08,
            color: color || 'red',
            fromCap: 1,
            toCap: 1
        });
        shapes.push({type: 'shape', obj: cyl});
        
        if (label) {
            var lbl = viewer.addLabel(label, {
                position: {x: x2, y: y2, z: z2},
                backgroundColor: color || 'red',
                fontColor: 'white',
                backgroundOpacity: 0.8,
                fontSize: 12
            });
            shapes.push({type: 'label', obj: lbl});
        }
        
        symmetryShapes[id] = shapes;
        viewer.render();
    }
    
    function drawSymmetryPlane(id, nx, ny, nz, color, radius, cx, cy, cz, label, showBorder, opacity) {
        clearSymmetryElement(id);
        
        var shapes = [];
        var x = cx || 0;
        var y = cy || 0;
        var z = cz || 0;
        var r = radius || 3.5;
        var planeColor = color || '#00e5ff';
        var op = (typeof opacity === 'number') ? opacity : 0.35;
        if (showBorder === undefined || showBorder === null) {
            showBorder = true;
        }
        
        // Normalize normal vector
        var norm = Math.sqrt(nx*nx + ny*ny + nz*nz);
        if (norm === 0) { nx = 0; ny = 0; nz = 1; norm = 1; }
        nx /= norm; ny /= norm; nz /= norm;

        // Construct orthonormal vectors u and v perpendicular to n in the plane
        var ax = (Math.abs(nx) > 0.9) ? 0 : 1;
        var ay = (Math.abs(nx) > 0.9) ? 1 : 0;
        var az = 0;

        var ux = ny * az - nz * ay;
        var uy = nz * ax - nx * az;
        var uz = nx * ay - ny * ax;
        var u_len = Math.sqrt(ux*ux + uy*uy + uz*uz);
        ux /= u_len; uy /= u_len; uz /= u_len;

        var vx = ny * uz - nz * uy;
        var vy = nz * ux - nx * uz;
        var vz = nx * uy - ny * ux;

        var thickness = 0.025;
        var half_t = thickness / 2.0;
        var start_pos = { x: x - nx * half_t, y: y - ny * half_t, z: z - nz * half_t };
        var end_pos = { x: x + nx * half_t, y: y + ny * half_t, z: z + nz * half_t };

        // Translucent plane disc
        var disk = viewer.addCylinder({
            start: start_pos,
            end: end_pos,
            radius: r,
            color: planeColor,
            opacity: op,
            fromCap: 1,
            toCap: 1
        });
        shapes.push({type: 'shape', obj: disk});

        // Crisp border ring along circumference
        if (showBorder) {
            var segs = 60;
            for (var i = 0; i < segs; i++) {
                var t1 = (2.0 * Math.PI * i) / segs;
                var t2 = (2.0 * Math.PI * (i + 1)) / segs;
                var p1 = {
                    x: x + r * (Math.cos(t1) * ux + Math.sin(t1) * vx),
                    y: y + r * (Math.cos(t1) * uy + Math.sin(t1) * vy),
                    z: z + r * (Math.cos(t1) * uz + Math.sin(t1) * vz)
                };
                var p2 = {
                    x: x + r * (Math.cos(t2) * ux + Math.sin(t2) * vx),
                    y: y + r * (Math.cos(t2) * uy + Math.sin(t2) * vy),
                    z: z + r * (Math.cos(t2) * uz + Math.sin(t2) * vz)
                };
                var rimSeg = viewer.addCylinder({
                    start: p1,
                    end: p2,
                    radius: 0.025,
                    color: planeColor,
                    opacity: 0.85,
                    fromCap: 1,
                    toCap: 1
                });
                shapes.push({type: 'shape', obj: rimSeg});
            }
        }

        // Label on the perimeter in the plane with contrast font color
        if (label) {
            var fontColor = '#0f172a';
            if (planeColor.startsWith('#') && planeColor.length === 7) {
                var red = parseInt(planeColor.substr(1, 2), 16);
                var green = parseInt(planeColor.substr(3, 2), 16);
                var blue = parseInt(planeColor.substr(5, 2), 16);
                var lum = (red * 0.299 + green * 0.587 + blue * 0.114);
                if (lum < 125) { fontColor = '#ffffff'; }
            }
            var lbl_pos = {
                x: x + ux * (r + 0.35),
                y: y + uy * (r + 0.35),
                z: z + uz * (r + 0.35)
            };
            var lbl = viewer.addLabel(label, {
                position: lbl_pos,
                backgroundColor: planeColor,
                fontColor: fontColor,
                backgroundOpacity: 0.9,
                fontSize: 13,
                inFront: true
            });
            shapes.push({type: 'label', obj: lbl});
        }

        symmetryShapes[id] = shapes;
        viewer.render();
    }
    
    function drawInversionCenter(id, x, y, z, color) {
        clearSymmetryElement(id);
        
        var sphere = viewer.addSphere({
            center: {x: x, y: y, z: z},
            radius: 0.25,
            color: color || 'yellow',
            opacity: 0.8
        });
        
        symmetryShapes[id] = [{type: 'shape', obj: sphere}];
        viewer.render();
    }
    
    function clearSymmetryElement(id) {
        if (symmetryShapes[id]) {
            for (var i = 0; i < symmetryShapes[id].length; i++) {
                var item = symmetryShapes[id][i];
                try {
                    if (item.type === 'label') {
                        viewer.removeLabel(item.obj);
                    } else {
                        viewer.removeShape(item.obj);
                    }
                } catch(e) {
                    console.log("Error removing symmetry element:", e);
                }
            }
            delete symmetryShapes[id];
            viewer.render();
        }
    }
    
    function clearAllSymmetryElements() {
        for (var id in symmetryShapes) {
            clearSymmetryElement(id);
        }
        symmetryShapes = {};
        viewer.render();
    }

    function loadOrbital(cubeData, isoval) {
        for (var i = 0; i < orbitalShapes.length; i++) {
            viewer.removeShape(orbitalShapes[i]);
        }
        orbitalShapes = [];
        viewer.removeAllSurfaces();
        
        var volData = new $3Dmol.VolumeData(cubeData, "cube");
        var shape1 = viewer.addIsosurface(volData, {
            isoval: isoval,
            color: "#00c853", // green for positive phase
            opacity: 0.75
        });
        var shape2 = viewer.addIsosurface(volData, {
            isoval: -isoval,
            color: "#d50000", // red for negative phase
            opacity: 0.75
        });
        if (shape1) orbitalShapes.push(shape1);
        if (shape2) orbitalShapes.push(shape2);
        viewer.render();
    }
    
    function loadDensity(cubeData, isoval) {
        for (var i = 0; i < orbitalShapes.length; i++) {
            viewer.removeShape(orbitalShapes[i]);
        }
        orbitalShapes = [];
        viewer.removeAllSurfaces();
        
        var volData = new $3Dmol.VolumeData(cubeData, "cube");
        var shape = viewer.addIsosurface(volData, {
            isoval: isoval,
            color: "#00b0ff", // cyan/light blue
            opacity: 0.5
        });
        if (shape) orbitalShapes.push(shape);
        viewer.render();
    }

    function clearSurfaces() {
        for (var i = 0; i < orbitalShapes.length; i++) {
            viewer.removeShape(orbitalShapes[i]);
        }
        orbitalShapes = [];
        viewer.removeAllSurfaces();
        viewer.render();
    }
  </script>
</body>
</html>
"""


from PyQt5.QtWidgets import QComboBox, QCheckBox, QTableWidget, QTableWidgetItem, QHeaderView

class DragDropWebView(QWebEngineView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_win = parent
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls:
                file_path = urls[0].toLocalFile()
                if file_path:
                    # Let parent load the file
                    self.parent_win.load_molecule_from_file(file_path)
                    event.acceptProposedAction()
                    return
        super().dropEvent(event)

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
        self.setWindowTitle(f"LeMoVi - Lehnin Molecule Visualizer (v{__version__})")
        self.resize(1250, 850)
        self.setWindowIcon(QIcon(os.path.join(os.path.dirname(__file__), "icon.png")))
        self.symmetry_dialog = None
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
        self.surface_combo.addItems([
            "None", "Van der Waals", "Solvent Accessible", 
            "Molecular Surface (Connolly)", "Electrostatic Potential", 
            "Hydrophobicity (LogP)", "Polarizability (MR)", "Hydrogen Bonding"
        ])
        self.surface_combo.currentTextChanged.connect(self.change_surface)
        ctrl_bar.addWidget(self.surface_combo)
        
        self.label_cb = QCheckBox("Atom Labels")
        self.label_cb.toggled.connect(self.toggle_labels)
        ctrl_bar.addWidget(self.label_cb)
        
        ctrl_bar.addStretch()
        
        self.center_btn = QPushButton("🎯 Center View")
        self.center_btn.clicked.connect(self.center_view)
        ctrl_bar.addWidget(self.center_btn)
        
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

        # Main View (3D) & ORCA Job Manager (Splitter-based)
        self.splitter = QSplitter(Qt.Vertical)
        
        self.web_view = DragDropWebView(self)
        self.web_view.titleChanged.connect(self.on_viewer_title_changed)
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.web_view.setHtml(HTML_3DMOL, QUrl.fromLocalFile(base_dir + "/"))
        self.splitter.addWidget(self.web_view)
        
        self.orca_job_widget = OrcaJobManagerWidget(base_dir, self)
        self.orca_job_widget.setVisible(False)
        self.splitter.addWidget(self.orca_job_widget)
        
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 0)
        self.splitter.setSizes([750, 180])
        
        main_layout.addWidget(self.splitter)
        
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

    def center_view(self):
        js = "viewer.zoomTo();"
        self.web_view.page().runJavaScript(js)

    def on_viewer_title_changed(self, title):
        if title.startswith("CLICKED_ATOM_"):
            try:
                atom_idx = int(title.split("_")[-1])
                if hasattr(self, 'orca_job_widget') and hasattr(self.orca_job_widget, 'results_dialog'):
                    dlg = self.orca_job_widget.results_dialog
                    if dlg and dlg.isVisible():
                        dlg.highlight_atom_from_viewer(atom_idx)
            except Exception as e:
                print("Error propagating clicked atom:", e)

    def set_method_badge(self, method_text):
        """Updates top-right 3D viewer method/basis badge."""
        if hasattr(self, 'web_view') and self.web_view:
            js = f"setMethodBadge({json.dumps(method_text)});"
            self.web_view.page().runJavaScript(js)

    def optimize_structure(self):
        smiles = self.smiles_input.text().strip()
        if not smiles: return
        method = self.method_combo.currentText()

        try:
            self.statusBar().showMessage(f"Processing SMILES for {method}...")
            
            # Check if we can reuse the coordinates of the currently loaded molecule
            use_existing_coords = False
            mol = None
            if hasattr(self, 'current_mol') and self.current_mol is not None and self.current_mol.GetNumConformers() > 0:
                try:
                    current_smi = Chem.MolToSmiles(Chem.RemoveHs(self.current_mol))
                    # Standardize SMILES for comparison
                    input_mol = Chem.MolFromSmiles(smiles)
                    if input_mol:
                        input_smi = Chem.MolToSmiles(Chem.RemoveHs(input_mol))
                        if Chem.CanonSmiles(current_smi) == Chem.CanonSmiles(input_smi):
                            # Yes! The structure matches. We can use the existing molecule with its conformer.
                            mol = Chem.Mol(self.current_mol)
                            use_existing_coords = True
                except Exception as e:
                    print("Could not compare SMILES for coordinate reuse:", e)

            if not use_existing_coords:
                mol = Chem.MolFromSmiles(smiles)
                if not mol: raise ValueError("Invalid SMILES code")
                mol = Chem.AddHs(mol)
                params = AllChem.ETKDGv3()
                params.randomSeed = 42
                if AllChem.EmbedMolecule(mol, params) == -1:
                    AllChem.EmbedMolecule(mol, randomSeed=42)

            if "MMFF94" in method:
                if use_existing_coords:
                    self.statusBar().showMessage("Optimizing existing 3D coordinates (MMFF94)...")
                else:
                    self.statusBar().showMessage("Generating 3D coordinates & Optimization (MMFF94)...")
                
                status = 1
                attempts = 0
                max_attempts = 5
                used_method = "MMFF94"
                
                # Strategy 1: Multiple passes with maxIters
                while status == 1 and attempts < max_attempts:
                    status = AllChem.MMFFOptimizeMolecule(mol, maxIters=500)
                    attempts += 1
                
                if status == -1:
                    # Strategy 2: UFF fallback
                    self.statusBar().showMessage("MMFF94 parameters missing. Trying UFF fallback...")
                    status = 1
                    attempts = 0
                    used_method = "UFF"
                    while status == 1 and attempts < max_attempts:
                        status = AllChem.UFFOptimizeMolecule(mol, maxIters=500)
                        attempts += 1
                    
                    if status == 0:
                        msg = f"Optimization (UFF fallback) completed successfully (converged in {attempts} pass(es))."
                    elif status == 1:
                        msg = "Optimization (UFF fallback) stopped: Did not converge after maximum iterations."
                    else:
                        msg = "Optimization failed: Missing parameters for both MMFF94 and UFF."
                else:
                    if status == 0:
                        msg = f"Optimization (MMFF94) completed successfully (converged in {attempts} pass(es))."
                    else:
                        msg = "Optimization (MMFF94) stopped: Did not converge after maximum iterations."
                
                self.update_viewer(mol)
                self.set_method_badge(f"Method: {used_method} (Geom Opt)")
                self.statusBar().showMessage(msg)
            else:
                self.run_xtb(mol)
            
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))
            self.statusBar().showMessage("Error during optimization.")

    def run_xtb(self, mol):
        import subprocess
        import tempfile
        import shutil
        self.statusBar().showMessage("Running xTB Optimization... (this may take a while)")
        
        # Check for xtb
        xtb_exe = os.path.join(os.path.dirname(os.path.abspath(__file__)), "xtb", "xtb.exe")
        if not os.path.exists(xtb_exe):
            QMessageBox.critical(self, "xTB not found", f"Please download xTB and extract it to:\n{xtb_exe}")
            self.statusBar().showMessage("xTB Optimization aborted.")
            return

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                current_input = "input.xyz"
                input_xyz = os.path.join(tmpdir, current_input)
                Chem.MolToXYZFile(mol, input_xyz)
                
                max_attempts = 3
                attempt = 0
                success = False
                
                while attempt < max_attempts and not success:
                    attempt += 1
                    self.statusBar().showMessage(f"Running xTB Optimization... (Attempt {attempt}/{max_attempts})")
                    
                    cmd = [xtb_exe, current_input, "--opt"]
                    try:
                        subprocess.run(cmd, cwd=tmpdir, check=True, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
                        success = True
                    except subprocess.CalledProcessError as e:
                        xtbopt_xyz = os.path.join(tmpdir, "xtbopt.xyz")
                        if os.path.exists(xtbopt_xyz):
                            current_input = f"input_retry_{attempt}.xyz"
                            shutil.copy(xtbopt_xyz, os.path.join(tmpdir, current_input))
                            os.remove(xtbopt_xyz)
                        else:
                            break
                
                if not success:
                    self.statusBar().showMessage(f"xTB failed to converge after {attempt} attempt(s).")
                
                final_xyz = os.path.join(tmpdir, "xtbopt.xyz")
                if not os.path.exists(final_xyz):
                    final_xyz = os.path.join(tmpdir, current_input)
                
                if not os.path.exists(final_xyz):
                    raise ValueError("No structure file found.")
                    
                with open(final_xyz, "r") as f:
                    lines = f.readlines()
                
                if len(lines) > 2:
                    conf = mol.GetConformer()
                    for i, line in enumerate(lines[2:]):
                        parts = line.split()
                        if len(parts) >= 4:
                            x, y, z = map(float, parts[1:4])
                            conf.SetAtomPosition(i, (x, y, z))
                            
                self.update_viewer(mol)
                self.set_method_badge("Method: GFN2-xTB (Geom Opt)")
                
                if success:
                    self.statusBar().showMessage(f"Optimization (xTB) completed successfully (in {attempt} pass(es)).")
                else:
                    self.statusBar().showMessage("Optimization (xTB) incomplete: Displaying best intermediate structure.")
                    QMessageBox.warning(self, "xTB Warning", f"xTB convergence failed after {attempt} attempts.\nThe displayed structure is incompletely optimized.")

                    self.statusBar().showMessage("Optimization (xTB) incomplete: Displaying best intermediate structure.")
                    QMessageBox.warning(self, "xTB Warning", f"xTB Konvergenz fehlgeschlagen nach {attempt} Versuchen.\nDie angezeigte Struktur ist unvollständig optimiert.")
                    
        except Exception as e:
            QMessageBox.critical(self, "xTB Error", f"xTB ist fehlgeschlagen:\n{str(e)}")
            self.statusBar().showMessage("xTB Error.")

    def update_viewer(self, mol):
        self.current_mol = mol
        self.overlay_table.setRowCount(0)
        self.overlay_table.setVisible(False)
        if hasattr(self, 'symmetry_dialog') and self.symmetry_dialog is not None and self.symmetry_dialog.isVisible():
            try:
                self.symmetry_dialog.update_molecule(mol)
            except Exception as e:
                print("Error updating symmetry dialog:", e)
        try:
            from rdkit.Chem import Crippen
            AllChem.ComputeGasteigerCharges(mol)
            logp_contribs = Crippen.CrippenContribs(mol)
        except Exception as e:
            print("Warning: Could not compute properties:", e)
            logp_contribs = [(0,0)] * mol.GetNumAtoms()

        donor_smarts = Chem.MolFromSmarts('[$([N,O,S;!H0])]')
        acceptor_smarts = Chem.MolFromSmarts('[$([O,N;!v4])]')
        donors = set(sum(mol.GetSubstructMatches(donor_smarts), ())) if donor_smarts else set()
        acceptors = set(sum(mol.GetSubstructMatches(acceptor_smarts), ())) if acceptor_smarts else set()

        props = []
        for i, atom in enumerate(mol.GetAtoms()):
            charge = 0.0
            logp = 0.0
            mr = 0.0
            hbond = 0
            if i in donors: hbond = 1
            elif i in acceptors: hbond = -1

            try:
                charge = float(atom.GetProp("_GasteigerCharge"))
                if math.isnan(charge) or math.isinf(charge): charge = 0.0
            except:
                pass
            try:
                logp = logp_contribs[i][0]
                mr = logp_contribs[i][1]
            except:
                pass
            props.append({"charge": charge, "logp": logp, "mr": mr, "hbond": hbond})

        mol_block = Chem.MolToMolBlock(mol)
        js = f"loadMolecule({json.dumps(mol_block)}, {json.dumps(props)});"
        self.web_view.page().runJavaScript(js)
        self.change_surface(self.surface_combo.currentText())

    def create_menu(self):
        menubar = self.menuBar()
        menubar.setStyleSheet("background-color: #2d2d2d; color: white;")
        self.file_menu = menubar.addMenu("File")

        pubchem_action = QAction("PubChem Search...", self)
        pubchem_action.triggered.connect(self.pubchem_search)
        self.file_menu.addAction(pubchem_action)

        import_action = QAction("Import Molecule...", self)
        import_action.triggered.connect(self.import_molecule)
        self.file_menu.addAction(import_action)

        self.recent_menu = self.file_menu.addMenu("Zuletzt verwendet")
        self.rebuild_recent_menu()

        overlay_action = QAction("Overlay Molecule...", self)
        overlay_action.triggered.connect(self.overlay_molecule)
        self.file_menu.addAction(overlay_action)

        export_action = QAction("Export Molecule...", self)
        export_action.triggered.connect(self.export_molecule)
        self.file_menu.addAction(export_action)

        export_img_action = QAction("Als Bild speichern...", self)
        export_img_action.triggered.connect(self.export_as_image)
        self.file_menu.addAction(export_img_action)

        export_gif_action = QAction("Als rotierendes GIF speichern...", self)
        export_gif_action.triggered.connect(self.start_spinning_export)
        self.file_menu.addAction(export_gif_action)

        # Symmetry Menu
        symmetry_menu = menubar.addMenu("Symmetry")
        analyze_sym_action = QAction("Analyze Molecule Symmetry...", self)
        analyze_sym_action.triggered.connect(self.open_symmetry_dialog)
        symmetry_menu.addAction(analyze_sym_action)

        clear_sym_action = QAction("Clear Symmetry Elements", self)
        clear_sym_action.triggered.connect(self.clear_symmetry_visualizations)
        symmetry_menu.addAction(clear_sym_action)

        orca_menu = menubar.addMenu("ORCA 6")

        setup_action = QAction("Setup Calculation...", self)
        setup_action.triggered.connect(self.open_orca_setup)
        orca_menu.addAction(setup_action)

        queue_action = QAction("Toggle Job Manager", self)
        queue_action.triggered.connect(self.toggle_orca_queue)
        orca_menu.addAction(queue_action)
    def open_orca_setup(self):
        if not hasattr(self, 'current_mol') or self.current_mol is None:
            QMessageBox.warning(self, "Warning", "No molecule loaded. Please load or optimize a structure first.")
            return

        xyz_block = ""
        try:
            conf = self.current_mol.GetConformer()
            for atom in self.current_mol.GetAtoms():
                pos = conf.GetAtomPosition(atom.GetIdx())
                xyz_block += f"{atom.GetSymbol()} {pos.x:.6f} {pos.y:.6f} {pos.z:.6f}\n"
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to get coordinates from molecule:\n{str(e)}")
            return

        default_job_name = "orca_calc"
        if self.current_mol.HasProp("_Name"):
            mol_name = self.current_mol.GetProp("_Name").strip()
            if mol_name:
                import re
                clean_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', mol_name)
                clean_name = re.sub(r'_+', '_', clean_name).strip('_')
                if clean_name:
                    default_job_name = clean_name

        dialog = OrcaSetupDialog(self, xyz_block, self.orca_job_widget.job_manager, default_name=default_job_name)
        if dialog.exec_() == QDialog.Accepted:
            self.orca_job_widget.setVisible(True)
            self.orca_job_widget.refresh_queue()

    def toggle_orca_queue(self):
        self.orca_job_widget.setVisible(not self.orca_job_widget.isVisible())

    def clear_symmetry_visualizations(self):
        self.web_view.page().runJavaScript("clearAllSymmetryElements();")
        if hasattr(self, 'symmetry_dialog') and self.symmetry_dialog is not None:
            self.symmetry_dialog.deselect_all()

    def open_symmetry_dialog(self):
        if not hasattr(self, 'current_mol') or self.current_mol is None:
            QMessageBox.warning(self, "Warning", "No molecule loaded. Please load or optimize a structure first.")
            return
        
        if hasattr(self, 'symmetry_dialog') and self.symmetry_dialog is not None:
            try:
                if self.symmetry_dialog.isVisible():
                    if getattr(self.symmetry_dialog, 'mol', None) != self.current_mol:
                        self.symmetry_dialog.update_molecule(self.current_mol)
                    self.symmetry_dialog.raise_()
                    self.symmetry_dialog.activateWindow()
                    return
                else:
                    self.symmetry_dialog.update_molecule(self.current_mol)
                    self.symmetry_dialog.show()
                    self.symmetry_dialog.raise_()
                    self.symmetry_dialog.activateWindow()
                    return
            except Exception:
                pass

        self.symmetry_dialog = SymmetryDialog(self, self.current_mol)
        self.symmetry_dialog.show()
        self.symmetry_dialog.raise_()
        self.symmetry_dialog.activateWindow()

    def import_molecule(self):
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Import Molecule", "", 
            "Supported Formats (*.mol *.sdf *.pdb *.smi *.xyz *.com);;MDL MOL (*.mol);;SDF (*.sdf);;PDB (*.pdb);;SMILES (*.smi);;XYZ (*.xyz);;Gaussian Input (*.com)", 
            options=options
        )
        if file_name:
            self.load_molecule_from_file(file_name)

    def load_molecule_from_file(self, file_name):
        if not file_name or not os.path.exists(file_name):
            return
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
            elif ext == '.xyz':
                with open(file_name, 'r') as f:
                    xyz_content = f.read()
                mol = Chem.MolFromXYZBlock(xyz_content)
                if mol:
                    from rdkit.Chem import rdDetermineBonds
                    try:
                        rdDetermineBonds.DetermineBonds(mol, charge=0)
                    except Exception:
                        pass
            elif ext == '.com':
                with open(file_name, 'r') as f:
                    content = f.read()
                import re
                from rdkit.Chem import rdDetermineBonds
                blocks = re.split(r'(?i)--link1--', content)
                pt = Chem.GetPeriodicTable()
                self.sdf_molecules = []
                for block in blocks:
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
                                try: charge = int(parts[0])
                                except ValueError: pass
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
                    if raw_mol:
                        try:
                            rdDetermineBonds.DetermineBonds(raw_mol, charge=charge)
                        except Exception:
                            pass
                        raw_mol.SetProp("_Name", title)
                        self.sdf_molecules.append(raw_mol)
                if self.sdf_molecules:
                    mol = self.sdf_molecules[0]
                
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
            self.update_recent_files(file_name)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to import:\n{str(e)}")

    def update_recent_files(self, file_path):
        if not file_path or not os.path.exists(file_path):
            return
        settings = QSettings("LeMoVi", "Visualizer")
        files = settings.value("recentFiles", [])
        if not isinstance(files, list):
            files = []
        
        if file_path in files:
            files.remove(file_path)
        files.insert(0, file_path)
        files = files[:10]
        settings.setValue("recentFiles", files)
        self.rebuild_recent_menu()

    def rebuild_recent_menu(self):
        self.recent_menu.clear()
        settings = QSettings("LeMoVi", "Visualizer")
        files = settings.value("recentFiles", [])
        if not isinstance(files, list):
            files = []
            
        existing_files = [f for f in files if os.path.exists(f)]
        if len(existing_files) != len(files):
            settings.setValue("recentFiles", existing_files)
            files = existing_files
            
        if not files:
            no_recent_action = QAction("Keine kürzlichen Dateien", self)
            no_recent_action.setEnabled(False)
            self.recent_menu.addAction(no_recent_action)
            return
            
        for file_path in files:
            action = QAction(os.path.basename(file_path), self)
            action.setStatusTip(file_path)
            action.triggered.connect(lambda checked, path=file_path: self.load_molecule_from_file(path))
            self.recent_menu.addAction(action)
            
        self.recent_menu.addSeparator()
        clear_action = QAction("Historie löschen", self)
        clear_action.triggered.connect(self.clear_recent_files)
        self.recent_menu.addAction(clear_action)

    def clear_recent_files(self):
        settings = QSettings("LeMoVi", "Visualizer")
        settings.setValue("recentFiles", [])
        self.rebuild_recent_menu()

    def export_as_image(self):
        if not hasattr(self, 'current_mol') or self.current_mol is None:
            QMessageBox.warning(self, "Export Error", "No molecule loaded.")
            return
            
        options = QFileDialog.Options()
        file_path, selected_filter = QFileDialog.getSaveFileName(
            self, "Save as Image", "", 
            "PNG Image (*.png);;JPEG Image (*.jpg)", 
            options=options
        )
        if not file_path:
            return
            
        transparent = False
        ext = os.path.splitext(file_path)[1].lower()
        if not ext:
            if "PNG" in selected_filter:
                ext = ".png"
            else:
                ext = ".jpg"
            file_path += ext
            
        if ext == ".png":
            reply = QMessageBox.question(
                self, "Background", 
                "Do you want a transparent background?", 
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            transparent = (reply == QMessageBox.Yes)
            
        js = """
        (function() {
            try {
                var transparent = %s;
                var origBg = (typeof viewer.getBackgroundColor === 'function') ? 
                             viewer.getBackgroundColor() : 
                             (viewer.bgColor !== undefined ? viewer.bgColor : '#1e1e1e');
                if (transparent) {
                    viewer.setBackgroundColor(0x000000, 0);
                    viewer.render();
                }
                var data = "";
                if (typeof viewer.pngURI === 'function') {
                    data = viewer.pngURI();
                } else if (typeof viewer.png === 'function') {
                    data = viewer.png();
                } else if (typeof viewer.getCanvas === 'function') {
                    var canvas = viewer.getCanvas();
                    data = canvas ? canvas.toDataURL("image/png") : "";
                }
                if (transparent) {
                    viewer.setBackgroundColor(origBg, 1);
                    viewer.render();
                }
                return data;
            } catch(e) {
                console.error("Export image error:", e);
                return "";
            }
        })()
        """ % ("true" if transparent else "false")
        
        def on_image_captured(png_data_url):
            if not png_data_url:
                QMessageBox.critical(self, "Export Error", "Failed to capture image from viewer.")
                return
            if png_data_url.startswith("data:image/"):
                base64_data = png_data_url.split(",")[1]
                try:
                    import base64
                    from PyQt5.QtGui import QImage
                    image_data = base64.b64decode(base64_data)
                    image = QImage.fromData(image_data)
                    if image.isNull():
                        QMessageBox.critical(self, "Export Error", "Failed to decode captured image.")
                        return
                    if ext in [".jpg", ".jpeg"]:
                        if image.hasAlphaChannel():
                            from PyQt5.QtGui import QPainter, QColor
                            rgb_image = QImage(image.size(), QImage.Format_RGB32)
                            rgb_image.fill(QColor("#1e1e1e"))
                            painter = QPainter(rgb_image)
                            painter.drawImage(0, 0, image)
                            painter.end()
                            rgb_image.save(file_path, "JPEG", 95)
                        else:
                            image.save(file_path, "JPEG", 95)
                    else:
                        image.save(file_path, "PNG")
                    self.statusBar().showMessage(f"Image saved to {os.path.basename(file_path)}")
                except Exception as e:
                    QMessageBox.critical(self, "Export Error", f"Failed to save image:\n{e}")
            else:
                QMessageBox.critical(self, "Export Error", "Viewer returned invalid image format.")
                    
        self.web_view.page().runJavaScript(js, on_image_captured)

    def start_spinning_export(self):
        if not hasattr(self, 'current_mol') or self.current_mol is None:
            QMessageBox.warning(self, "Export Error", "No molecule loaded.")
            return

        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Als rotierendes GIF speichern", "", 
            "GIF Image (*.gif)", 
            options=options
        )
        if not file_path:
            return

        if not file_path.lower().endswith(".gif"):
            file_path += ".gif"

        self.export_gif_path = file_path
        self.export_frames = []
        self.export_step = 0
        self.export_total_steps = 36
        
        from PyQt5.QtWidgets import QProgressDialog
        self.export_progress = QProgressDialog("Exportiere rotierendes GIF...", "Abbrechen", 0, self.export_total_steps, self)
        self.export_progress.setWindowModality(Qt.WindowModal)
        self.export_progress.setAutoClose(True)
        self.export_progress.show()
        
        self.capture_next_frame()

    def capture_next_frame(self):
        if self.export_progress.wasCanceled():
            self.export_frames = []
            return
            
        if self.export_step >= self.export_total_steps:
            self.save_gif()
            return
            
        self.export_progress.setValue(self.export_step)
        
        js = """
        (function() {
            try {
                viewer.rotate(10, 'y');
                viewer.render();
                if (typeof viewer.pngURI === 'function') {
                    return viewer.pngURI();
                } else if (typeof viewer.png === 'function') {
                    return viewer.png();
                } else if (typeof viewer.getCanvas === 'function') {
                    var canvas = viewer.getCanvas();
                    return canvas ? canvas.toDataURL("image/png") : "";
                }
                return "";
            } catch(e) {
                console.error("Frame capture error:", e);
                return "";
            }
        })()
        """
        self.web_view.page().runJavaScript(js, self.on_frame_captured)

    def on_frame_captured(self, png_data_url):
        if not png_data_url:
            self.export_progress.close()
            QMessageBox.critical(self, "Export Error", "Frame capture failed.")
            return
            
        if png_data_url.startswith("data:image/"):
            base64_data = png_data_url.split(",")[1]
            try:
                import base64
                from PIL import Image
                import io
                image_data = base64.b64decode(base64_data)
                img = Image.open(io.BytesIO(image_data))
                self.export_frames.append(img.convert("RGBA"))
            except Exception as e:
                self.export_progress.close()
                QMessageBox.critical(self, "Export Error", f"Failed to process frame: {e}")
                return
        else:
            self.export_progress.close()
            QMessageBox.critical(self, "Export Error", "Invalid frame format received.")
            return
                
        self.export_step += 1
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(40, self.capture_next_frame)

    def save_gif(self):
        self.export_progress.setValue(self.export_total_steps)
        self.export_progress.close()
        
        if not self.export_frames:
            QMessageBox.warning(self, "Export Warning", "No frames were captured for GIF.")
            return
            
        try:
            self.export_frames[0].save(
                self.export_gif_path,
                save_all=True,
                append_images=self.export_frames[1:],
                duration=60,
                loop=0,
                disposal=2
            )
            self.statusBar().showMessage(f"Rotierendes GIF gespeichert: {os.path.basename(self.export_gif_path)}")
            QMessageBox.information(self, "Erfolg", f"Rotierendes GIF erfolgreich gespeichert:\n{self.export_gif_path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Saving GIF failed:\n{e}")
        finally:
            self.export_frames = []

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
                self.update_recent_files(file_name)
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
            "Supported Formats (*.mol *.sdf *.pdb *.smi *.xyz *.com);;MDL MOL (*.mol);;SDF (*.sdf);;PDB (*.pdb);;SMILES (*.smi);;XYZ (*.xyz);;Gaussian Input (*.com)", 
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
                elif ext == '.xyz':
                    with open(file_name, 'r') as f:
                        xyz_content = f.read()
                    mol = Chem.MolFromXYZBlock(xyz_content)
                    if mol:
                        from rdkit.Chem import rdDetermineBonds
                        try:
                            rdDetermineBonds.DetermineBonds(mol, charge=0)
                        except Exception:
                            pass
                elif ext == '.com':
                    # Parse first block of COM file for overlay
                    with open(file_name, 'r') as f:
                        content = f.read()
                    import re
                    from rdkit.Chem import rdDetermineBonds
                    blocks = re.split(r'(?i)--link1--', content)
                    pt = Chem.GetPeriodicTable()
                    for block in blocks:
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
                                    try: charge = int(parts[0])
                                    except ValueError: pass
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
                        if raw_mol:
                            try:
                                rdDetermineBonds.DetermineBonds(raw_mol, charge=charge)
                            except Exception:
                                pass
                            raw_mol.SetProp("_Name", title)
                            mol = raw_mol
                            break
                    
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

        donor_smarts = Chem.MolFromSmarts('[$([N,O,S;!H0])]')
        acceptor_smarts = Chem.MolFromSmarts('[$([O,N;!v4])]')
        donors = set(sum(mol.GetSubstructMatches(donor_smarts), ())) if donor_smarts else set()
        acceptors = set(sum(mol.GetSubstructMatches(acceptor_smarts), ())) if acceptor_smarts else set()

        props = []
        for i, atom in enumerate(mol.GetAtoms()):
            charge = 0.0
            logp = 0.0
            mr = 0.0
            hbond = 0
            if i in donors: hbond = 1
            elif i in acceptors: hbond = -1

            try:
                charge = float(atom.GetProp("_GasteigerCharge"))
                if math.isnan(charge) or math.isinf(charge): charge = 0.0
            except: pass
            try:
                logp = logp_contribs[i][0]
                mr = logp_contribs[i][1]
            except: pass
            props.append({"charge": charge, "logp": logp, "mr": mr, "hbond": hbond})

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


from symmetry_finder import find_symmetry

class SymmetryDialog(QDialog):
    def __init__(self, parent, mol):
        super().__init__(parent)
        self.setWindowTitle("Symmetry & Point Group Analysis")
        self.mol = mol
        self.app = parent
        
        # Non-modal so the user can freely interact with the 3D viewer (rotate, pan, zoom)
        self.setModal(False)
        self.setWindowModality(Qt.NonModal)
        self.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint | Qt.WindowCloseButtonHint | Qt.WindowMinimizeButtonHint)
        
        # Load user settings for plane styling & behavior
        settings = QSettings("LeMoVi", "LeMoVi")
        self.plane_color_mode = settings.value("symmetry/plane_color_mode", "#00e5ff")
        self.custom_plane_color = settings.value("symmetry/custom_plane_color", "#00e5ff")
        self.plane_border = settings.value("symmetry/plane_border", True, type=bool)
        self.plane_opacity = settings.value("symmetry/plane_opacity", 0.35, type=float)
        self.keep_on_close = settings.value("symmetry/keep_on_close", True, type=bool)
        
        # Position & geometry: restore saved position or place neatly to the right
        saved_geo = settings.value("symmetry/dialog_geometry")
        if saved_geo:
            self.restoreGeometry(saved_geo)
        else:
            self.resize(480, 540)
            if parent:
                p_geo = parent.geometry()
                x = p_geo.right() - 500 - 30
                y = p_geo.top() + 75
                self.move(max(p_geo.left() + 20, x), max(p_geo.top() + 40, y))
        
        # Calculate symmetry
        self.sym_data = find_symmetry(mol)
        
        self.setup_ui()
        self.update_content()

    def create_color_icon(self, hex_color):
        pixmap = QPixmap(14, 14)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor(hex_color))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(0, 0, 14, 14, 3, 3)
        painter.end()
        return QIcon(pixmap)

    def get_plane_color(self, index=0):
        if self.plane_color_mode == "multi":
            palette = ["#00e5ff", "#00e676", "#1de9b6", "#38bdf8", "#69f0ae", "#a7f3d0"]
            return palette[index % len(palette)]
        elif self.plane_color_mode == "custom":
            return self.custom_plane_color
        else:
            return self.plane_color_mode

    def setup_ui(self):
        self.setStyleSheet("""
            QDialog { background-color: #1e1e1e; color: #f1f5f9; }
            QLabel { color: #f1f5f9; font-family: 'Segoe UI', system-ui, sans-serif; }
            QPushButton { 
                background-color: #2b2d31; 
                color: #f1f5f9; 
                border: 1px solid #3f4248; 
                padding: 7px 14px; 
                border-radius: 5px; 
                font-family: 'Segoe UI', system-ui, sans-serif; 
                font-size: 12px;
                font-weight: 500;
            }
            QPushButton:hover { background-color: #3b3e45; border-color: #0284c7; }
            QPushButton:pressed { background-color: #232428; }
            #PrimaryBtn { 
                background-color: #0284c7; 
                border-color: #0369a1; 
                color: white; 
                font-weight: bold;
            }
            #PrimaryBtn:hover { background-color: #0369a1; }
            QListWidget { 
                background-color: #18191c; 
                color: #e2e8f0; 
                border: 1px solid #334155; 
                border-radius: 6px; 
                font-family: 'Segoe UI', system-ui, sans-serif; 
                font-size: 13px; 
                padding: 4px;
            }
            QListWidget::item {
                padding: 6px 8px;
                border-radius: 4px;
                margin-bottom: 2px;
            }
            QListWidget::item:hover {
                background-color: #23272a;
            }
            QListWidget::item:selected {
                background-color: #1e293b;
                color: #38bdf8;
            }
            QCheckBox { 
                color: #e2e8f0; 
                font-family: 'Segoe UI', system-ui, sans-serif; 
                font-size: 12px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                background-color: #2b2d31;
                border: 1px solid #475569;
                border-radius: 3px;
            }
            QCheckBox::indicator:checked {
                background-color: #0284c7;
                border-color: #0284c7;
            }
            QComboBox { 
                background-color: #2b2d31; 
                color: #f1f5f9; 
                border: 1px solid #475569; 
                border-radius: 4px; 
                padding: 4px 8px; 
                font-family: 'Segoe UI', system-ui, sans-serif; 
                font-size: 12px;
            }
            QComboBox::drop-down { border: none; }
            QComboBox QAbstractItemView { 
                background-color: #1e1e1e; 
                color: #f1f5f9; 
                selection-background-color: #0284c7; 
                border: 1px solid #475569;
            }
            QGroupBox {
                border: 1px solid #334155;
                border-radius: 6px;
                margin-top: 8px;
                padding-top: 10px;
                font-family: 'Segoe UI', system-ui, sans-serif;
                font-size: 11px;
                font-weight: bold;
                color: #94a3b8;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 4px;
            }
        """)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(14, 14, 14, 14)
        main_layout.setSpacing(10)
        
        # Point group info card
        header_frame = QFrame()
        header_frame.setStyleSheet("""
            QFrame {
                background-color: #25282e;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 8px;
            }
        """)
        header_layout = QVBoxLayout(header_frame)
        header_layout.setContentsMargins(10, 8, 10, 8)
        header_layout.setSpacing(4)
        
        self.pg_lbl = QLabel()
        self.pg_lbl.setStyleSheet("font-family: 'Segoe UI'; font-size: 14px;")
        header_layout.addWidget(self.pg_lbl)
        
        self.desc_lbl = QLabel()
        self.desc_lbl.setWordWrap(True)
        self.desc_lbl.setStyleSheet("color: #94a3b8; font-style: italic; font-size: 12px;")
        header_layout.addWidget(self.desc_lbl)
        
        status_hint = QLabel("● 3D-Ansicht bleibt aktiv (Drehen mit linker Maustaste, Zoomen mit Mausrad)")
        status_hint.setStyleSheet("color: #22c55e; font-size: 11px; font-weight: 500; margin-top: 2px;")
        header_layout.addWidget(status_hint)
        
        main_layout.addWidget(header_frame)
        
        # Elements list section
        list_lbl = QLabel("Symmetrieelemente (Auswählen zum Einblenden in 3D):")
        list_lbl.setStyleSheet("font-weight: bold; color: #e2e8f0; font-size: 12px;")
        main_layout.addWidget(list_lbl)
        
        self.list_widget = QListWidget()
        self.list_widget.itemChanged.connect(self.on_item_toggled)
        self.list_widget.itemDoubleClicked.connect(self.on_item_double_clicked)
        main_layout.addWidget(self.list_widget)
        
        # Mirror Plane Appearance Controls in GroupBox
        self.plane_group = QGroupBox("Spiegelebenen-Darstellung")
        plane_opts_layout = QHBoxLayout(self.plane_group)
        plane_opts_layout.setContentsMargins(10, 8, 10, 8)
        plane_opts_layout.setSpacing(10)
        
        self.color_lbl = QLabel("Farbe:")
        self.color_lbl.setStyleSheet("font-weight: bold; color: #cbd5e1;")
        plane_opts_layout.addWidget(self.color_lbl)
        
        self.color_combo = QComboBox()
        color_items = [
            ("Hellblau / Cyan (Standard)", "#00e5ff"),
            ("Hellgrün / Mint", "#00e676"),
            ("Mehrfarbig (Hellblau & Grün)", "multi"),
            ("Smaragd / Teal", "#1de9b6"),
            ("Himmelblau / Sky Blue", "#38bdf8"),
            ("Pastellgrün / Seafoam", "#69f0ae"),
            ("Klassisch Blau", "#2979ff"),
            ("Benutzerdefiniert...", "custom")
        ]
        selected_idx = 0
        for idx, (name, val) in enumerate(color_items):
            self.color_combo.addItem(name, val)
            if val == self.plane_color_mode:
                selected_idx = idx
        if self.plane_color_mode not in [v for _, v in color_items]:
            selected_idx = len(color_items) - 1
        self.color_combo.setCurrentIndex(selected_idx)
        self.color_combo.currentIndexChanged.connect(self.on_plane_color_changed)
        plane_opts_layout.addWidget(self.color_combo)
        
        self.border_cb = QCheckBox("Randlinie")
        self.border_cb.setChecked(self.plane_border)
        self.border_cb.setToolTip("Hebt die kreisförmige Begrenzung der Spiegelebene mit einer Konturlinie hervor")
        self.border_cb.toggled.connect(self.on_plane_style_changed)
        plane_opts_layout.addWidget(self.border_cb)
        
        plane_opts_layout.addSpacing(6)
        self.opacity_lbl = QLabel("Deckkraft:")
        plane_opts_layout.addWidget(self.opacity_lbl)
        self.opacity_combo = QComboBox()
        opacity_items = [
            ("35% (Ausgewogen)", 0.35),
            ("20% (Zart)", 0.20),
            ("50% (Kräftig)", 0.50)
        ]
        op_idx = 0
        for idx, (name, val) in enumerate(opacity_items):
            self.opacity_combo.addItem(name, val)
            if abs(val - self.plane_opacity) < 0.05:
                op_idx = idx
        self.opacity_combo.setCurrentIndex(op_idx)
        self.opacity_combo.currentIndexChanged.connect(self.on_plane_style_changed)
        plane_opts_layout.addWidget(self.opacity_combo)
        
        main_layout.addWidget(self.plane_group)
        
        # Action buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        
        self.all_btn = QPushButton("Select All")
        self.all_btn.setToolTip("Alle Symmetrieelemente auswählen und anzeigen")
        self.all_btn.clicked.connect(self.select_all)
        
        self.none_btn = QPushButton("Deselect All")
        self.none_btn.setToolTip("Alle Symmetrieelemente abwählen und ausblenden")
        self.none_btn.clicked.connect(self.deselect_all)
        
        self.center_btn = QPushButton("Ansicht zentrieren")
        self.center_btn.setToolTip("Zentriert das Molekül und die Symmetrieelemente in der 3D-Ansicht")
        self.center_btn.clicked.connect(self.app.center_view)
        
        self.close_btn = QPushButton("Close")
        self.close_btn.setObjectName("PrimaryBtn")
        self.close_btn.clicked.connect(self.reject)
        
        btn_layout.addWidget(self.all_btn)
        btn_layout.addWidget(self.none_btn)
        btn_layout.addWidget(self.center_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.close_btn)
        
        main_layout.addLayout(btn_layout)
        
        # Keep elements on close option
        bottom_opts_layout = QHBoxLayout()
        self.keep_on_close_cb = QCheckBox("Elemente beim Schließen in 3D beibehalten")
        self.keep_on_close_cb.setChecked(self.keep_on_close)
        self.keep_on_close_cb.setToolTip("Wenn aktiviert, bleiben ausgewählte Symmetrieelemente auch nach dem Schließen dieses Fensters in der 3D-Ansicht sichtbar.")
        bottom_opts_layout.addWidget(self.keep_on_close_cb)
        bottom_opts_layout.addStretch()
        
        main_layout.addLayout(bottom_opts_layout)

    def update_content(self):
        pg = self.sym_data.get("point_group", "C1")
        pg_display = pg
        subscripts = {"0":"₀", "1":"₁", "2":"₂", "3":"₃", "4":"₄", "5":"₅", "6":"₆", "7":"₇", "8":"₈", "9":"₉", "i":"ᵢ", "d":"d", "h":"ₕ", "v":"ᵥ", "s":"ₛ", "inf": "∞"}
        for k, v in subscripts.items():
            pg_display = pg_display.replace(k, v)
        
        self.pg_lbl.setText(f"Detected Point Group: <b style='font-size: 18px; color: #38bdf8;'>{pg_display}</b>")
        self.desc_lbl.setText(self.get_point_group_description(pg))
        
        has_planes = len(self.sym_data.get("planes", [])) > 0
        self.color_lbl.setEnabled(has_planes)
        self.color_combo.setEnabled(has_planes)
        self.border_cb.setEnabled(has_planes)
        self.opacity_lbl.setEnabled(has_planes)
        self.opacity_combo.setEnabled(has_planes)
        
        self.show_symmetry_elements()

    def update_molecule(self, mol):
        self.mol = mol
        self.sym_data = find_symmetry(mol)
        self.update_content()

    def get_point_group_description(self, pg):
        descriptions = {
            "C1": "No symmetry elements except identity (chiral).",
            "Cs": "Only one mirror plane (plane of symmetry).",
            "Ci": "Only an inversion center.",
            "Cinfv": "Linear molecule without horizontal mirror plane (e.g. CO, HCl).",
            "Dinfh": "Linear molecule with horizontal mirror plane (e.g. N2, CO2).",
            "Td": "Tetrahedral symmetry (e.g. CH4, CCl4).",
            "Oh": "Octahedral symmetry (e.g. SF6).",
            "Ih": "Icosahedral symmetry (e.g. C60).",
        }
        if pg in descriptions:
            return descriptions[pg]
        
        if pg.startswith("C") and pg.endswith("v"):
            n = pg[1:-1]
            return f"C{n}v group: One principal C{n} axis and {n} vertical mirror planes (e.g. H2O is C2v, NH3 is C3v)."
        elif pg.startswith("C") and pg.endswith("h"):
            n = pg[1:-1]
            return f"C{n}h group: One principal C{n} axis and one horizontal mirror plane."
        elif pg.startswith("D") and pg.endswith("h"):
            n = pg[1:-1]
            return f"D{n}h group: One C{n} axis, {n} perpendicular C2 axes, one horizontal mirror plane, and {n} vertical mirror planes (e.g. Benzene is D6h, Ethene is D2h)."
        elif pg.startswith("D") and pg.endswith("d"):
            n = pg[1:-1]
            return f"D{n}d group: One C{n} axis, {n} perpendicular C2 axes, and {n} dihedral mirror planes (e.g. Allene is D2d, Cyclohexane is D3d)."
        elif pg.startswith("D"):
            n = pg[1:]
            return f"D{n} group: One C{n} axis and {n} perpendicular C2 axes (chiral)."
        elif pg.startswith("C"):
            n = pg[1:]
            return f"C{n} group: Only a principal C{n} axis (chiral)."
        elif pg.startswith("S"):
            n = pg[1:]
            return f"S{n} group: Only an S{n} improper rotation axis."
        
        return "Symmetric point group."
        
    def show_symmetry_elements(self):
        self.list_widget.blockSignals(True)
        self.list_widget.clear()
        
        com = self.sym_data.get("center_of_mass", [0,0,0])
        
        if self.sym_data.get("inversion"):
            item = QListWidgetItem("Inversion Center (i)")
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            item.setIcon(self.create_color_icon("#ffeb3b"))
            item.setData(Qt.UserRole, {"type": "inversion", "center": com})
            self.list_widget.addItem(item)
            
        for i, ax in enumerate(self.sym_data.get("axes", [])):
            n = ax["n"]
            vec = ax["vector"]
            item = QListWidgetItem(f"Proper Rotation Axis C{n} (Axis {i+1})")
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            item.setIcon(self.create_color_icon("#ff1744"))
            item.setData(Qt.UserRole, {"type": "axis", "n": n, "vector": vec, "center": com, "id": f"axis_{i}"})
            self.list_widget.addItem(item)
            
        subscript_map = {"0":"₀", "1":"₁", "2":"₂", "3":"₃", "4":"₄", "5":"₅", "6":"₆", "7":"₇", "8":"₈", "9":"₉"}
        planes_list = self.sym_data.get("planes", [])
        multiple_planes = len(planes_list) > 1
        for i, pl in enumerate(planes_list):
            normal = pl["normal"]
            i_sub = "".join(subscript_map.get(c, c) for c in str(i+1)) if multiple_planes else ""
            label_text = f"Spiegelebene / Mirror Plane σ{i_sub} (Plane {i+1})" if multiple_planes else "Spiegelebene / Mirror Plane σ"
            color = self.get_plane_color(i)
            item = QListWidgetItem(label_text)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            item.setIcon(self.create_color_icon(color))
            item.setData(Qt.UserRole, {
                "type": "plane",
                "normal": normal,
                "center": com,
                "id": f"plane_{i}",
                "index": i,
                "label": f"σ{i_sub}" if multiple_planes else "σ"
            })
            self.list_widget.addItem(item)
            
        self.list_widget.blockSignals(False)

    def on_item_double_clicked(self, item):
        new_state = Qt.Unchecked if item.checkState() == Qt.Checked else Qt.Checked
        item.setCheckState(new_state)

    def on_plane_color_changed(self, index):
        data = self.color_combo.itemData(index)
        if data == "custom":
            initial_col = QColor(self.custom_plane_color)
            col = QColorDialog.getColor(initial_col, self, "Spiegelebenen-Farbe wählen")
            if col.isValid():
                self.custom_plane_color = col.name()
                self.plane_color_mode = "custom"
                self.color_combo.setItemText(index, f"Benutzerdefiniert ({self.custom_plane_color})")
            else:
                for i in range(self.color_combo.count()):
                    if self.color_combo.itemData(i) == self.plane_color_mode:
                        self.color_combo.blockSignals(True)
                        self.color_combo.setCurrentIndex(i)
                        self.color_combo.blockSignals(False)
                        break
                return
        else:
            self.plane_color_mode = data
            
        self.save_plane_settings()
        self.refresh_planes()

    def on_plane_style_changed(self):
        self.plane_border = self.border_cb.isChecked()
        self.plane_opacity = float(self.opacity_combo.currentData())
        self.save_plane_settings()
        self.refresh_planes()

    def save_plane_settings(self):
        settings = QSettings("LeMoVi", "LeMoVi")
        settings.setValue("symmetry/plane_color_mode", self.plane_color_mode)
        settings.setValue("symmetry/custom_plane_color", self.custom_plane_color)
        settings.setValue("symmetry/plane_border", self.plane_border)
        settings.setValue("symmetry/plane_opacity", self.plane_opacity)

    def refresh_planes(self):
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            data = item.data(Qt.UserRole)
            if data and data.get("type") == "plane":
                idx = data.get("index", 0)
                color = self.get_plane_color(idx)
                item.setIcon(self.create_color_icon(color))
                if item.checkState() == Qt.Checked:
                    self.render_plane(data, checked=True)

    def render_plane(self, data, checked=True):
        plane_id = data["id"]
        if checked:
            nx, ny, nz = data["normal"]
            cx, cy, cz = data["center"]
            idx = data.get("index", 0)
            color = self.get_plane_color(idx)
            label = data.get("label", "σ")
            radius = 3.5
            try:
                conf = self.mol.GetConformer()
                max_dist = 0
                for atom in self.mol.GetAtoms():
                    pos = conf.GetAtomPosition(atom.GetIdx())
                    dist = math.sqrt((pos.x-cx)**2 + (pos.y-cy)**2 + (pos.z-cz)**2)
                    if dist > max_dist:
                        max_dist = dist
                radius = max(2.5, max_dist + 1.2)
            except:
                pass
            border_js = "true" if self.plane_border else "false"
            op_js = str(self.plane_opacity)
            js = f"drawSymmetryPlane('{plane_id}', {nx}, {ny}, {nz}, '{color}', {radius}, {cx}, {cy}, {cz}, '{label}', {border_js}, {op_js});"
            self.app.web_view.page().runJavaScript(js)
        else:
            self.app.web_view.page().runJavaScript(f"clearSymmetryElement('{plane_id}');")

    def on_item_toggled(self, item):
        data = item.data(Qt.UserRole)
        checked = (item.checkState() == Qt.Checked)
        if not data:
            return
            
        typ = data["type"]
        
        if typ == "inversion":
            if checked:
                cx, cy, cz = data["center"]
                js = f"drawInversionCenter('inversion', {cx}, {cy}, {cz}, '#ffeb3b');"
                self.app.web_view.page().runJavaScript(js)
            else:
                self.app.web_view.page().runJavaScript("clearSymmetryElement('inversion');")
                
        elif typ == "axis":
            axis_id = data["id"]
            if checked:
                n = data["n"]
                vx, vy, vz = data["vector"]
                cx, cy, cz = data["center"]
                length = 4.5
                try:
                    conf = self.mol.GetConformer()
                    max_dist = 0
                    for atom in self.mol.GetAtoms():
                        pos = conf.GetAtomPosition(atom.GetIdx())
                        dist = math.sqrt((pos.x-cx)**2 + (pos.y-cy)**2 + (pos.z-cz)**2)
                        if dist > max_dist:
                            max_dist = dist
                    length = max(3.5, max_dist + 1.2)
                except:
                    pass
                x1, y1, z1 = cx - vx * length, cy - vy * length, cz - vz * length
                x2, y2, z2 = cx + vx * length, cy + vy * length, cz + vz * length
                label = f"C{n}"
                js = f"drawSymmetryAxis('{axis_id}', {x1}, {y1}, {z1}, {x2}, {y2}, {z2}, '#ff1744', '{label}');"
                self.app.web_view.page().runJavaScript(js)
            else:
                self.app.web_view.page().runJavaScript(f"clearSymmetryElement('{axis_id}');")
                
        elif typ == "plane":
            self.render_plane(data, checked=checked)

    def select_all(self):
        self.list_widget.blockSignals(True)
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            item.setCheckState(Qt.Checked)
            self.on_item_toggled(item)
        self.list_widget.blockSignals(False)
        
    def deselect_all(self):
        self.list_widget.blockSignals(True)
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            item.setCheckState(Qt.Unchecked)
            self.on_item_toggled(item)
        self.list_widget.blockSignals(False)
        
    def clear_visualizations(self):
        self.app.web_view.page().runJavaScript("clearAllSymmetryElements();")

    def reject(self):
        try:
            settings = QSettings("LeMoVi", "LeMoVi")
            settings.setValue("symmetry/dialog_geometry", self.saveGeometry())
            settings.setValue("symmetry/keep_on_close", self.keep_on_close_cb.isChecked())
            if not self.keep_on_close_cb.isChecked():
                self.clear_visualizations()
        except Exception as e:
            print("Error saving symmetry settings on close:", e)
        super().reject()

    def accept(self):
        self.reject()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lemovi-logo.png")
    splash = None
    if os.path.exists(logo_path):
        pixmap = QPixmap(logo_path)
        if pixmap.width() > 600:
            pixmap = pixmap.scaledToWidth(600, Qt.SmoothTransformation)
        splash = QSplashScreen(pixmap, Qt.WindowStaysOnTopHint)
        splash.show()
        app.processEvents()
        
        # Small delay to ensure splash is visible for at least a moment
        import time
        time.sleep(1)
        
    window = MolViewer3D()
    window.showMaximized()
    
    if splash:
        splash.finish(window)
        
    sys.exit(app.exec_())

