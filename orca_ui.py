import os
import sys
import json
import math
import re

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
                             QPushButton, QComboBox, QSpinBox, QDoubleSpinBox, QCheckBox, QTextEdit, QDialog, 
                             QTableWidget, QTableWidgetItem, QHeaderView, QTabWidget, 
                             QMessageBox, QSplitter, QGroupBox, QFileDialog, QFormLayout)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QPainter, QPen


from orca_manager import (OrcaJobManager, DEFAULT_NMR_REFS, DEFAULT_TMS_REFERENCES, 
                        load_tms_references, save_tms_references, find_best_tms_match,
                        DEFAULT_TANTILLO_SCALING, load_tantillo_scaling, save_tantillo_scaling, find_best_tantillo_match,
                        format_orca_method)


class EnergyPlotWidget(QWidget):
    """A beautiful custom QPainter-based widget to draw SCF energy convergence."""
    stepClicked = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.energies = []
        self.points_coords = []
        self.selected_step = -1
        self.setMinimumHeight(150)
        self.setCursor(Qt.PointingHandCursor)

    def set_energies(self, energies):
        self.energies = energies
        if energies:
            self.selected_step = len(energies) - 1
        else:
            self.selected_step = -1
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw background
        painter.fillRect(self.rect(), QColor("#222222"))
        
        if not self.energies:
            painter.setPen(QColor("#888888"))
            painter.drawText(self.rect(), Qt.AlignCenter, "No energy convergence data available")
            return

        # Margins
        margin_left = 60
        margin_right = 20
        margin_top = 20
        margin_bottom = 30
        
        w = self.width() - margin_left - margin_right
        h = self.height() - margin_top - margin_bottom

        # Min and Max energy values
        min_e = min(self.energies)
        max_e = max(self.energies)
        range_e = max_e - min_e if max_e != min_e else 1.0

        # Draw grid and axes
        painter.setPen(QColor("#444444"))
        painter.drawLine(margin_left, margin_top, margin_left, margin_top + h)
        painter.drawLine(margin_left, margin_top + h, margin_left + w, margin_top + h)

        # Draw Y-axis labels (Energies)
        painter.setPen(QColor("#aaaaaa"))
        painter.setFont(QFont("Segoe UI", 8))
        painter.drawText(10, margin_top + 5, f"{max_e:.4f}")
        painter.drawText(10, margin_top + h, f"{min_e:.4f}")

        # Draw X-axis labels (Steps)
        num_steps = len(self.energies)
        step_w = w / (num_steps - 1) if num_steps > 1 else w

        # Draw line plot
        pen = QPen(QColor("#0078D4"), 2)
        painter.setPen(pen)

        self.points_coords = []
        for i, energy in enumerate(self.energies):
            x = margin_left + i * step_w
            y = margin_top + h - ((energy - min_e) / range_e) * h
            self.points_coords.append((x, y))

        for i in range(len(self.points_coords) - 1):
            p1 = self.points_coords[i]
            p2 = self.points_coords[i+1]
            painter.drawLine(int(p1[0]), int(p1[1]), int(p2[0]), int(p2[1]))

        # Draw point dots and highlight the selected one
        for i, p in enumerate(self.points_coords):
            x, y = int(p[0]), int(p[1])
            if i == self.selected_step:
                painter.setPen(QPen(QColor("#e81123"), 2))
                painter.setBrush(QColor("#ffffff"))
                painter.drawEllipse(x - 5, y - 5, 10, 10)
            else:
                painter.setPen(QColor("#0078D4"))
                painter.setBrush(QColor("#ffffff"))
                painter.drawEllipse(x - 3, y - 3, 6, 6)

        # Label for steps
        painter.setPen(QColor("#888888"))
        selected_text = f" (Ausgewaehlt: Schritt {self.selected_step + 1})" if self.selected_step != -1 else ""
        painter.drawText(margin_left + w//2 - 60, margin_top + h + 20, f"Schritt (Gesamt: {num_steps}){selected_text}")

    def mousePressEvent(self, event):
        if not self.points_coords:
            return
        
        click_pos = event.pos()
        click_x = click_pos.x()
        click_y = click_pos.y()
        
        closest_idx = -1
        min_dist = 15.0
        for i, (px, py) in enumerate(self.points_coords):
            dist = ((px - click_x)**2 + (py - click_y)**2)**0.5
            if dist < min_dist:
                min_dist = dist
                closest_idx = i
                
        if closest_idx != -1 and closest_idx != self.selected_step:
            self.selected_step = closest_idx
            self.update()
            self.stepClicked.emit(closest_idx)


class IrSpectrumPlotWidget(QWidget):
    """Widget for plotting calculated Infrared (IR) Vibrational Spectrum with peak broadening."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.modes = []
        self.fwhm = 15.0
        self.setMinimumHeight(240)

    def set_modes(self, modes):
        self.modes = [m for m in modes if m.get("frequency", 0) > 0]
        self.update()

    def set_fwhm(self, fwhm):
        self.fwhm = max(2.0, min(80.0, float(fwhm)))
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor("#1e1e1e"))

        if not self.modes:
            painter.setPen(QColor("#888888"))
            painter.drawText(self.rect(), Qt.AlignCenter, "No vibrational frequency data available for IR spectrum")
            return

        margin_left = 65
        margin_right = 25
        margin_top = 25
        margin_bottom = 35
        w = self.width() - margin_left - margin_right
        h = self.height() - margin_top - margin_bottom

        x_min, x_max = 400.0, 4000.0
        x_span = x_max - x_min

        num_points = max(250, w)
        freqs = [x_max - i * (x_span / (num_points - 1)) for i in range(num_points)]
        intensities = [0.0] * num_points
        sigma = self.fwhm / 2.35482

        for mode in self.modes:
            v_k = mode["frequency"]
            i_k = mode.get("intensity", 0.0)
            if v_k < x_min or v_k > x_max or i_k <= 0:
                continue
            for idx, v in enumerate(freqs):
                diff = v - v_k
                intensities[idx] += i_k * math.exp(-(diff * diff) / (2.0 * sigma * sigma))

        max_int = max(intensities) if intensities and max(intensities) > 0 else 1.0

        # Grid and Ticks
        painter.setPen(QColor("#333333"))
        for tick_v in [4000, 3500, 3000, 2500, 2000, 1500, 1000, 500]:
            px = margin_left + ((x_max - tick_v) / x_span) * w
            painter.drawLine(int(px), margin_top, int(px), margin_top + h)
            painter.setPen(QColor("#777777"))
            painter.setFont(QFont("Segoe UI", 8))
            painter.drawText(int(px) - 15, margin_top + h + 18, str(tick_v))
            painter.setPen(QColor("#333333"))

        painter.setPen(QColor("#555555"))
        painter.drawLine(margin_left, margin_top, margin_left, margin_top + h)
        painter.drawLine(margin_left, margin_top + h, margin_left + w, margin_top + h)

        # Labels
        painter.setPen(QColor("#aaaaaa"))
        painter.setFont(QFont("Segoe UI", 9))
        painter.drawText(margin_left + w // 2 - 60, margin_top + h + 32, "Wavenumber (cm⁻¹)")
        painter.drawText(10, margin_top + 12, "IR Absorbance")

        # Plot Curve
        pen = QPen(QColor("#4fc3f7"), 2)
        painter.setPen(pen)

        path_points = []
        for idx, i_val in enumerate(intensities):
            px = margin_left + idx * (w / (num_points - 1))
            py = margin_top + h - (i_val / max_int) * (h - 15)
            path_points.append((px, py))

        for i in range(len(path_points) - 1):
            p1 = path_points[i]
            p2 = path_points[i+1]
            painter.drawLine(int(p1[0]), int(p1[1]), int(p2[0]), int(p2[1]))

        # Stick peaks
        max_mode_int = max(m.get("intensity", 1.0) for m in self.modes) or 1.0
        painter.setPen(QPen(QColor("#e81123"), 1, Qt.DashLine))
        for mode in self.modes:
            v_k = mode["frequency"]
            i_k = mode.get("intensity", 0.0)
            if x_min <= v_k <= x_max and i_k > 0:
                px = margin_left + ((x_max - v_k) / x_span) * w
                py = margin_top + h - (i_k / max_mode_int) * (h - 15)
                painter.drawLine(int(px), margin_top + h, int(px), int(py))


class NmrSpectrumPlotWidget(QWidget):
    """Widget for plotting calculated 1H or 13C NMR Chemical Shift Spectra with Lorentzian broadening."""
    atomClicked = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.shifts = []
        self.nucleus = "1H"
        self.fwhm = 0.05
        self.highlighted_atom = None
        self.setMinimumHeight(240)
        self.setCursor(Qt.PointingHandCursor)

    def set_data(self, shifts, nucleus="1H"):
        self.nucleus = nucleus
        self.fwhm = 0.05 if nucleus == "1H" else 0.5
        self.shifts = [s for s in shifts if s.get("elem") == ("H" if nucleus == "1H" else "C")]
        self.highlighted_atom = None
        self.update()

    def set_fwhm(self, fwhm):
        self.fwhm = max(0.005, float(fwhm))
        self.update()

    def highlight_atom(self, atom_name):
        self.highlighted_atom = atom_name
        self.update()

    def mousePressEvent(self, event):
        if not self.shifts:
            return
        
        margin_left = 65
        margin_right = 25
        w = self.width() - margin_left - margin_right
        
        if self.nucleus == "1H":
            x_min, x_max = -0.5, 12.5
        else:
            x_min, x_max = -5.0, 220.0
            
        x_span = x_max - x_min
        click_x = event.x()
        
        if click_x < margin_left or click_x > self.width() - margin_right:
            return
            
        # Convert X coordinate back to ppm chemical shift value
        clicked_ppm = x_max - ((click_x - margin_left) / w) * x_span
        
        closest_shift = None
        min_diff = float("inf")
        threshold = 0.3 if self.nucleus == "1H" else 4.0
        
        for s in self.shifts:
            diff = abs(s["shift"] - clicked_ppm)
            if diff < min_diff and diff < threshold:
                min_diff = diff
                closest_shift = s
                
        if closest_shift:
            self.highlight_atom(closest_shift["atom"])
            self.atomClicked.emit(closest_shift["atom"])

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor("#1e1e1e"))

        if not self.shifts:
            painter.setPen(QColor("#888888"))
            painter.drawText(self.rect(), Qt.AlignCenter, f"No calculated {self.nucleus} NMR shift data available")
            return

        margin_left = 65
        margin_right = 25
        margin_top = 25
        margin_bottom = 35
        w = self.width() - margin_left - margin_right
        h = self.height() - margin_top - margin_bottom

        if self.nucleus == "1H":
            x_min, x_max = -0.5, 12.5
            ticks = [12, 10, 8, 6, 4, 2, 0]
        else:
            x_min, x_max = -5.0, 220.0
            ticks = [200, 160, 120, 80, 40, 0]

        x_span = x_max - x_min
        num_points = max(300, w)
        ppm_vals = [x_max - i * (x_span / (num_points - 1)) for i in range(num_points)]
        intensities = [0.0] * num_points
        half_w = self.fwhm / 2.0

        for s in self.shifts:
            shift_val = s["shift"]
            if shift_val < x_min or shift_val > x_max:
                continue
            for idx, ppm in enumerate(ppm_vals):
                diff = ppm - shift_val
                intensities[idx] += 1.0 / (1.0 + (diff / half_w) ** 2)

        max_int = max(intensities) if intensities and max(intensities) > 0 else 1.0

        # Grid & Ticks
        painter.setPen(QColor("#333333"))
        for tick in ticks:
            px = margin_left + ((x_max - tick) / x_span) * w
            painter.drawLine(int(px), margin_top, int(px), margin_top + h)
            painter.setPen(QColor("#777777"))
            painter.setFont(QFont("Segoe UI", 8))
            painter.drawText(int(px) - 10, margin_top + h + 18, str(tick))
            painter.setPen(QColor("#333333"))

        painter.setPen(QColor("#555555"))
        painter.drawLine(margin_left, margin_top, margin_left, margin_top + h)
        painter.drawLine(margin_left, margin_top + h, margin_left + w, margin_top + h)

        painter.setPen(QColor("#aaaaaa"))
        painter.setFont(QFont("Segoe UI", 9))
        painter.drawText(margin_left + w // 2 - 60, margin_top + h + 32, f"{self.nucleus} Chemical Shift (δ, ppm)")
        painter.drawText(10, margin_top + 12, "Intensity")

        # Plot Spectrum
        pen = QPen(QColor("#54b354" if self.nucleus == "1H" else "#ff9800"), 2)
        painter.setPen(pen)

        path_points = []
        for idx, i_val in enumerate(intensities):
            px = margin_left + idx * (w / (num_points - 1))
            py = margin_top + h - (i_val / max_int) * (h - 15)
            path_points.append((px, py))

        for i in range(len(path_points) - 1):
            p1 = path_points[i]
            p2 = path_points[i+1]
            painter.drawLine(int(p1[0]), int(p1[1]), int(p2[0]), int(p2[1]))

        # Atom Labels & Delta sticks
        for s in self.shifts:
            shift_val = s["shift"]
            if x_min <= shift_val <= x_max:
                px = margin_left + ((x_max - shift_val) / x_span) * w
                is_high = (self.highlighted_atom == s["atom"])
                if is_high:
                    painter.setPen(QPen(QColor("#ff3333"), 2, Qt.SolidLine))
                    painter.drawLine(int(px), margin_top + h, int(px), margin_top + 8)
                    painter.setBrush(QColor("#ff3333"))
                    painter.drawEllipse(int(px) - 4, margin_top + 8, 8, 8)
                    painter.setPen(QColor("#ff3333"))
                    painter.setFont(QFont("Segoe UI", 9, QFont.Bold))
                    painter.drawText(int(px) - 14, margin_top + 4, f"{s['atom']} ({shift_val:.2f})")
                else:
                    painter.setPen(QPen(QColor("#ffffff"), 1, Qt.SolidLine))
                    painter.drawLine(int(px), margin_top + 30, int(px), margin_top + 20)
                    painter.setPen(QColor("#4fc3f7"))
                    painter.setFont(QFont("Segoe UI", 7))
                    painter.drawText(int(px) - 12, margin_top + 16, f"{s['atom']} ({shift_val:.2f})")
        painter.setPen(QPen(QColor("#ffffff"), 1, Qt.SolidLine))
        painter.setBrush(Qt.NoBrush)

class OrcaSetupDialog(QDialog):

    def __init__(self, parent, xyz_content, job_manager, default_name="orca_calc"):
        super().__init__(parent)
        self.setWindowTitle("ORCA 6 Calculation Setup")
        self.resize(750, 500)
        self.setStyleSheet("""
            QDialog { background-color: #1e1e1e; color: white; }
            QLabel { color: #ffffff; font-family: 'Segoe UI'; }
            QLineEdit, QSpinBox { background-color: #2d2d2d; color: white; border: 1px solid #444; padding: 4px; border-radius: 4px; }
            QComboBox { background-color: #333; color: white; border: 1px solid #444; padding: 4px; border-radius: 4px; }
            QTextEdit { background-color: #151515; color: #8ef28e; font-family: 'Consolas'; border: 1px solid #333; }
        """)

        self.xyz_content = xyz_content
        self.job_manager = job_manager

        # Layout
        self.layout = QHBoxLayout(self)
        left_layout = QVBoxLayout()
        right_layout = QVBoxLayout()

        # Job Name
        left_layout.addWidget(QLabel("Job Name:"))
        self.name_input = QLineEdit(default_name)
        left_layout.addWidget(self.name_input)

        # Task/Calculation Type
        left_layout.addWidget(QLabel("Calculation Type:"))
        self.task_combo = QComboBox()
        self.task_combo.addItems([
            "Opt", "Freq", "Opt+Freq", "NMR", "Opt+NMR", "Opt+Freq+NMR", "Single Point (SP)"
        ])
        left_layout.addWidget(self.task_combo)

        # Method
        left_layout.addWidget(QLabel("Method/Functional (Geometry):"))
        self.method_combo = QComboBox()
        self.method_combo.addItems([
            "B3LYP", "PBE0", "mPW1PW91", "BMK", "WC04", "WP04", "M06-2X", "wB97X-D4", "HF", "r2SCAN-3c", "HF-3c", "MP2", "DLPNO-CCSD(T)"
        ])
        left_layout.addWidget(self.method_combo)

        # Basis Set
        left_layout.addWidget(QLabel("Basis Set (Geometry):"))
        self.basis_combo = QComboBox()
        self.basis_combo.addItems([
            # Karlsruhe/Ahlrichs Basis Sets
            "def2-SVP", "def2-TZVP", "def2-TZVPP", "def2-QZVP", "def2-mSVP",
            
            # Minimally Augmented def2 Basis Sets
            "ma-def2-SVP", "ma-def2-TZVP", "ma-def2-TZVPP",
            
            # Pople Basis Sets
            "6-31G", "6-31G*", "6-31G**", "6-31+G*", "6-31++G**", "6-31+G(d,p)", "6-311+G(2d,p)",
            
            # Jensen's Polarization Consistent (Optimized for DFT Properties)
            "pcseg-1", "pcseg-2", "pcseg-3", "aug-pcseg-1", "aug-pcseg-2",
            
            # Dunning's Correlation Consistent (Optimized for Wavefunction Methods)
            "cc-pVDZ", "cc-pVTZ", "cc-pVQZ", "aug-cc-pVDZ", "aug-cc-pVTZ", "aug-cc-pVQZ",
            
            "None (Semi-empirical)"
        ])
        left_layout.addWidget(self.basis_combo)

        # Separate NMR Method & Basis Set Option
        self.sep_nmr_cb = QCheckBox("Use separate Method & Basis Set for NMR (% Compound)")
        self.sep_nmr_cb.setStyleSheet("color: #4fc3f7; font-weight: bold;")
        left_layout.addWidget(self.sep_nmr_cb)

        self.sep_nmr_widget = QWidget()
        nmr_layout = QFormLayout(self.sep_nmr_widget)
        nmr_layout.setContentsMargins(10, 2, 0, 2)
        
        self.nmr_method_combo = QComboBox()
        self.nmr_method_combo.addItems([
            "mPW1PW91", "BMK", "WC04", "WP04", "B3LYP", "PBE0", "M06-2X", "M06-L", "VSXC", "MP2", "HF"
        ])
        
        self.nmr_basis_combo = QComboBox()
        self.nmr_basis_combo.addItems([
            # Karlsruhe/Ahlrichs Basis Sets
            "def2-SVP", "def2-TZVP", "def2-TZVPP", "def2-QZVP", "def2-mSVP",
            
            # Minimally Augmented def2 Basis Sets
            "ma-def2-SVP", "ma-def2-TZVP", "ma-def2-TZVPP",
            
            # Pople Basis Sets
            "6-31G", "6-31G*", "6-31G**", "6-31+G*", "6-31++G**", "6-31+G(d,p)", "6-311+G(2d,p)",
            
            # Jensen's Polarization Consistent (Optimized for DFT Properties)
            "pcseg-1", "pcseg-2", "pcseg-3", "aug-pcseg-1", "aug-pcseg-2",
            
            # Dunning's Correlation Consistent (Optimized for Wavefunction Methods)
            "cc-pVDZ", "cc-pVTZ", "cc-pVQZ", "aug-cc-pVDZ", "aug-cc-pVTZ", "aug-cc-pVQZ",
            
            "None (Semi-empirical)"
        ])
        self.nmr_basis_combo.setCurrentText("6-311+G(2d,p)")
        
        nmr_layout.addRow("NMR Method:", self.nmr_method_combo)
        nmr_layout.addRow("NMR Basis Set:", self.nmr_basis_combo)

        # Solvent for NMR step (inside sep_nmr_widget)
        self.nmr_solvent_model_combo = QComboBox()
        self.nmr_solvent_model_combo.addItems(["None (Gas)", "CPCM", "SMD", "PCM", "SCRF"])
        self.nmr_solvent_model_combo.setCurrentIndex(0)
        self.nmr_solvent_model_combo.currentTextChanged.connect(self._update_nmr_solvent_visibility)
        self.nmr_solvent_model_combo.currentTextChanged.connect(self.update_preview)
        nmr_layout.addRow("NMR Solvent Model:", self.nmr_solvent_model_combo)

        self.nmr_solvent_combo = QComboBox()
        self.nmr_solvent_combo.addItems([
            "Chloroform", "Acetone", "Acetonitrile", "Benzene", "DMSO",
            "Dichloromethane", "Ethanol", "Hexane", "Methanol", "THF", "Toluene", "Water"
        ])
        self.nmr_solvent_combo.setCurrentText("Chloroform")
        self.nmr_solvent_combo.currentTextChanged.connect(self.update_preview)
        self.nmr_solvent_combo.setVisible(False)
        nmr_layout.addRow("NMR Solvent:", self.nmr_solvent_combo)

        # GIAO info label
        giao_label = QLabel("ℹ ORCA uses GIAO by default for NMR calculations.")
        giao_label.setStyleSheet("color: #aaa; font-size: 10px; font-style: italic;")
        nmr_layout.addRow("", giao_label)

        self.sep_nmr_widget.setVisible(False)
        left_layout.addWidget(self.sep_nmr_widget)

        # ── Solvent for Opt step ──────────────────────────────────────────────
        opt_solv_lbl = QLabel("Solvent (Geometry Optimization / SP):")
        opt_solv_lbl.setStyleSheet("color: #b0bec5; font-weight: bold;")
        left_layout.addWidget(opt_solv_lbl)

        solv_row = QHBoxLayout()
        self.opt_solvent_model_combo = QComboBox()
        self.opt_solvent_model_combo.addItems(["None (Gas)", "CPCM", "SMD", "PCM", "SCRF"])
        self.opt_solvent_model_combo.setCurrentIndex(0)
        self.opt_solvent_model_combo.currentTextChanged.connect(self._update_opt_solvent_visibility)
        self.opt_solvent_model_combo.currentTextChanged.connect(self.update_preview)
        solv_row.addWidget(QLabel("Model:"))
        solv_row.addWidget(self.opt_solvent_model_combo, 1)

        self.opt_solvent_combo = QComboBox()
        self.opt_solvent_combo.addItems([
            "Chloroform", "Acetone", "Acetonitrile", "Benzene", "DMSO",
            "Dichloromethane", "Ethanol", "Hexane", "Methanol", "THF", "Toluene", "Water"
        ])
        self.opt_solvent_combo.setCurrentText("Chloroform")
        self.opt_solvent_combo.currentTextChanged.connect(self.update_preview)
        self.opt_solvent_combo.setVisible(False)
        solv_row.addWidget(QLabel("Solvent:"))
        solv_row.addWidget(self.opt_solvent_combo, 1)
        left_layout.addLayout(solv_row)

        self.draco_cb = QCheckBox("DRACO Radii (ORCA 6+)")
        self.draco_cb.setStyleSheet("color: #90caf9;")
        self.draco_cb.toggled.connect(self.update_preview)
        left_layout.addWidget(self.draco_cb)

        # Dispersion
        left_layout.addWidget(QLabel("Dispersion Correction:"))
        self.disp_combo = QComboBox()
        self.disp_combo.addItems(["None", "D4", "D3BJ"])
        left_layout.addWidget(self.disp_combo)

        # Charge and Multiplicity
        h_layout = QHBoxLayout()
        v1 = QVBoxLayout()
        v1.addWidget(QLabel("Charge:"))
        self.charge_spin = QSpinBox()
        self.charge_spin.setRange(-5, 5)
        self.charge_spin.setValue(0)
        v1.addWidget(self.charge_spin)
        
        v2 = QVBoxLayout()
        v2.addWidget(QLabel("Multiplicity:"))
        self.multi_spin = QSpinBox()
        self.multi_spin.setRange(1, 10)
        self.multi_spin.setValue(1)
        v2.addWidget(self.multi_spin)
        h_layout.addLayout(v1)
        h_layout.addLayout(v2)
        left_layout.addLayout(h_layout)

        # Resources
        h_layout2 = QHBoxLayout()
        v3 = QVBoxLayout()
        v3.addWidget(QLabel("Cores (pal):"))
        self.cores_spin = QSpinBox()
        self.cores_spin.setRange(1, 64)
        self.cores_spin.setValue(1)
        v3.addWidget(self.cores_spin)
        
        v4 = QVBoxLayout()
        v4.addWidget(QLabel("MaxCore (MB):"))
        self.mem_spin = QSpinBox()
        self.mem_spin.setRange(500, 32000)
        self.mem_spin.setSingleStep(500)
        self.mem_spin.setValue(2000)
        v4.addWidget(self.mem_spin)
        h_layout2.addLayout(v3)
        h_layout2.addLayout(v4)
        left_layout.addLayout(h_layout2)

        # Custom Keywords
        left_layout.addWidget(QLabel("Custom Keywords:"))
        self.custom_kw_input = QLineEdit()
        left_layout.addWidget(self.custom_kw_input)

        left_layout.addStretch()

        # Buttons
        h_btn_layout = QHBoxLayout()
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        self.run_btn = QPushButton("Launch Job")
        self.run_btn.setStyleSheet("background-color: #0078D4; font-weight: bold;")
        self.run_btn.clicked.connect(self.launch_job)
        h_btn_layout.addWidget(self.cancel_btn)
        h_btn_layout.addWidget(self.run_btn)
        left_layout.addLayout(h_btn_layout)

        # Right side: Text Preview
        right_layout.addWidget(QLabel("Input File Preview:"))
        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        right_layout.addWidget(self.preview_text)

        # Splitter or Layout Setup
        left_widget = QWidget()
        left_widget.setLayout(left_layout)
        right_widget = QWidget()
        right_widget.setLayout(right_layout)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        self.layout.addWidget(splitter)

        # Connect slots
        self.name_input.textChanged.connect(self.update_preview)
        self.task_combo.currentTextChanged.connect(self.update_preview)
        self.method_combo.currentTextChanged.connect(self.update_preview)
        self.basis_combo.currentTextChanged.connect(self.update_preview)
        self.sep_nmr_cb.toggled.connect(self.on_sep_nmr_toggled)
        self.nmr_method_combo.currentTextChanged.connect(self.update_preview)
        self.nmr_basis_combo.currentTextChanged.connect(self.update_preview)
        self.disp_combo.currentTextChanged.connect(self.update_preview)
        self.charge_spin.valueChanged.connect(self.update_preview)
        self.multi_spin.valueChanged.connect(self.update_preview)
        self.cores_spin.valueChanged.connect(self.update_preview)
        self.mem_spin.valueChanged.connect(self.update_preview)
        self.custom_kw_input.textChanged.connect(self.update_preview)
        # Run first preview
        self.update_preview()

    def _update_opt_solvent_visibility(self, model_text):
        self.opt_solvent_combo.setVisible(model_text != "None (Gas)")

    def _update_nmr_solvent_visibility(self, model_text):
        self.nmr_solvent_combo.setVisible(model_text != "None (Gas)")

    def _get_solvent_block(self, model_text, solvent_text, use_draco=False, indent=""):
        """Builds a %cpcm block string for the preview / for passing to manager."""
        if model_text == "None (Gas)":
            return ""
        block = f"{indent}%cpcm\n"
        if model_text.upper() == "SMD":
            block += f"{indent}  smd true\n"
            block += f'{indent}  SMDsolvent "{solvent_text}"\n'
        else:
            block += f"{indent}  smd false\n"
            block += f'{indent}  solvent "{solvent_text}"\n'
        if use_draco:
            block += f"{indent}  draco true\n"
        block += f"{indent}end\n"
        return block

    def on_sep_nmr_toggled(self, checked):
        self.sep_nmr_widget.setVisible(checked)
        self.update_preview()

    def update_preview(self):
        task = self.task_combo.currentText()
        has_nmr = "NMR" in task
        has_opt = "Opt" in task

        self.sep_nmr_cb.setVisible(has_nmr and has_opt)
        if not (has_nmr and has_opt):
            self.sep_nmr_widget.setVisible(False)

        use_sep = self.sep_nmr_cb.isChecked() and has_nmr and has_opt
        use_draco = self.draco_cb.isChecked()
        opt_model = self.opt_solvent_model_combo.currentText()
        opt_solv = self.opt_solvent_combo.currentText()
        nmr_model = self.nmr_solvent_model_combo.currentText()
        nmr_solv = self.nmr_solvent_combo.currentText()
        opt_block = self._get_solvent_block(opt_model, opt_solv, use_draco)
        nmr_block = self._get_solvent_block(nmr_model, nmr_solv, use_draco)

        if use_sep:
            geom_m = self.method_combo.currentText()
            geom_b = self.basis_combo.currentText()
            if "None" not in geom_b: geom_b = geom_b.split()[0]
            else: geom_b = ""

            nmr_m = self.nmr_method_combo.currentText()
            nmr_b = self.nmr_basis_combo.currentText().split()[0]
            if "None" in nmr_b: nmr_b = ""

            disp = self.disp_combo.currentText()
            custom = self.custom_kw_input.text().strip()

            geom_kw, geom_block = format_orca_method(geom_m)
            nmr_kw, nmr_block_method = format_orca_method(nmr_m)

            opt_task = "Opt Freq" if "Freq" in task else "Opt"
            opt_kws = [opt_task]
            if geom_kw: opt_kws.append(geom_kw)
            if geom_b: opt_kws.append(geom_b)
            if disp != "None" and not bool(geom_block): opt_kws.append(disp)
            if custom: opt_kws.append(custom)

            nmr_kws = ["NMR"]
            if nmr_kw: nmr_kws.append(nmr_kw)
            if nmr_b: nmr_kws.append(nmr_b)

            should_use_json = False
            if self.job_manager and getattr(self.job_manager, "orca_version", None):
                try:
                    parts = [int(p) for p in self.job_manager.orca_version.split(".")]
                    if len(parts) >= 2 and (parts[0] > 6 or (parts[0] == 6 and parts[1] >= 1)):
                        should_use_json = True
                except:
                    pass

            json_prop_block = "%output\n  JSONPropFile true\nend\n" if should_use_json else ""

            inp = "%Compound\n"
            inp += "  New_Step\n"
            inp += f"    ! {' '.join(opt_kws)}\n"
            if geom_block:
                for bl in geom_block.strip().splitlines():
                    inp += f"    {bl}\n"
            if opt_block:
                for bl in opt_block.splitlines():
                    inp += f"    {bl}\n"
            if json_prop_block:
                for bl in json_prop_block.splitlines():
                    inp += f"    {bl}\n"
            inp += f"    * xyz {self.charge_spin.value()} {self.multi_spin.value()}\n"
            for line in self.xyz_content.strip().splitlines():
                inp += f"      {line}\n"
            inp += "    *\n"
            inp += "  Step_End\n"
            inp += "  New_Step\n"
            inp += f"    ! {' '.join(nmr_kws)}\n"
            if nmr_block_method:
                for bl in nmr_block_method.strip().splitlines():
                    inp += f"    {bl}\n"
            if nmr_block:
                for bl in nmr_block.splitlines():
                    inp += f"    {bl}\n"
            if json_prop_block:
                for bl in json_prop_block.splitlines():
                    inp += f"    {bl}\n"
            inp += "  Step_End\n"
            inp += "End\n"
            inp += f"%maxcore {self.mem_spin.value()}\n"
            if self.cores_spin.value() > 1:
                inp += f"%pal\n  nprocs {self.cores_spin.value()}\nend\n"
        else:
            single_kw, single_block = format_orca_method(self.method_combo.currentText())
            kws = []
            if task == "Single Point (SP)": task = "SP"
            kws.append(task)
            if single_kw:
                kws.append(single_kw)

            basis = self.basis_combo.currentText()
            if "None" not in basis:
                kws.append(basis.split()[0])

            disp = self.disp_combo.currentText()
            if disp != "None" and not has_nmr and not bool(single_block):
                kws.append(disp)

            custom = self.custom_kw_input.text().strip()
            if custom:
                kws.append(custom)

            # For single-step, use NMR block for NMR tasks, otherwise Opt block
            active_block = nmr_block if has_nmr else opt_block
            if has_nmr and not nmr_block:
                active_block = opt_block

            should_use_json = False
            if self.job_manager and getattr(self.job_manager, "orca_version", None):
                try:
                    parts = [int(p) for p in self.job_manager.orca_version.split(".")]
                    if len(parts) >= 2 and (parts[0] > 6 or (parts[0] == 6 and parts[1] >= 1)):
                        should_use_json = True
                except:
                    pass

            json_prop_block = "%output\n  JSONPropFile true\nend\n" if should_use_json else ""

            inp = f"! {' '.join(kws)}\n"
            inp += f"%maxcore {self.mem_spin.value()}\n"
            if self.cores_spin.value() > 1:
                inp += f"%pal\n  nprocs {self.cores_spin.value()}\nend\n"
            if single_block:
                inp += single_block
            if json_prop_block:
                inp += json_prop_block
            if active_block:
                inp += active_block
            inp += f"\n* xyz {self.charge_spin.value()} {self.multi_spin.value()}\n"
            inp += self.xyz_content.strip() + "\n"
            inp += "*\n"

        self.preview_text.setText(inp)

    def launch_job(self):
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Invalid Name", "Please enter a valid job name.")
            return

        task = self.task_combo.currentText()
        if task == "Single Point (SP)": task = "SP"
        
        basis = self.basis_combo.currentText().split()[0]
        if "None" in basis:
            basis = ""

        use_sep = self.sep_nmr_cb.isChecked() and ("NMR" in task) and ("Opt" in task)
        nmr_m = self.nmr_method_combo.currentText()
        nmr_b = self.nmr_basis_combo.currentText().split()[0]

        # --- PRE-FLIGHT CHECKS ---
        charge = self.charge_spin.value()
        multiplicity = self.multi_spin.value()
        is_valid, expected_desc, correct_mult = self.job_manager.validate_spin_multiplicity(
            self.xyz_content, charge, multiplicity
        )
        if not is_valid:
            msgBox = QMessageBox(self)
            msgBox.setIcon(QMessageBox.Warning)
            msgBox.setWindowTitle("Spin Multiplicity Warning")
            msgBox.setText(
                f"The combination of charge ({charge}) and multiplicity ({multiplicity}) might be physically invalid.\n"
                f"Based on the electron count, the multiplicity should be {expected_desc}."
            )
            msgBox.setInformativeText(f"Do you want to correct the multiplicity to {correct_mult}?")
            btn_correct = msgBox.addButton("Correct to " + str(correct_mult), QMessageBox.YesRole)
            btn_ignore = msgBox.addButton("Ignore and Run", QMessageBox.NoRole)
            btn_cancel = msgBox.addButton("Cancel", QMessageBox.RejectRole)
            msgBox.exec_()
            
            if msgBox.clickedButton() == btn_correct:
                self.multi_spin.setValue(correct_mult)
                multiplicity = correct_mult
            elif msgBox.clickedButton() == btn_cancel:
                return

        # Heavy Elements Check
        has_heavy = False
        try:
            from rdkit import Chem
            pt = Chem.GetPeriodicTable()
        except ImportError:
            pt = None
            
        for line in self.xyz_content.strip().split("\n"):
            parts = line.split()
            if parts:
                sym = parts[0].capitalize()
                z = 0
                if pt:
                    try: z = pt.GetAtomicNumber(sym)
                    except: pass
                else:
                    if sym not in ["H", "He", "Li", "Be", "B", "C", "N", "O", "F", "Ne", "Na", "Mg", "Al", "Si", "P", "S", "Cl", "Ar", "K", "Ca"]:
                        has_heavy = True
                        break
                if z > 20:
                    has_heavy = True
                    break
                    
        if has_heavy and basis.startswith("6-31"):
            reply = QMessageBox.warning(
                self,
                "Heavy Elements Warning",
                "Your molecule contains transition metals or heavy elements (Z > 20), "
                "but you have selected a Pople basis set (6-31G). Pople basis sets are "
                "often not defined or highly inaccurate for these elements.\n\n"
                "It is strongly recommended to use Ahlrichs basis sets (e.g. def2-SVP or def2-TZVP).\n\n"
                "Do you want to abort to change the basis set?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                return

        import shutil
        if not shutil.which("orca"):
            reply = QMessageBox.question(
                self,
                "ORCA Not Found",
                "The 'orca' executable was not found on your system's PATH.\n"
                "You can still create the job files, but starting the job will fail "
                "unless ORCA is correctly set up.\n\n"
                "Do you want to create the job anyway?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.No:
                return

        # Collect solvent settings
        opt_model_text = self.opt_solvent_model_combo.currentText()
        nmr_model_text = self.nmr_solvent_model_combo.currentText()
        # Map display labels to manager model strings
        def _map_model(txt):
            if txt == "None (Gas)": return "None"
            return txt  # "CPCM", "SMD", "PCM"

        # Create job
        job_id = self.job_manager.create_job(
            name=name,
            xyz_content=self.xyz_content,
            charge=charge,
            multiplicity=multiplicity,
            task=task,
            method=self.method_combo.currentText(),
            basis=basis,
            dispersion=self.disp_combo.currentText(),
            nprocs=self.cores_spin.value(),
            maxcore=self.mem_spin.value(),
            custom_keywords=self.custom_kw_input.text().strip(),
            use_sep_nmr=use_sep,
            nmr_method=nmr_m,
            nmr_basis=nmr_b,
            opt_solvent_model=_map_model(opt_model_text),
            opt_solvent=self.opt_solvent_combo.currentText(),
            nmr_solvent_model=_map_model(nmr_model_text),
            nmr_solvent=self.nmr_solvent_combo.currentText(),
            use_draco=self.draco_cb.isChecked()
        )

        # Start job
        success = self.job_manager.start_job(job_id)
        if success:
            QMessageBox.information(self, "Job Started", f"ORCA job '{name}' was started successfully.")
            self.accept()
        else:
            QMessageBox.critical(self, "Job Start Failed", "Failed to start ORCA process. Check path settings.")



class LogViewerDialog(QDialog):
    def __init__(self, parent, job_id, job_manager):
        super().__init__(parent)
        self.setWindowTitle(f"Log Viewer - {job_id}")
        self.resize(800, 600)
        self.setStyleSheet("QDialog { background-color: #1e1e1e; }")
        
        layout = QVBoxLayout(self)
        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setStyleSheet("background-color: #111; color: #ddd; font-family: 'Consolas';")
        layout.addWidget(self.text_edit)

        self.job_id = job_id
        self.job_manager = job_manager
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.load_log)
        self.timer.start(1000)
        self.load_log()

    def load_log(self):
        log_file = os.path.join(self.job_manager.get_job_dir(self.job_id), "orca_output.out")
        if os.path.exists(log_file):
            try:
                with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                    # Load only last 1000 lines for performance
                    lines = f.readlines()
                    text = "".join(lines[-1000:])
                    
                # Only update and scroll if text has actually changed
                if self.text_edit.toPlainText() != text:
                    scrollbar = self.text_edit.verticalScrollBar()
                    scroll_pos = scrollbar.value()
                    at_bottom = scroll_pos >= scrollbar.maximum() - 15
                    
                    self.text_edit.setPlainText(text)
                    
                    if at_bottom:
                        scrollbar.setValue(scrollbar.maximum())
                    else:
                        scrollbar.setValue(scroll_pos)
            except Exception as e:
                self.text_edit.setPlainText(f"Error loading log: {e}")


class TMSEditDialog(QDialog):
    """Dialog to add or edit a single TMS reference entry."""
    def __init__(self, entry=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit TMS Reference Value" if entry else "Add New TMS Reference Value")
        self.resize(450, 420)
        self.entry = entry or {}
        
        layout = QVBoxLayout(self)
        form = QFormLayout()
        
        self.geom_method_input = QLineEdit(str(self.entry.get("geom_method", "-")))
        self.geom_basis_input = QLineEdit(str(self.entry.get("geom_basis", "-")))
        self.geom_solvent_input = QLineEdit(str(self.entry.get("geom_solvent", "-")))
        self.method_input = QLineEdit(str(self.entry.get("method", "")))
        self.basis_input = QLineEdit(str(self.entry.get("basis", "")))
        self.nmr_solvent_input = QLineEdit(str(self.entry.get("nmr_solvent", "-")))
        self.solvent_model_input = QLineEdit(str(self.entry.get("solvent_model", "-")))
        
        h1 = self.entry.get("h1_shielding")
        self.h1_input = QLineEdit("" if h1 is None else str(h1))
        
        c13 = self.entry.get("c13_shielding")
        self.c13_input = QLineEdit("" if c13 is None else str(c13))
        
        self.source_input = QLineEdit(str(self.entry.get("source", "")))
        
        form.addRow("Geometry Method:", self.geom_method_input)
        form.addRow("Geometry Basis Set:", self.geom_basis_input)
        form.addRow("Geometry Solvent:", self.geom_solvent_input)
        form.addRow("NMR Method:", self.method_input)
        form.addRow("NMR Basis Set:", self.basis_input)
        form.addRow("NMR Solvent:", self.nmr_solvent_input)
        form.addRow("Solvent Model:", self.solvent_model_input)
        form.addRow("1H Shielding (ppm):", self.h1_input)
        form.addRow("13C Shielding (ppm):", self.c13_input)
        form.addRow("Source / Reference:", self.source_input)
        
        layout.addLayout(form)
        
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    def get_data(self):
        def parse_float(val_str):
            val_str = str(val_str).strip().replace(",", ".")
            if not val_str or val_str.lower() in ["n/a", "-", "none"]:
                return None
            try:
                return float(val_str)
            except ValueError:
                return None

        return {
            "geom_method": self.geom_method_input.text().strip() or "-",
            "geom_basis": self.geom_basis_input.text().strip() or "-",
            "geom_solvent": self.geom_solvent_input.text().strip() or "-",
            "method": self.method_input.text().strip() or "-",
            "basis": self.basis_input.text().strip() or "-",
            "nmr_solvent": self.nmr_solvent_input.text().strip() or "-",
            "solvent_model": self.solvent_model_input.text().strip() or "-",
            "h1_shielding": parse_float(self.h1_input.text()),
            "c13_shielding": parse_float(self.c13_input.text()),
            "source": self.source_input.text().strip() or "-"
        }


class TMSReferenceDialog(QDialog):
    """Dialog displaying complete TMS reference table with filter and editing options."""
    def __init__(self, workspace_dir=None, current_method=None, current_basis=None, parent=None,
                 geom_method=None, geom_basis=None, geom_solvent=None, nmr_solvent=None, solvent_model=None):
        super().__init__(parent)
        self.setWindowTitle("TMS Reference Shielding Constants")
        self.resize(1100, 520)
        self.workspace_dir = workspace_dir
        self.tms_list = load_tms_references(workspace_dir)
        self.selected_ref = None
        
        self.current_method = current_method
        self.current_basis = current_basis
        self.geom_method = geom_method
        self.geom_basis = geom_basis
        self.geom_solvent = geom_solvent
        self.nmr_solvent = nmr_solvent
        self.solvent_model = solvent_model

        layout = QVBoxLayout(self)
        
        # Search & Filter
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Search / Filter:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("e.g. B3LYP, HF, 6-31G*, Chloroform, CPCM...")
        self.search_input.textChanged.connect(self.populate_table)
        filter_layout.addWidget(self.search_input)
        
        if current_method or current_basis:
            match = find_best_tms_match(
                current_method or "", current_basis or "", 
                geom_method=geom_method, geom_basis=geom_basis, 
                tms_list=self.tms_list,
                geom_solvent=geom_solvent, nmr_solvent=nmr_solvent, solvent_model=solvent_model
            )
            if match:
                h1_m = match.get('h1_shielding')
                c13_m = match.get('c13_shielding')
                h1_str = f"{h1_m:.4f}" if isinstance(h1_m, (int, float)) else "n/a"
                c13_str = f"{c13_m:.4f}" if isinstance(c13_m, (int, float)) else "n/a"
                info_lbl = QLabel(f"<b>Recommended: 1H={h1_str}, 13C={c13_str}</b>")
                info_lbl.setStyleSheet("color: #4fc3f7; margin-left: 10px;")
                filter_layout.addWidget(info_lbl)
                
        layout.addLayout(filter_layout)
        
        # Table
        self.table = QTableWidget(0, 10)
        self.table.setHorizontalHeaderLabels([
            "Geometry Method", "Geometry Basis Set", "Geometry Solvent",
            "NMR Method", "NMR Basis Set", "NMR Solvent", "Solvent Model",
            "1H Shielding (ppm)", "13C Shielding (ppm)", "Source"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.doubleClicked.connect(self.apply_selected)
        layout.addWidget(self.table)
        
        # Action Buttons
        btn_layout = QHBoxLayout()
        
        self.btn_apply = QPushButton("Apply Values")
        self.btn_apply.setStyleSheet("font-weight: bold; background-color: #2e7d32; color: white;")
        self.btn_apply.clicked.connect(self.apply_selected)
        
        self.btn_add = QPushButton("Add...")
        self.btn_add.clicked.connect(self.add_entry)
        
        self.btn_edit = QPushButton("Edit...")
        self.btn_edit.clicked.connect(self.edit_entry)
        
        self.btn_delete = QPushButton("Delete")
        self.btn_delete.clicked.connect(self.delete_entry)
        
        self.btn_reset = QPushButton("Reset to Default")
        self.btn_reset.setToolTip("Restores original default table")
        self.btn_reset.clicked.connect(self.reset_to_default)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.reject)
        
        btn_layout.addWidget(self.btn_apply)
        btn_layout.addWidget(self.btn_add)
        btn_layout.addWidget(self.btn_edit)
        btn_layout.addWidget(self.btn_delete)
        btn_layout.addWidget(self.btn_reset)
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        
        layout.addLayout(btn_layout)
        
        self.populate_table()
        
        # Highlight match if current_method / current_basis provided
        if current_method or current_basis:
            self.highlight_match(
                current_method, current_basis, 
                geom_method=geom_method, geom_basis=geom_basis, 
                geom_solvent=geom_solvent, nmr_solvent=nmr_solvent, solvent_model=solvent_model
            )

    def populate_table(self):
        filter_text = self.search_input.text().strip().lower()
        self.table.setRowCount(0)
        
        for idx, entry in enumerate(self.tms_list):
            row_str = " ".join([
                str(entry.get("geom_method", "")),
                str(entry.get("geom_basis", "")),
                str(entry.get("geom_solvent", "")),
                str(entry.get("method", "")),
                str(entry.get("basis", "")),
                str(entry.get("nmr_solvent", "")),
                str(entry.get("solvent_model", "")),
                str(entry.get("source", ""))
            ]).lower()
            
            if filter_text and filter_text not in row_str:
                continue
                
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            self.table.setItem(row, 0, QTableWidgetItem(str(entry.get("geom_method", "-"))))
            self.table.setItem(row, 1, QTableWidgetItem(str(entry.get("geom_basis", "-"))))
            self.table.setItem(row, 2, QTableWidgetItem(str(entry.get("geom_solvent", "-"))))
            self.table.setItem(row, 3, QTableWidgetItem(str(entry.get("method", "-"))))
            self.table.setItem(row, 4, QTableWidgetItem(str(entry.get("basis", "-"))))
            self.table.setItem(row, 5, QTableWidgetItem(str(entry.get("nmr_solvent", "-"))))
            self.table.setItem(row, 6, QTableWidgetItem(str(entry.get("solvent_model", "-"))))
            
            h1 = entry.get("h1_shielding")
            h1_str = f"{h1:.4f}" if isinstance(h1, (int, float)) else "n/a"
            self.table.setItem(row, 7, QTableWidgetItem(h1_str))
            
            c13 = entry.get("c13_shielding")
            c13_str = f"{c13:.4f}" if isinstance(c13, (int, float)) else "n/a"
            self.table.setItem(row, 8, QTableWidgetItem(c13_str))
            
            self.table.setItem(row, 9, QTableWidgetItem(str(entry.get("source", "-"))))
            
            # Attach index into original tms_list as UserRole on item
            self.table.item(row, 0).setData(Qt.UserRole, idx)

    def highlight_match(self, method, basis, geom_method=None, geom_basis=None,
                        geom_solvent=None, nmr_solvent=None, solvent_model=None):
        match = find_best_tms_match(
            method, basis, 
            geom_method=geom_method, geom_basis=geom_basis, 
            tms_list=self.tms_list,
            geom_solvent=geom_solvent, nmr_solvent=nmr_solvent, solvent_model=solvent_model
        )
        if not match:
            return
        try:
            match_idx = self.tms_list.index(match)
            for r in range(self.table.rowCount()):
                idx = self.table.item(r, 0).data(Qt.UserRole)
                if idx == match_idx:
                    self.table.selectRow(r)
        except ValueError:
            pass

    def get_selected_tms_index(self):
        row = self.table.currentRow()
        if row >= 0:
            item = self.table.item(row, 0)
            if item:
                return item.data(Qt.UserRole)
        return None

    def apply_selected(self):
        idx = self.get_selected_tms_index()
        if idx is not None and 0 <= idx < len(self.tms_list):
            entry = self.tms_list[idx]
            self.selected_ref = (entry.get("h1_shielding"), entry.get("c13_shielding"))
            self.accept()
        else:
            QMessageBox.information(self, "Information", "Please select a row from the table first.")

    def add_entry(self):
        dlg = TMSEditDialog(parent=self)
        if dlg.exec_() == QDialog.Accepted:
            new_data = dlg.get_data()
            self.tms_list.append(new_data)
            save_tms_references(self.tms_list, self.workspace_dir)
            self.populate_table()

    def edit_entry(self):
        idx = self.get_selected_tms_index()
        if idx is None or not (0 <= idx < len(self.tms_list)):
            QMessageBox.information(self, "Information", "Please select a row to edit.")
            return
        dlg = TMSEditDialog(entry=self.tms_list[idx], parent=self)
        if dlg.exec_() == QDialog.Accepted:
            self.tms_list[idx] = dlg.get_data()
            save_tms_references(self.tms_list, self.workspace_dir)
            self.populate_table()

    def delete_entry(self):
        idx = self.get_selected_tms_index()
        if idx is None or not (0 <= idx < len(self.tms_list)):
            QMessageBox.information(self, "Information", "Please select a row to delete.")
            return
        reply = QMessageBox.question(
            self, "Confirm Delete",
            "Are you sure you want to delete this reference entry?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            del self.tms_list[idx]
            save_tms_references(self.tms_list, self.workspace_dir)
            self.populate_table()

    def reset_to_default(self):
        reply = QMessageBox.question(
            self, "Confirm Reset",
            "Do you want to reset all TMS reference values to default?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.tms_list = [dict(e) for e in DEFAULT_TMS_REFERENCES]
            save_tms_references(self.tms_list, self.workspace_dir)
            self.populate_table()


class TantilloEditDialog(QDialog):
    """Dialog to add or edit a single Tantillo scaling entry."""
    def __init__(self, entry=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Tantillo Scaling Entry" if entry else "Add New Tantillo Scaling Entry")
        self.resize(520, 460)
        self.entry = entry or {}

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.geom_method_input = QLineEdit(str(self.entry.get("geom_method", "-")))
        self.geom_basis_input = QLineEdit(str(self.entry.get("geom_basis", "-")))

        geom_solvent_val = self.entry.get("geom_solvent", "Gas")
        self.geom_solvent_input = QLineEdit(str(geom_solvent_val) if geom_solvent_val else "Gas")

        self.method_input = QLineEdit(str(self.entry.get("method", "")))
        self.basis_input = QLineEdit(str(self.entry.get("basis", "")))

        nmr_solvent_val = self.entry.get("nmr_solvent", "Gas")
        self.nmr_solvent_input = QLineEdit(str(nmr_solvent_val) if nmr_solvent_val else "Gas")

        solvent_model_val = self.entry.get("solvent_model") or ""
        self.solvent_model_combo = QComboBox()
        self.solvent_model_combo.addItems(["", "SMD", "CPCM", "PCM", "SCRF"])
        if solvent_model_val in ["", "SMD", "CPCM", "PCM", "SCRF"]:
            self.solvent_model_combo.setCurrentText(solvent_model_val)

        h1_s = self.entry.get("h1_slope")
        self.h1_slope_input = QLineEdit("" if h1_s is None else str(h1_s))

        h1_i = self.entry.get("h1_intercept")
        self.h1_intercept_input = QLineEdit("" if h1_i is None else str(h1_i))

        c13_s = self.entry.get("c13_slope")
        self.c13_slope_input = QLineEdit("" if c13_s is None else str(c13_s))

        c13_i = self.entry.get("c13_intercept")
        self.c13_intercept_input = QLineEdit("" if c13_i is None else str(c13_i))

        self.source_input = QLineEdit(str(self.entry.get("source", "CHESHIRE")))

        form.addRow("Geometry Method:", self.geom_method_input)
        form.addRow("Geometry Basis Set:", self.geom_basis_input)
        form.addRow("Geom. Solvent:", self.geom_solvent_input)
        form.addRow("NMR Method:", self.method_input)
        form.addRow("NMR Basis Set:", self.basis_input)
        form.addRow("NMR Solvent:", self.nmr_solvent_input)
        form.addRow("Solvent Model:", self.solvent_model_combo)
        form.addRow("1H Slope:", self.h1_slope_input)
        form.addRow("1H Intercept:", self.h1_intercept_input)
        form.addRow("13C Slope:", self.c13_slope_input)
        form.addRow("13C Intercept:", self.c13_intercept_input)
        form.addRow("Source / Note:", self.source_input)

        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    def get_data(self):
        def parse_float(val_str):
            val_str = str(val_str).strip().replace(",", ".")
            if not val_str or val_str.lower() in ["n/a", "-", "none"]:
                return None
            try:
                return float(val_str)
            except ValueError:
                return None

        solvent_model = self.solvent_model_combo.currentText().strip() or None
        return {
            "geom_method": self.geom_method_input.text().strip() or "-",
            "geom_basis": self.geom_basis_input.text().strip() or "-",
            "geom_solvent": self.geom_solvent_input.text().strip() or "Gas",
            "method": self.method_input.text().strip() or "-",
            "basis": self.basis_input.text().strip() or "-",
            "nmr_solvent": self.nmr_solvent_input.text().strip() or "Gas",
            "solvent_model": solvent_model,
            "h1_slope": parse_float(self.h1_slope_input.text()),
            "h1_intercept": parse_float(self.h1_intercept_input.text()),
            "c13_slope": parse_float(self.c13_slope_input.text()),
            "c13_intercept": parse_float(self.c13_intercept_input.text()),
            "source": self.source_input.text().strip() or "-"
        }


class TantilloReferenceDialog(QDialog):
    """Dialog displaying complete Tantillo scaling table with filter and editing options."""
    def __init__(self, workspace_dir=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Tantillo Scaling Factors (NMR Shift Scaling)")
        self.resize(1000, 520)
        self.workspace_dir = workspace_dir
        self.tantillo_list = load_tantillo_scaling(workspace_dir)
        
        layout = QVBoxLayout(self)
        
        # Search & Filter
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Search / Filter:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("e.g. B3LYP, M06-2X, MP2, 6-31G(d), 6-311+G(2d,p)...")
        self.search_input.textChanged.connect(self.populate_table)
        filter_layout.addWidget(self.search_input)
        layout.addLayout(filter_layout)
        
        # Table – 12 columns
        self.table = QTableWidget(0, 12)
        self.table.setHorizontalHeaderLabels([
            "Geom. Method", "Geom. Basis", "Geom. Solvent",
            "NMR Method", "NMR Basis", "NMR Solvent", "Model",
            "1H Slope", "1H Intercept", "13C Slope", "13C Intercept", "Source"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        layout.addWidget(self.table)
        
        # Action Buttons
        btn_layout = QHBoxLayout()
        
        self.btn_add = QPushButton("Add...")
        self.btn_add.clicked.connect(self.add_entry)
        
        self.btn_edit = QPushButton("Edit...")
        self.btn_edit.clicked.connect(self.edit_entry)
        
        self.btn_delete = QPushButton("Delete")
        self.btn_delete.clicked.connect(self.delete_entry)
        
        self.btn_reset = QPushButton("Reset to Default")
        self.btn_reset.setToolTip("Restores original default table")
        self.btn_reset.clicked.connect(self.reset_to_default)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        
        btn_layout.addWidget(self.btn_add)
        btn_layout.addWidget(self.btn_edit)
        btn_layout.addWidget(self.btn_delete)
        btn_layout.addWidget(self.btn_reset)
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        
        layout.addLayout(btn_layout)
        self.populate_table()

    def populate_table(self):
        filter_text = self.search_input.text().strip().lower()
        self.table.setRowCount(0)

        for idx, entry in enumerate(self.tantillo_list):
            solvent_model = entry.get("solvent_model") or ""
            geom_solvent = entry.get("geom_solvent", "Gas") or "Gas"
            nmr_solvent = entry.get("nmr_solvent", "Gas") or "Gas"
            row_str = " ".join([
                str(entry.get("geom_method", "")),
                str(entry.get("geom_basis", "")),
                geom_solvent,
                str(entry.get("method", "")),
                str(entry.get("basis", "")),
                nmr_solvent,
                str(solvent_model),
                str(entry.get("source", ""))
            ]).lower()

            if filter_text and filter_text not in row_str:
                continue

            row = self.table.rowCount()
            self.table.insertRow(row)

            self.table.setItem(row, 0, QTableWidgetItem(str(entry.get("geom_method", "-"))))
            self.table.setItem(row, 1, QTableWidgetItem(str(entry.get("geom_basis", "-"))))
            self.table.setItem(row, 2, QTableWidgetItem(geom_solvent))
            self.table.setItem(row, 3, QTableWidgetItem(str(entry.get("method", "-"))))
            self.table.setItem(row, 4, QTableWidgetItem(str(entry.get("basis", "-"))))
            self.table.setItem(row, 5, QTableWidgetItem(nmr_solvent))
            self.table.setItem(row, 6, QTableWidgetItem(str(solvent_model)))

            h1_s = entry.get("h1_slope")
            self.table.setItem(row, 7, QTableWidgetItem(f"{h1_s:.4f}" if isinstance(h1_s, (int, float)) else "n/a"))

            h1_i = entry.get("h1_intercept")
            self.table.setItem(row, 8, QTableWidgetItem(f"{h1_i:.4f}" if isinstance(h1_i, (int, float)) else "n/a"))

            c13_s = entry.get("c13_slope")
            self.table.setItem(row, 9, QTableWidgetItem(f"{c13_s:.4f}" if isinstance(c13_s, (int, float)) else "n/a"))

            c13_i = entry.get("c13_intercept")
            self.table.setItem(row, 10, QTableWidgetItem(f"{c13_i:.4f}" if isinstance(c13_i, (int, float)) else "n/a"))

            self.table.setItem(row, 11, QTableWidgetItem(str(entry.get("source", "-"))))

            # Attach index into original tantillo_list as UserRole on col-0 item
            self.table.item(row, 0).setData(Qt.UserRole, idx)

    def get_selected_tantillo_index(self):
        row = self.table.currentRow()
        if row >= 0:
            item = self.table.item(row, 0)
            if item:
                return item.data(Qt.UserRole)
        return None

    def add_entry(self):
        dlg = TantilloEditDialog(parent=self)
        if dlg.exec_() == QDialog.Accepted:
            new_data = dlg.get_data()
            self.tantillo_list.append(new_data)
            save_tantillo_scaling(self.tantillo_list, self.workspace_dir)
            self.populate_table()

    def edit_entry(self):
        idx = self.get_selected_tantillo_index()
        if idx is None or not (0 <= idx < len(self.tantillo_list)):
            QMessageBox.information(self, "Information", "Please select a row to edit.")
            return
        dlg = TantilloEditDialog(entry=self.tantillo_list[idx], parent=self)
        if dlg.exec_() == QDialog.Accepted:
            self.tantillo_list[idx] = dlg.get_data()
            save_tantillo_scaling(self.tantillo_list, self.workspace_dir)
            self.populate_table()

    def delete_entry(self):
        idx = self.get_selected_tantillo_index()
        if idx is None or not (0 <= idx < len(self.tantillo_list)):
            QMessageBox.information(self, "Information", "Please select a row to delete.")
            return
        reply = QMessageBox.question(
            self, "Confirm Delete",
            "Are you sure you want to delete this scaling entry?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            del self.tantillo_list[idx]
            save_tantillo_scaling(self.tantillo_list, self.workspace_dir)
            self.populate_table()

    def reset_to_default(self):
        reply = QMessageBox.question(
            self, "Confirm Reset",
            "Do you want to reset all Tantillo scaling factors to default?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.tantillo_list = [dict(e) for e in DEFAULT_TANTILLO_SCALING]
            save_tantillo_scaling(self.tantillo_list, self.workspace_dir)
            self.populate_table()


def calculate_symmetry_ranks(mol):
    from collections import defaultdict as _defaultdict
    from rdkit import Chem
    from rdkit.Chem import AllChem

    Chem.AssignStereochemistry(mol, cleanIt=True, force=True)
    base_ranks = list(Chem.CanonicalRankAtoms(mol, breakTies=False, includeChirality=True))
    num_at = mol.GetNumAtoms()

    # 1. Find rotatable bonds (single, non-ring, between non-terminal heavy atoms)
    rot_smarts = Chem.MolFromSmarts('[!D1]-&!@[!D1]')
    rot_matches = mol.GetSubstructMatches(rot_smarts)
    rot_bonds = [mol.GetBondBetweenAtoms(a, b).GetIdx() for a, b in rot_matches]

    # 2. Cut molecule into rigid fragments
    if rot_bonds:
        frags_mol = Chem.FragmentOnBonds(mol, rot_bonds)
    else:
        frags_mol = Chem.Mol(mol)

    frag_indices = Chem.GetMolFrags(frags_mol, asMols=False)
    frags_mols   = Chem.GetMolFrags(frags_mol, asMols=True, sanitizeFrags=False)

    # 3. Compute idealized 2D coords for each fragment
    frag_confs = []
    for frag in frags_mols:
        try:
            AllChem.Compute2DCoords(frag)
            frag_confs.append(frag.GetConformer())
        except Exception:
            frag_confs.append(None)

    # 4. Group atoms by topological base rank, then refine via fragment geometry
    rank_groups = _defaultdict(list)
    for i, r in enumerate(base_ranks):
        rank_groups[r].append(i)

    sym_ranks  = [-1] * num_at
    next_rank  = 0

    for r in sorted(rank_groups.keys()):
        atoms = rank_groups[r]
        if len(atoms) == 1:
            sym_ranks[atoms[0]] = next_rank
            next_rank += 1
            continue

        # Build distance-profile signature for each atom within its fragment
        signatures = {}
        for a_idx in atoms:
            for f_idx, f_atoms in enumerate(frag_indices):
                if a_idx in f_atoms:
                    frag_mol   = frags_mols[f_idx]
                    conf       = frag_confs[f_idx]
                    local_idx  = f_atoms.index(a_idx)
                    if conf is not None:
                        pos   = conf.GetAtomPosition(local_idx)
                        dists = tuple(sorted(
                            round(pos.Distance(conf.GetAtomPosition(k)), 3)
                            for k in range(frag_mol.GetNumAtoms())
                        ))
                        signatures[a_idx] = dists
                    else:
                        signatures[a_idx] = (0,)
                    break

        # Group by signature, assign ranks deterministically
        sig_groups = _defaultdict(list)
        for a_idx, sig in signatures.items():
            sig_groups[sig].append(a_idx)

        for sig in sorted(sig_groups.keys()):
            for a_idx in sig_groups[sig]:
                sym_ranks[a_idx] = next_rank
            next_rank += 1
            
    return sym_ranks


import glob
import subprocess

def parse_orbitals(out_file_path):
    """Parses orbital energies from ORCA output file.
    Returns:
        orbitals: list of dicts with keys 'num', 'occ', 'energy_eh', 'energy_ev', 'is_homo', 'is_lumo'
        homo_idx: int index of HOMO, or -1
        lumo_idx: int index of LUMO, or -1
    """
    orbitals = []
    homo_idx = -1
    lumo_idx = -1
    
    if not os.path.exists(out_file_path):
        return orbitals, homo_idx, lumo_idx
        
    try:
        with open(out_file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except Exception as e:
        print("Error reading ORCA output for orbitals:", e)
        return orbitals, homo_idx, lumo_idx
        
    # Find orbital energy block.
    match = re.search(r"ORBITAL\s+ENERGIES\s*\n\s*-+\s*\n\s*NO\s+OCC", content, re.IGNORECASE)
    if not match:
        match = re.search(r"NO\s+OCC\s+E\(Eh\)\s+E\(eV\)", content, re.IGNORECASE)
        
    if match:
        start_idx = match.end()
        lines = content[start_idx:].splitlines()
        for line in lines:
            line = line.strip()
            if not line:
                if orbitals: # end of block
                    break
                continue
            parts = line.split()
            if len(parts) >= 4:
                try:
                    num = int(parts[0])
                    occ = float(parts[1])
                    energy_eh = float(parts[2])
                    energy_ev = float(parts[3])
                    orbitals.append({
                        "num": num,
                        "occ": occ,
                        "energy_eh": energy_eh,
                        "energy_ev": energy_ev,
                        "is_homo": False,
                        "is_lumo": False
                    })
                except ValueError:
                    if orbitals:
                        break
                    
    # Identify HOMO and LUMO
    if orbitals:
        last_occupied = -1
        for i, orb in enumerate(orbitals):
            if orb["occ"] > 0.05:
                last_occupied = i
        
        if last_occupied != -1:
            orbitals[last_occupied]["is_homo"] = True
            homo_idx = orbitals[last_occupied]["num"]
            
            if last_occupied + 1 < len(orbitals):
                orbitals[last_occupied + 1]["is_lumo"] = True
                lumo_idx = orbitals[last_occupied + 1]["num"]
                
    return orbitals, homo_idx, lumo_idx


def generate_orbital_cube(job_dir, orca_plot_exe, orbital_num):
    """Runs orca_plot non-interactively to generate a cube file for the specified orbital."""
    for f in glob.glob(os.path.join(job_dir, f"*mo{orbital_num}a*.cube")):
        try: os.remove(f)
        except: pass
        
    gbw_file = "orca_input.gbw"
    if not os.path.exists(os.path.join(job_dir, gbw_file)):
        return None, "orca_input.gbw not found in job directory."
        
    creationflags = 0
    if sys.platform == "win32":
        creationflags = subprocess.CREATE_NO_WINDOW
        
    try:
        proc = subprocess.Popen(
            [orca_plot_exe, gbw_file, "-i"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=job_dir,
            text=True,
            creationflags=creationflags
        )
        
        # Parse menu options dynamically to support both ORCA 5 and ORCA 6
        plot_option = None
        exit_option = None
        init_output = []
        
        while True:
            line = proc.stdout.readline()
            if not line:
                break
            init_output.append(line)
            if "Generate the plot" in line:
                parts = line.strip().split("-")
                if parts:
                    plot_option = parts[0].strip()
            if "exit this program" in line or "Exit" in line:
                parts = line.strip().split("-")
                if parts:
                    exit_option = parts[0].strip()
            if plot_option and exit_option:
                break
                
        if not plot_option: plot_option = "11"
        if not exit_option: exit_option = "12"
        
        commands = f"1\n1\n2\n{orbital_num}\n3\n0\n4\n40\n5\n7\n{plot_option}\n{exit_option}\n"
        stdout, stderr = proc.communicate(input=commands, timeout=30)
        full_output = "".join(init_output) + (stdout or "") + (stderr or "")
    except Exception as e:
        print("Failed running orca_plot for orbital:", e)
        return None, str(e)
        
    matching_files = glob.glob(os.path.join(job_dir, f"*mo{orbital_num}a*.cube"))
    if matching_files:
        return matching_files[0], ""
    return None, full_output


def generate_density_cube(job_dir, orca_plot_exe):
    """Runs orca_plot non-interactively to generate a cube file for electron density."""
    for f in glob.glob(os.path.join(job_dir, "*dens*.cube")):
        try: os.remove(f)
        except: pass
        
    gbw_file = "orca_input.gbw"
    if not os.path.exists(os.path.join(job_dir, gbw_file)):
        return None, "orca_input.gbw not found in job directory."
        
    creationflags = 0
    if sys.platform == "win32":
        creationflags = subprocess.CREATE_NO_WINDOW
        
    try:
        proc = subprocess.Popen(
            [orca_plot_exe, gbw_file, "-i"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=job_dir,
            text=True,
            creationflags=creationflags
        )
        
        plot_option = None
        exit_option = None
        init_output = []
        
        while True:
            line = proc.stdout.readline()
            if not line:
                break
            init_output.append(line)
            if "Generate the plot" in line:
                parts = line.strip().split("-")
                if parts:
                    plot_option = parts[0].strip()
            if "exit this program" in line or "Exit" in line:
                parts = line.strip().split("-")
                if parts:
                    exit_option = parts[0].strip()
            if plot_option and exit_option:
                break
                
        if not plot_option: plot_option = "11"
        if not exit_option: exit_option = "12"
        
        commands = f"1\n2\nn\n4\n40\n5\n7\n{plot_option}\n{exit_option}\n"
        stdout, stderr = proc.communicate(input=commands, timeout=30)
        full_output = "".join(init_output) + (stdout or "") + (stderr or "")
    except Exception as e:
        print("Failed running orca_plot for density:", e)
        return None, str(e)
        
    matching_files = glob.glob(os.path.join(job_dir, "*dens*.cube"))
    if matching_files:
        return matching_files[0], ""
    return None, full_output


class OrcaResultsDialog(QDialog):


    def __init__(self, parent, job_id, job_manager, app_instance):
        super().__init__(parent)
        self.setWindowTitle(f"Calculation Results - {job_id}")
        self.resize(750, 550)
        self.setStyleSheet("""
            QDialog { background-color: #1e1e1e; color: white; }
            QTabWidget::pane { border: 1px solid #444; background: #2d2d2d; }
            QTabBar::tab { background: #333; color: #ccc; padding: 8px 16px; }
            QTabBar::tab:selected { background: #0078D4; color: white; }
            QTableWidget { background-color: #222; color: #fff; gridline-color: #444; }
            QLineEdit { background-color: #333; color: white; border: 1px solid #555; padding: 4px; }
            QPushButton { background-color: #0078D4; color: white; border: none; padding: 6px 12px; border-radius: 4px; }
        """)

        self.job_id = job_id
        self.job_manager = job_manager
        self.app_instance = app_instance
        self.results = self.job_manager.parse_results(job_id)

        # Load job metadata first (required for charge etc.)
        self.job_meta = {}
        job_dir = self.job_manager.get_job_dir(job_id)
        meta_file = os.path.join(job_dir, "job_meta.json")
        if os.path.exists(meta_file):
            try:
                with open(meta_file, "r") as f:
                    self.job_meta = json.load(f)
            except:
                pass

        # Compute symmetry ranks
        self.sym_ranks = None
        xyz_content = self.results.get("optimized_xyz")
        if xyz_content:
            try:
                from rdkit import Chem
                from rdkit.Chem import rdDetermineBonds
                mol = Chem.MolFromXYZBlock(xyz_content)
                if mol:
                    charge = self.job_meta.get("charge", 0)
                    try:
                        rdDetermineBonds.DetermineBonds(mol, charge=charge)
                    except Exception as ex:
                        print("Symmetry ranking DetermineBonds error:", ex)
                    ranks_list = calculate_symmetry_ranks(mol)
                    if ranks_list:
                        self.sym_ranks = {i: r for i, r in enumerate(ranks_list)}
            except Exception as e:
                print("Symmetry ranking calculation error:", e)
        
        if not self.sym_ranks and self.results.get("nmr_shieldings"):
            self.sym_ranks = {idx: idx for idx in self.results["nmr_shieldings"].keys()}

        layout = QVBoxLayout(self)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # Tab 1: SCF Energies (Convergence)
        self.energy_tab = QWidget()
        et_layout = QVBoxLayout(self.energy_tab)
        self.energy_plot = EnergyPlotWidget()
        self.energy_plot.set_energies(self.results["energies"])
        self.energy_plot.stepClicked.connect(self.on_step_clicked)
        et_layout.addWidget(self.energy_plot)
        self.tabs.addTab(self.energy_tab, "Energy Convergence")

        # Tab 2: NMR Chemical Shifts (Sub-tabs for Standard TMS & Tantillo Scaling)
        self.nmr_tab = QWidget()
        nt_layout = QVBoxLayout(self.nmr_tab)
        nt_layout.setContentsMargins(4, 4, 4, 4)
        
        self.nmr_subtabs = QTabWidget()
        nt_layout.addWidget(self.nmr_subtabs)
        
        method = self.job_meta.get("functional") or self.job_meta.get("method", "")
        basis = self.job_meta.get("basis", "")
        workspace_dir = self.job_manager.workspace_dir if hasattr(self.job_manager, 'workspace_dir') else None

        # --- SUB-TAB 1: Standard TMS Methode ---
        self.nmr_std_tab = QWidget()
        std_layout = QVBoxLayout(self.nmr_std_tab)
        
        h_refs_std = QHBoxLayout()
        h_refs_std.addWidget(QLabel("1H Reference Shielding:"))
        self.ref_1h_input = QLineEdit(str(DEFAULT_NMR_REFS["1H"]))
        self.ref_1h_input.setFixedWidth(75)
        self.ref_1h_input.textChanged.connect(self.update_std_nmr_table)
        h_refs_std.addWidget(self.ref_1h_input)

        h_refs_std.addWidget(QLabel("13C Reference Shielding:"))
        self.ref_13c_input = QLineEdit(str(DEFAULT_NMR_REFS["13C"]))
        self.ref_13c_input.setFixedWidth(75)
        self.ref_13c_input.textChanged.connect(self.update_std_nmr_table)
        h_refs_std.addWidget(self.ref_13c_input)

        self.btn_tms_db = QPushButton("TMS References...")
        self.btn_tms_db.setToolTip("Opens database for TMS reference values to view, select, and edit")
        self.btn_tms_db.clicked.connect(self.open_tms_db_dialog)
        h_refs_std.addWidget(self.btn_tms_db)

        # Quick match check for TMS
        geom_method = self.job_meta.get("geom_method")
        geom_basis = self.job_meta.get("geom_basis")
        geom_solvent = self.job_meta.get("opt_solvent")
        nmr_solvent = self.job_meta.get("nmr_solvent")
        solvent_model = self.job_meta.get("nmr_solvent_model")
        matched_tms = find_best_tms_match(
            method, basis,
            geom_method=geom_method, geom_basis=geom_basis,
            tms_list=load_tms_references(workspace_dir),
            geom_solvent=geom_solvent, nmr_solvent=nmr_solvent, solvent_model=solvent_model
        )
        if matched_tms:
            h1 = matched_tms.get("h1_shielding")
            c13 = matched_tms.get("c13_shielding")
            m_parts = []
            if h1 is not None: m_parts.append(f"1H={h1}")
            if c13 is not None: m_parts.append(f"13C={c13}")
            if m_parts:
                btn_quick_tms = QPushButton(f"⚡ {method}/{basis} ({', '.join(m_parts)})")
                btn_quick_tms.setStyleSheet("background-color: #2b5b84; color: white; border: 1px solid #4fc3f7;")
                btn_quick_tms.setToolTip(f"Automatically applies matching TMS reference values for {method}/{basis}")
                btn_quick_tms.clicked.connect(lambda _, h=h1, c=c13: self._quick_apply_tms(h, c))
                h_refs_std.addWidget(btn_quick_tms)

        h_refs_std.addStretch()
        std_layout.addLayout(h_refs_std)

        self.nmr_std_table = QTableWidget(0, 5)
        self.nmr_std_table.setHorizontalHeaderLabels(["Atom", "Element", "Shielding (\u03c3, ppm)", "Standard Shift (\u03b4, ppm)", "Symmetry Avg. Shift (\u03b4, ppm)"])
        self.nmr_std_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.nmr_std_table.itemSelectionChanged.connect(self.on_std_table_selection_changed)
        std_layout.addWidget(self.nmr_std_table)

        std_btn_layout = QHBoxLayout()
        self.apply_std_nmr_btn = QPushButton("Apply Standard NMR Shifts as 3D Labels")
        self.apply_std_nmr_btn.clicked.connect(self.apply_standard_nmr_labels)
        std_btn_layout.addWidget(self.apply_std_nmr_btn)
        self.apply_std_avg_nmr_btn = QPushButton("Apply Symmetry Avg. Shifts as 3D Labels")
        self.apply_std_avg_nmr_btn.clicked.connect(self.apply_standard_avg_nmr_labels)
        self.apply_std_avg_nmr_btn.setStyleSheet("background-color: #2e7d32; color: white;")
        std_btn_layout.addWidget(self.apply_std_avg_nmr_btn)
        std_btn_layout.addStretch()
        std_layout.addLayout(std_btn_layout)

        self.nmr_subtabs.addTab(self.nmr_std_tab, "Standard TMS Method")

        # --- SUB-TAB 2: Tantillo Scaling Method ---
        self.nmr_tantillo_tab = QWidget()
        tantillo_layout = QVBoxLayout(self.nmr_tantillo_tab)

        # Retrieve solvent info from job metadata
        nmr_solvent_meta = self.job_meta.get("nmr_solvent", "Gas")
        nmr_model_meta = self.job_meta.get("nmr_solvent_model", None)
        opt_solvent_meta = self.job_meta.get("opt_solvent", "Gas")
        opt_model_meta = self.job_meta.get("opt_solvent_model", None)

        solv_info_parts = []
        if nmr_model_meta and nmr_model_meta.lower() not in ("none", ""):
            solv_info_parts.append(f"NMR: {nmr_solvent_meta} ({nmr_model_meta})")
        else:
            solv_info_parts.append("NMR: Gas Phase")
        if opt_model_meta and opt_model_meta.lower() not in ("none", ""):
            solv_info_parts.append(f"Geom: {opt_solvent_meta} ({opt_model_meta})")
        else:
            solv_info_parts.append("Geom: Gas Phase")

        solv_info_lbl = QLabel("ℹ " + " | ".join(solv_info_parts))
        solv_info_lbl.setStyleSheet("color: #80cbc4; font-size: 11px; font-style: italic;")
        tantillo_layout.addWidget(solv_info_lbl)

        # Prefill default or matched Tantillo parameters (solvent-aware)
        matched_tantillo = find_best_tantillo_match(
            method, basis,
            geom_method=self.job_meta.get("geom_method"),
            geom_basis=self.job_meta.get("geom_basis"),
            tantillo_list=load_tantillo_scaling(workspace_dir),
            nmr_solvent=nmr_solvent_meta,
            solvent_model=nmr_model_meta if nmr_model_meta and nmr_model_meta.lower() not in ("none", "") else None
        )
        t_h1_slope = str(matched_tantillo.get("h1_slope", "-0.9957")) if matched_tantillo else "-0.9957"
        t_h1_int = str(matched_tantillo.get("h1_intercept", "32.2884")) if matched_tantillo else "32.2884"
        t_c13_slope = str(matched_tantillo.get("c13_slope", "-0.9269")) if matched_tantillo else "-0.9269"
        t_c13_int = str(matched_tantillo.get("c13_intercept", "187.4743")) if matched_tantillo else "187.4743"

        h_tantillo_inputs = QHBoxLayout()

        h_tantillo_inputs.addWidget(QLabel("1H Slope:"))
        self.tantillo_1h_slope_input = QLineEdit(t_h1_slope)
        self.tantillo_1h_slope_input.setFixedWidth(65)
        self.tantillo_1h_slope_input.textChanged.connect(self.update_tantillo_nmr_table)
        h_tantillo_inputs.addWidget(self.tantillo_1h_slope_input)

        h_tantillo_inputs.addWidget(QLabel("1H Intercept:"))
        self.tantillo_1h_intercept_input = QLineEdit(t_h1_int)
        self.tantillo_1h_intercept_input.setFixedWidth(65)
        self.tantillo_1h_intercept_input.textChanged.connect(self.update_tantillo_nmr_table)
        h_tantillo_inputs.addWidget(self.tantillo_1h_intercept_input)

        h_tantillo_inputs.addWidget(QLabel("13C Slope:"))
        self.tantillo_13c_slope_input = QLineEdit(t_c13_slope)
        self.tantillo_13c_slope_input.setFixedWidth(65)
        self.tantillo_13c_slope_input.textChanged.connect(self.update_tantillo_nmr_table)
        h_tantillo_inputs.addWidget(self.tantillo_13c_slope_input)

        h_tantillo_inputs.addWidget(QLabel("13C Intercept:"))
        self.tantillo_13c_intercept_input = QLineEdit(t_c13_int)
        self.tantillo_13c_intercept_input.setFixedWidth(65)
        self.tantillo_13c_intercept_input.textChanged.connect(self.update_tantillo_nmr_table)
        h_tantillo_inputs.addWidget(self.tantillo_13c_intercept_input)

        self.btn_tantillo_db = QPushButton("Tantillo Scaling...")
        self.btn_tantillo_db.setToolTip("Opens database for Tantillo scaling factors")
        self.btn_tantillo_db.clicked.connect(self.open_tantillo_db_dialog)
        h_tantillo_inputs.addWidget(self.btn_tantillo_db)

        if matched_tantillo:
            nmr_s_lbl = matched_tantillo.get("nmr_solvent", "Gas")
            sol_m_lbl = matched_tantillo.get("solvent_model") or ""
            solvent_suffix = f" | {nmr_s_lbl}/{sol_m_lbl}" if sol_m_lbl else (f" | {nmr_s_lbl}" if nmr_s_lbl != "Gas" else "")
            btn_quick_tan = QPushButton(f"⚡ {method}/{basis}{solvent_suffix}")
            btn_quick_tan.setStyleSheet("background-color: #2b5b84; color: white; border: 1px solid #4fc3f7;")
            btn_quick_tan.setToolTip(
                f"Applies Tantillo parameters for {method}/{basis}\n"
                f"Source: {matched_tantillo.get('source', '')}\n"
                f"NMR Solvent: {nmr_s_lbl} ({sol_m_lbl or 'Gas'})"
            )
            btn_quick_tan.clicked.connect(lambda _, m=matched_tantillo: self._quick_apply_tantillo(m))
            h_tantillo_inputs.addWidget(btn_quick_tan)

        h_tantillo_inputs.addStretch()
        tantillo_layout.addLayout(h_tantillo_inputs)

        self.nmr_tantillo_table = QTableWidget(0, 5)
        self.nmr_tantillo_table.setHorizontalHeaderLabels(["Atom", "Element", "Shielding (\u03c3, ppm)", "Tantillo Shift (\u03b4, ppm)", "Symmetry Avg. Shift (\u03b4, ppm)"])
        self.nmr_tantillo_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.nmr_tantillo_table.itemSelectionChanged.connect(self.on_tantillo_table_selection_changed)
        tantillo_layout.addWidget(self.nmr_tantillo_table)

        tan_btn_layout = QHBoxLayout()
        self.apply_tantillo_nmr_btn = QPushButton("Apply Tantillo NMR Shifts as 3D Labels")
        self.apply_tantillo_nmr_btn.clicked.connect(self.apply_tantillo_nmr_labels)
        tan_btn_layout.addWidget(self.apply_tantillo_nmr_btn)
        self.apply_tan_avg_nmr_btn = QPushButton("Apply Symmetry Avg. Shifts as 3D Labels")
        self.apply_tan_avg_nmr_btn.clicked.connect(self.apply_tantillo_avg_nmr_labels)
        self.apply_tan_avg_nmr_btn.setStyleSheet("background-color: #2e7d32; color: white;")
        tan_btn_layout.addWidget(self.apply_tan_avg_nmr_btn)
        tan_btn_layout.addStretch()
        tantillo_layout.addLayout(tan_btn_layout)

        self.nmr_subtabs.addTab(self.nmr_tantillo_tab, "Tantillo Scaling Method")

        # Dynamic Tabs for NMR (only if NMR shieldings exist)
        shieldings_data = self.results.get("nmr_shieldings", {})
        if shieldings_data:
            self.tabs.addTab(self.nmr_tab, "NMR Chemical Shifts")
            self.update_std_nmr_table()
            self.update_tantillo_nmr_table()

            self.nmr_spec_tab = QWidget()
            nmr_sp_layout = QVBoxLayout(self.nmr_spec_tab)

            nmr_sp_ctrl = QHBoxLayout()
            nmr_sp_ctrl.addWidget(QLabel("Nucleus:"))
            self.nmr_nuc_combo = QComboBox()
            self.nmr_nuc_combo.addItems(["1H", "13C"])
            nmr_sp_ctrl.addWidget(self.nmr_nuc_combo)

            nmr_sp_ctrl.addWidget(QLabel("Method:"))
            self.nmr_meth_combo = QComboBox()
            self.nmr_meth_combo.addItems(["Standard TMS", "Standard TMS (Symmetry Avg.)", "Tantillo Scaled", "Tantillo Scaled (Symmetry Avg.)"])
            nmr_sp_ctrl.addWidget(self.nmr_meth_combo)

            nmr_sp_ctrl.addStretch()
            nmr_sp_layout.addLayout(nmr_sp_ctrl)

            self.nmr_spec_plot = NmrSpectrumPlotWidget()
            self.nmr_spec_plot.atomClicked.connect(self.on_nmr_peak_clicked)
            nmr_sp_layout.addWidget(self.nmr_spec_plot)

            self.nmr_nuc_combo.currentTextChanged.connect(self.update_nmr_spectrum_plot)
            self.nmr_meth_combo.currentTextChanged.connect(self.update_nmr_spectrum_plot)

            self.tabs.addTab(self.nmr_spec_tab, "NMR Spectrum")
            self.update_nmr_spectrum_plot()

        # Tab 3: Vibrational Frequencies & IR Spectrum (only if frequencies exist)
        freqs_data = self.results.get("frequencies") or self.results.get("vibrational_frequencies", [])
        if freqs_data:
            self.freq_tab = QWidget()
            ft_layout = QVBoxLayout(self.freq_tab)
            self.freq_table = QTableWidget(0, 3)
            self.freq_table.setHorizontalHeaderLabels(["Mode Index", "Frequency (cm\u207b\u00b9)", "IR Intensity"])
            self.freq_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            ft_layout.addWidget(self.freq_table)

            h_freq_btn = QHBoxLayout()
            self.vib_btn = QPushButton("Animate Selected Mode")
            self.vib_btn.clicked.connect(self.animate_selected_mode)
            self.freq_table.itemSelectionChanged.connect(self.on_freq_selection_changed)
            h_freq_btn.addWidget(self.vib_btn)
            ft_layout.addLayout(h_freq_btn)
            self.tabs.addTab(self.freq_tab, "Vibrational Frequencies")
            self.update_freq_table()

            # Dynamic Tab: IR Spectrum
            self.ir_spec_tab = QWidget()
            ir_layout = QVBoxLayout(self.ir_spec_tab)

            ir_ctrl = QHBoxLayout()
            ir_ctrl.addWidget(QLabel("Peak Broadening (FWHM, cm⁻¹):"))
            self.ir_fwhm_spin = QDoubleSpinBox()
            self.ir_fwhm_spin.setRange(2.0, 80.0)
            self.ir_fwhm_spin.setValue(15.0)
            self.ir_fwhm_spin.setSingleStep(2.0)
            ir_ctrl.addWidget(self.ir_fwhm_spin)
            ir_ctrl.addStretch()
            ir_layout.addLayout(ir_ctrl)

            self.ir_spec_plot = IrSpectrumPlotWidget()
            self.ir_spec_plot.set_modes(freqs_data)
            self.ir_fwhm_spin.valueChanged.connect(lambda val: self.ir_spec_plot.set_fwhm(val))
            ir_layout.addWidget(self.ir_spec_plot)

            self.tabs.addTab(self.ir_spec_tab, "IR Spectrum")



        # Tab 4: Short Results
        self.short_tab = QWidget()
        st_layout = QVBoxLayout(self.short_tab)

        # Card 1: Job Setup & Quantum Methods
        self.methods_card = QGroupBox("Calculation Setup & Quantum Methods")
        self.methods_card.setStyleSheet("QGroupBox { font-weight: bold; color: white; border: 1px solid #444; margin-top: 6px; padding: 10px; }")
        st_form1 = QFormLayout()

        task_str = str(self.job_meta.get("task", "Opt"))
        method_str = str(self.job_meta.get("functional") or self.job_meta.get("method", "B3LYP"))
        basis_str = str(self.job_meta.get("basis", "def2-SVP"))
        disp_str = str(self.job_meta.get("dispersion", "None"))
        charge_str = f"Charge = {self.job_meta.get('charge', 0)}, Multiplicity = {self.job_meta.get('multiplicity', 1)}"
        procs_str = f"{self.job_meta.get('nprocs', 1)} CPUs, MaxCore = {self.job_meta.get('maxcore', 2000)} MB"
        status_str = f"{self.job_meta.get('status', 'completed')} ({self.job_meta.get('created', 'N/A')})"

        use_sep_nmr = self.job_meta.get("use_sep_nmr", False)

        st_form1.addRow("Task Type:", QLabel(task_str))
        if use_sep_nmr:
            geom_m = self.job_meta.get("geom_method", method_str)
            geom_b = self.job_meta.get("geom_basis", basis_str)
            nmr_m = self.job_meta.get("nmr_method", method_str)
            nmr_b = self.job_meta.get("nmr_basis", basis_str)
            st_form1.addRow("Geometry Method & Basis:", QLabel(f"{geom_m} / {geom_b}"))
            st_form1.addRow("NMR Method & Basis:", QLabel(f"{nmr_m} / {nmr_b}"))
            st_form1.addRow("ORCA Job Type:", QLabel("% Compound (Multi-step Opt + NMR)"))
        else:
            st_form1.addRow("Functional / Method:", QLabel(method_str))
            st_form1.addRow("Basis Set:", QLabel(basis_str))

        st_form1.addRow("Dispersion Correction:", QLabel(disp_str))
        st_form1.addRow("Charge / Multiplicity:", QLabel(charge_str))
        st_form1.addRow("Parallelization:", QLabel(procs_str))
        st_form1.addRow("Job Status & Creation:", QLabel(status_str))
        self.methods_card.setLayout(st_form1)
        st_layout.addWidget(self.methods_card)


        # Card 2: Energy & Thermodynamics
        self.thermo_card = QGroupBox("Thermodynamics & Energy Summary (at 298.15 K)")
        self.thermo_card.setStyleSheet("QGroupBox { font-weight: bold; color: white; border: 1px solid #444; margin-top: 6px; padding: 10px; }")
        st_form2 = QFormLayout()

        energies = self.results.get("energies", [])
        e_final_str = f"{energies[-1]:.8f} Eh" if energies else "N/A"
        st_form2.addRow("Final Total Energy (E):", QLabel(e_final_str))

        h_val = self.results.get("enthalpy")
        h_str = f"{h_val:.6f} Eh" if h_val is not None else "N/A (Run Freq calculation)"
        st_form2.addRow("Enthalpy (H):", QLabel(h_str))

        g_val = self.results.get("gibbs_energy")
        g_str = f"{g_val:.6f} Eh" if g_val is not None else "N/A (Run Freq calculation)"
        st_form2.addRow("Gibbs Free Energy (G):", QLabel(g_str))

        ts_val = self.results.get("entropy_correction")
        ts_str = f"{ts_val:.6f} Eh" if ts_val is not None else "N/A (Run Freq calculation)"
        st_form2.addRow("TS Entropy Correction:", QLabel(ts_str))

        dip_val = self.results.get("dipole_magnitude")
        dip_str = f"{dip_val:.4f} Debye" if dip_val is not None else "N/A"
        st_form2.addRow("Dipole Moment Magnitude:", QLabel(dip_str))

        self.thermo_card.setLayout(st_form2)
        st_layout.addWidget(self.thermo_card)
        st_layout.addStretch()

        # Tab: Molecular Orbitals
        gbw_path = os.path.join(job_dir, "orca_input.gbw")
        if os.path.exists(gbw_path):
            self.orbitals_tab = QWidget()
            orb_layout = QVBoxLayout(self.orbitals_tab)
            
            ctrl_layout = QHBoxLayout()
            ctrl_layout.addWidget(QLabel("Iso-Wert (Contour):"))
            self.orb_isoval_spin = QDoubleSpinBox()
            self.orb_isoval_spin.setRange(0.001, 0.5)
            self.orb_isoval_spin.setValue(0.02)
            self.orb_isoval_spin.setDecimals(3)
            self.orb_isoval_spin.setSingleStep(0.005)
            self.orb_isoval_spin.setFixedWidth(80)
            ctrl_layout.addWidget(self.orb_isoval_spin)
            
            self.visualize_orb_btn = QPushButton("Orbital visualisieren")
            self.visualize_orb_btn.clicked.connect(self.visualize_selected_orbital)
            ctrl_layout.addWidget(self.visualize_orb_btn)
            
            self.visualize_dens_btn = QPushButton("Elektronendichte visualisieren")
            self.visualize_dens_btn.clicked.connect(self.visualize_density)
            ctrl_layout.addWidget(self.visualize_dens_btn)
            
            self.clear_orb_btn = QPushButton("Visualisierung zurücksetzen")
            self.clear_orb_btn.clicked.connect(self.clear_orbital_visualization)
            self.clear_orb_btn.setStyleSheet("background-color: #c42b1c;")
            ctrl_layout.addWidget(self.clear_orb_btn)
            
            ctrl_layout.addStretch()
            orb_layout.addLayout(ctrl_layout)
            
            self.orbitals_table = QTableWidget(0, 4)
            self.orbitals_table.setHorizontalHeaderLabels(["Orbital", "Besetzung (OCC)", "Energie (eV)", "Typ (HOMO/LUMO)"])
            self.orbitals_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            self.orbitals_table.setSelectionBehavior(QTableWidget.SelectRows)
            self.orbitals_table.setSelectionMode(QTableWidget.SingleSelection)
            orb_layout.addWidget(self.orbitals_table)
            
            self.tabs.addTab(self.orbitals_tab, "Molecular Orbitals")
            
            out_file = os.path.join(job_dir, "orca_output.out")
            self.parsed_orbitals, self.homo_idx, self.lumo_idx = parse_orbitals(out_file)
            self.fill_orbitals_table()

        self.tabs.addTab(self.short_tab, "Short Results")


        # Tab 5: Raw Output
        self.raw_tab = QWidget()
        rt_layout = QVBoxLayout(self.raw_tab)
        self.raw_text = QTextEdit()
        self.raw_text.setReadOnly(True)
        self.raw_text.setStyleSheet("background-color: #111; color: #ccc; font-family: 'Consolas';")
        out_file = os.path.join(self.job_manager.get_job_dir(job_id), "orca_output.out")
        if os.path.exists(out_file):
            try:
                with open(out_file, "r", encoding="utf-8", errors="ignore") as f:
                    self.raw_text.setText(f.read())
            except:
                pass
        rt_layout.addWidget(self.raw_text)
        self.tabs.addTab(self.raw_tab, "Raw Output")

    def on_step_clicked(self, step_idx):
        if "trajectory" in self.results and step_idx < len(self.results["trajectory"]):
            xyz_content = self.results["trajectory"][step_idx]
            from rdkit import Chem
            try:
                mol = Chem.MolFromXYZBlock(xyz_content)
                if mol:
                    try:
                        from rdkit.Chem import rdDetermineBonds
                        job_dir = self.job_manager.get_job_dir(self.job_id)
                        meta_file = os.path.join(job_dir, "job_meta.json")
                        charge = 0
                        if os.path.exists(meta_file):
                            with open(meta_file, "r") as f:
                                meta = json.load(f)
                                charge = meta.get("charge", 0)
                        rdDetermineBonds.DetermineBonds(mol, charge=charge)
                    except Exception as ex:
                        print("Determine bonds error:", ex)
                    self.app_instance.update_viewer(mol)
                    self.app_instance.current_mol = mol
                    func = self.job_meta.get("functional") or self.job_meta.get("method", "B3LYP")
                    basis = self.job_meta.get("basis", "")
                    b_str = f" / {basis}" if basis else ""
                    self.app_instance.set_method_badge(f"ORCA: {func}{b_str} (Step {step_idx + 1})")
                    self.app_instance.statusBar().showMessage(f"Preview: Geometry from optimization step {step_idx + 1}")
            except Exception as e:
                print("Could not update viewer for step:", e)

    def update_nmr_spectrum_plot(self):
        if not hasattr(self, 'nmr_spec_plot'):
            return
        nucleus = self.nmr_nuc_combo.currentText() if hasattr(self, 'nmr_nuc_combo') else "1H"
        method_type = self.nmr_meth_combo.currentText() if hasattr(self, 'nmr_meth_combo') else "Standard TMS"

        shieldings = self.results.get("nmr_shieldings", {})
        shifts = []
        computed_shifts = {}

        if "Standard TMS" in method_type:
            try: ref_1h = float(self.ref_1h_input.text().replace(',', '.'))
            except: ref_1h = DEFAULT_NMR_REFS["1H"]
            try: ref_13c = float(self.ref_13c_input.text().replace(',', '.'))
            except: ref_13c = DEFAULT_NMR_REFS["13C"]

            for idx, info in shieldings.items():
                elem = info["element"]
                ref_val = ref_1h if elem == "H" else (ref_13c if elem == "C" else DEFAULT_NMR_REFS.get(f"1{elem}", 0.0))
                computed_shifts[idx] = ref_val - info["shielding"]
        else: # Tantillo Scaled
            try: h1_s = float(self.tantillo_1h_slope_input.text().replace(',', '.'))
            except: h1_s = None
            try: h1_i = float(self.tantillo_1h_intercept_input.text().replace(',', '.'))
            except: h1_i = None
            try: c13_s = float(self.tantillo_13c_slope_input.text().replace(',', '.'))
            except: c13_s = None
            try: c13_i = float(self.tantillo_13c_intercept_input.text().replace(',', '.'))
            except: c13_i = None

            for idx, info in shieldings.items():
                elem = info["element"]
                val = None
                if elem == "H" and h1_s is not None and h1_i is not None and h1_s != 0:
                    val = (info["shielding"] - h1_i) / h1_s
                elif elem == "C" and c13_s is not None and c13_i is not None and c13_s != 0:
                    val = (info["shielding"] - c13_i) / c13_s
                if val is not None:
                    computed_shifts[idx] = val

        # Check if we should apply symmetry averaging
        if "Symmetry Avg." in method_type:
            rank_to_vals = {}
            if self.sym_ranks:
                for idx, val in computed_shifts.items():
                    rank = self.sym_ranks.get(idx)
                    if rank is not None:
                        if rank not in rank_to_vals:
                            rank_to_vals[rank] = []
                        rank_to_vals[rank].append(val)
            
            rank_to_avg = {}
            for rank, vals in rank_to_vals.items():
                rank_to_avg[rank] = sum(vals) / len(vals)

            for idx, info in shieldings.items():
                if idx in computed_shifts:
                    elem = info["element"]
                    rank = self.sym_ranks.get(idx) if self.sym_ranks else None
                    val = rank_to_avg.get(rank, computed_shifts[idx]) if rank is not None else computed_shifts[idx]
                    shifts.append({"atom": f"{elem}{idx}", "elem": elem, "shift": val})
        else:
            for idx, info in shieldings.items():
                if idx in computed_shifts:
                    elem = info["element"]
                    shifts.append({"atom": f"{elem}{idx}", "elem": elem, "shift": computed_shifts[idx]})

        self.nmr_spec_plot.set_data(shifts, nucleus=nucleus)

    def open_tms_db_dialog(self):
        method = self.job_meta.get("functional") or self.job_meta.get("method", "")
        basis = self.job_meta.get("basis", "")
        geom_method = self.job_meta.get("geom_method")
        geom_basis = self.job_meta.get("geom_basis")
        geom_solvent = self.job_meta.get("opt_solvent")
        nmr_solvent = self.job_meta.get("nmr_solvent")
        solvent_model = self.job_meta.get("nmr_solvent_model")
        workspace_dir = self.job_manager.workspace_dir if hasattr(self.job_manager, 'workspace_dir') else None
        
        dlg = TMSReferenceDialog(
            workspace_dir=workspace_dir,
            current_method=method,
            current_basis=basis,
            parent=self,
            geom_method=geom_method,
            geom_basis=geom_basis,
            geom_solvent=geom_solvent,
            nmr_solvent=nmr_solvent,
            solvent_model=solvent_model
        )
        if dlg.exec_() == QDialog.Accepted and dlg.selected_ref:
            h1_val, c13_val = dlg.selected_ref
            self._quick_apply_tms(h1_val, c13_val)

    def _quick_apply_tms(self, h1, c13):
        if h1 is not None:
            self.ref_1h_input.setText(str(h1))
        if c13 is not None:
            self.ref_13c_input.setText(str(c13))
        self.update_std_nmr_table()

    def _quick_apply_tantillo(self, entry):
        if entry:
            if entry.get("h1_slope") is not None:
                self.tantillo_1h_slope_input.setText(str(entry["h1_slope"]))
            if entry.get("h1_intercept") is not None:
                self.tantillo_1h_intercept_input.setText(str(entry["h1_intercept"]))
            if entry.get("c13_slope") is not None:
                self.tantillo_13c_slope_input.setText(str(entry["c13_slope"]))
            if entry.get("c13_intercept") is not None:
                self.tantillo_13c_intercept_input.setText(str(entry["c13_intercept"]))
            self.update_tantillo_nmr_table()

    def open_tantillo_db_dialog(self):
        workspace_dir = self.job_manager.workspace_dir if hasattr(self.job_manager, 'workspace_dir') else None
        dlg = TantilloReferenceDialog(workspace_dir=workspace_dir, parent=self)
        if dlg.exec_() == QDialog.Accepted:
            row = dlg.table.currentRow()
            if row >= 0 and 0 <= row < len(dlg.tantillo_list):
                selected = dlg.tantillo_list[row]
                self._quick_apply_tantillo(selected)

    def update_std_nmr_table(self):
        self.nmr_std_table.setRowCount(0)
        shieldings = self.results.get("nmr_shieldings", {})
        if not shieldings:
            return

        try:
            ref_1h = float(self.ref_1h_input.text().replace(',', '.'))
        except:
            ref_1h = DEFAULT_NMR_REFS["1H"]
        try:
            ref_13c = float(self.ref_13c_input.text().replace(',', '.'))
        except:
            ref_13c = DEFAULT_NMR_REFS["13C"]

        # Compute standard shifts
        computed_shifts = {}
        for idx, info in shieldings.items():
            elem = info["element"]
            ref_val = 0.0
            if elem == "H":
                ref_val = ref_1h
            elif elem == "C":
                ref_val = ref_13c
            else:
                ref_val = DEFAULT_NMR_REFS.get(f"1{elem}", 0.0)
            computed_shifts[idx] = ref_val - info["shielding"]

        # Symmetry averaging
        rank_to_vals = {}
        if self.sym_ranks:
            for idx, val in computed_shifts.items():
                rank = self.sym_ranks.get(idx)
                if rank is not None:
                    if rank not in rank_to_vals:
                        rank_to_vals[rank] = []
                    rank_to_vals[rank].append(val)
        
        rank_to_avg = {}
        for rank, vals in rank_to_vals.items():
            rank_to_avg[rank] = sum(vals) / len(vals)

        for idx, info in sorted(shieldings.items()):
            row = self.nmr_std_table.rowCount()
            self.nmr_std_table.insertRow(row)
            self.nmr_std_table.setItem(row, 0, QTableWidgetItem(f"Atom {idx}"))
            self.nmr_std_table.setItem(row, 1, QTableWidgetItem(info["element"]))
            self.nmr_std_table.setItem(row, 2, QTableWidgetItem(f"{info['shielding']:.4f}"))
            
            shift = computed_shifts[idx]
            self.nmr_std_table.setItem(row, 3, QTableWidgetItem(f"{shift:.2f}"))
            
            rank = self.sym_ranks.get(idx) if self.sym_ranks else None
            avg_shift = rank_to_avg.get(rank, shift) if rank is not None else shift
            self.nmr_std_table.setItem(row, 4, QTableWidgetItem(f"{avg_shift:.2f}"))
            
        self.update_nmr_spectrum_plot()

    def update_tantillo_nmr_table(self):
        self.nmr_tantillo_table.setRowCount(0)
        shieldings = self.results.get("nmr_shieldings", {})
        if not shieldings:
            return

        try: h1_s = float(self.tantillo_1h_slope_input.text().replace(',', '.'))
        except: h1_s = None
        try: h1_i = float(self.tantillo_1h_intercept_input.text().replace(',', '.'))
        except: h1_i = None
        try: c13_s = float(self.tantillo_13c_slope_input.text().replace(',', '.'))
        except: c13_s = None
        try: c13_i = float(self.tantillo_13c_intercept_input.text().replace(',', '.'))
        except: c13_i = None

        # Compute individual Tantillo shifts
        computed_shifts = {}
        for idx, info in shieldings.items():
            elem = info["element"]
            val = None
            if elem == "H" and h1_s is not None and h1_i is not None and h1_s != 0:
                val = (info["shielding"] - h1_i) / h1_s
            elif elem == "C" and c13_s is not None and c13_i is not None and c13_s != 0:
                val = (info["shielding"] - c13_i) / c13_s
            if val is not None:
                computed_shifts[idx] = val

        # Symmetry averaging
        rank_to_vals = {}
        if self.sym_ranks:
            for idx, val in computed_shifts.items():
                rank = self.sym_ranks.get(idx)
                if rank is not None:
                    if rank not in rank_to_vals:
                        rank_to_vals[rank] = []
                    rank_to_vals[rank].append(val)
        
        rank_to_avg = {}
        for rank, vals in rank_to_vals.items():
            rank_to_avg[rank] = sum(vals) / len(vals)

        for idx, info in sorted(shieldings.items()):
            row = self.nmr_tantillo_table.rowCount()
            self.nmr_tantillo_table.insertRow(row)
            self.nmr_tantillo_table.setItem(row, 0, QTableWidgetItem(f"Atom {idx}"))
            self.nmr_tantillo_table.setItem(row, 1, QTableWidgetItem(info["element"]))
            self.nmr_tantillo_table.setItem(row, 2, QTableWidgetItem(f"{info['shielding']:.4f}"))
            
            tantillo_val = "--"
            avg_val = "--"
            if idx in computed_shifts:
                val = computed_shifts[idx]
                tantillo_val = f"{val:.2f}"
                rank = self.sym_ranks.get(idx) if self.sym_ranks else None
                if rank in rank_to_avg:
                    avg_val = f"{rank_to_avg[rank]:.2f}"
                else:
                    avg_val = tantillo_val

            self.nmr_tantillo_table.setItem(row, 3, QTableWidgetItem(tantillo_val))
            self.nmr_tantillo_table.setItem(row, 4, QTableWidgetItem(avg_val))
        self.update_nmr_spectrum_plot()



    def on_freq_selection_changed(self):
        selected_ranges = self.freq_table.selectedRanges()
        if not selected_ranges:
            self.vib_btn.setText("Animate Selected Mode")
            return
        row = selected_ranges[0].topRow()
        try:
            mode_idx = int(self.freq_table.item(row, 0).text())
        except:
            self.vib_btn.setText("Animate Selected Mode")
            return
        if hasattr(self, "_animating_mode") and self._animating_mode == mode_idx:
            self.vib_btn.setText("Stop Animation")
        else:
            self.vib_btn.setText("Animate Selected Mode")

    def update_freq_table(self):
        self.freq_table.setRowCount(0)
        freqs = self.results["frequencies"]
        for f in freqs:
            row = self.freq_table.rowCount()
            self.freq_table.insertRow(row)
            self.freq_table.setItem(row, 0, QTableWidgetItem(str(f["index"])))
            self.freq_table.setItem(row, 1, QTableWidgetItem(f"{f['frequency']:.2f}"))
            intensity_str = f"{f['intensity']:.2f}" if "intensity" in f else "1.00 (Est.)"
            self.freq_table.setItem(row, 2, QTableWidgetItem(intensity_str))

    def animate_selected_mode(self):
        selected_ranges = self.freq_table.selectedRanges()
        if not selected_ranges:
            QMessageBox.warning(self, "No selection", "Please select a vibrational mode from the table first.")
            return
            
        row = selected_ranges[0].topRow()
        try:
            mode_idx = int(self.freq_table.item(row, 0).text())
        except:
            return
            
        normal_modes = self.results.get("normal_modes", {})
        if not normal_modes or mode_idx not in normal_modes:
            QMessageBox.warning(self, "No displacements", "No normal mode displacement coordinates found for this mode in the output file.")
            return
            
        disps = normal_modes[mode_idx]
        
        if hasattr(self, "_animating_mode") and self._animating_mode == mode_idx:
            js_code = "if (typeof viewer !== 'undefined') { viewer.stopAnimate(); }"
            self.app_instance.web_view.page().runJavaScript(js_code)
            if hasattr(self.app_instance, 'current_mol') and self.app_instance.current_mol:
                self.app_instance.update_viewer(self.app_instance.current_mol)
            self.vib_btn.setText("Animate Selected Mode")
            delattr(self, "_animating_mode")
            return
            
        self._animating_mode = mode_idx
        self.vib_btn.setText("Stop Animation")
        
        js_code = f"""
            var atoms = currentModel.selectedAtoms({{}});
            var disps = {json.dumps(disps)};
            if (atoms.length === disps.length) {{
                for (var i = 0; i < atoms.length; i++) {{
                    atoms[i].dx = disps[i][0];
                    atoms[i].dy = disps[i][1];
                    atoms[i].dz = disps[i][2];
                }}
                viewer.vibrate(30, 1.0, true);
                viewer.animate({{loop: "backAndForth"}});
            }} else {{
                console.error("Atom count mismatch: " + atoms.length + " vs " + disps.length);
            }}
        """
        self.app_instance.web_view.page().runJavaScript(js_code)

    def closeEvent(self, event):
        # Stop animation when closing dialog
        js_code = "if (typeof viewer !== 'undefined') { viewer.stopAnimate(); }"
        self.app_instance.web_view.page().runJavaScript(js_code)
        if hasattr(self.app_instance, 'current_mol') and self.app_instance.current_mol:
            self.app_instance.update_viewer(self.app_instance.current_mol)
        super().closeEvent(event)

    def apply_standard_nmr_labels(self):
        """Builds Standard NMR chemical shift labels list and displays them in 3Dmol viewer."""
        labels = {}
        shieldings = self.results.get("nmr_shieldings", {})
        if not shieldings:
            QMessageBox.warning(self, "No NMR data", "No chemical shielding data found to apply.")
            return

        try:
            ref_1h = float(self.ref_1h_input.text().replace(',', '.'))
        except:
            ref_1h = DEFAULT_NMR_REFS["1H"]
        try:
            ref_13c = float(self.ref_13c_input.text().replace(',', '.'))
        except:
            ref_13c = DEFAULT_NMR_REFS["13C"]

        for idx, info in shieldings.items():
            elem = info["element"]
            ref_val = ref_1h if elem == "H" else (ref_13c if elem == "C" else DEFAULT_NMR_REFS.get(f"1{elem}", 0.0))
            shift = ref_val - info["shielding"]
            labels[idx] = f"{elem}{idx}: {shift:.2f} ppm"

        self._show_3d_labels(labels, color='#107c41', title="Standard TMS NMR shifts")

    def apply_standard_avg_nmr_labels(self):
        """Builds Symmetry Averaged Standard NMR chemical shift labels list and displays them in 3Dmol viewer."""
        labels = {}
        shieldings = self.results.get("nmr_shieldings", {})
        if not shieldings:
            QMessageBox.warning(self, "No NMR data", "No chemical shielding data found to apply.")
            return

        try:
            ref_1h = float(self.ref_1h_input.text().replace(',', '.'))
        except:
            ref_1h = DEFAULT_NMR_REFS["1H"]
        try:
            ref_13c = float(self.ref_13c_input.text().replace(',', '.'))
        except:
            ref_13c = DEFAULT_NMR_REFS["13C"]

        computed_shifts = {}
        for idx, info in shieldings.items():
            elem = info["element"]
            ref_val = ref_1h if elem == "H" else (ref_13c if elem == "C" else DEFAULT_NMR_REFS.get(f"1{elem}", 0.0))
            computed_shifts[idx] = ref_val - info["shielding"]

        rank_to_vals = {}
        if self.sym_ranks:
            for idx, val in computed_shifts.items():
                rank = self.sym_ranks.get(idx)
                if rank is not None:
                    if rank not in rank_to_vals:
                        rank_to_vals[rank] = []
                    rank_to_vals[rank].append(val)
        
        rank_to_avg = {}
        for rank, vals in rank_to_vals.items():
            rank_to_avg[rank] = sum(vals) / len(vals)

        for idx, info in shieldings.items():
            elem = info["element"]
            shift = computed_shifts[idx]
            rank = self.sym_ranks.get(idx) if self.sym_ranks else None
            avg_shift = rank_to_avg.get(rank, shift) if rank is not None else shift
            labels[idx] = f"{elem}{idx}: {avg_shift:.2f} ppm"

        self._show_3d_labels(labels, color='#2e7d32', title="Standard TMS NMR shifts (Symmetry Avg.)")

    def apply_tantillo_nmr_labels(self):
        """Builds Tantillo NMR chemical shift labels list and displays them in 3Dmol viewer."""
        labels = {}
        shieldings = self.results.get("nmr_shieldings", {})
        if not shieldings:
            QMessageBox.warning(self, "No NMR data", "No chemical shielding data found to apply.")
            return

        try: h1_s = float(self.tantillo_1h_slope_input.text().replace(',', '.'))
        except: h1_s = None
        try: h1_i = float(self.tantillo_1h_intercept_input.text().replace(',', '.'))
        except: h1_i = None
        try: c13_s = float(self.tantillo_13c_slope_input.text().replace(',', '.'))
        except: c13_s = None
        try: c13_i = float(self.tantillo_13c_intercept_input.text().replace(',', '.'))
        except: c13_i = None

        for idx, info in shieldings.items():
            elem = info["element"]
            tantillo_val = None
            if elem == "H" and h1_s is not None and h1_i is not None and h1_s != 0:
                tantillo_val = (info["shielding"] - h1_i) / h1_s
            elif elem == "C" and c13_s is not None and c13_i is not None and c13_s != 0:
                tantillo_val = (info["shielding"] - c13_i) / c13_s

            if tantillo_val is not None:
                labels[idx] = f"{elem}{idx}: {tantillo_val:.2f} ppm"
            else:
                labels[idx] = f"{elem}{idx}: --"

        self._show_3d_labels(labels, color='#0078D4', title="Tantillo NMR shifts")

    def apply_tantillo_avg_nmr_labels(self):
        """Builds Symmetry Averaged Tantillo NMR chemical shift labels list and displays them in 3Dmol viewer."""
        labels = {}
        shieldings = self.results.get("nmr_shieldings", {})
        if not shieldings:
            QMessageBox.warning(self, "No NMR data", "No chemical shielding data found to apply.")
            return

        try: h1_s = float(self.tantillo_1h_slope_input.text().replace(',', '.'))
        except: h1_s = None
        try: h1_i = float(self.tantillo_1h_intercept_input.text().replace(',', '.'))
        except: h1_i = None
        try: c13_s = float(self.tantillo_13c_slope_input.text().replace(',', '.'))
        except: c13_s = None
        try: c13_i = float(self.tantillo_13c_intercept_input.text().replace(',', '.'))
        except: c13_i = None

        computed_shifts = {}
        for idx, info in shieldings.items():
            elem = info["element"]
            val = None
            if elem == "H" and h1_s is not None and h1_i is not None and h1_s != 0:
                val = (info["shielding"] - h1_i) / h1_s
            elif elem == "C" and c13_s is not None and c13_i is not None and c13_s != 0:
                val = (info["shielding"] - c13_i) / c13_s
            if val is not None:
                computed_shifts[idx] = val

        rank_to_vals = {}
        if self.sym_ranks:
            for idx, val in computed_shifts.items():
                rank = self.sym_ranks.get(idx)
                if rank is not None:
                    if rank not in rank_to_vals:
                        rank_to_vals[rank] = []
                    rank_to_vals[rank].append(val)
        
        rank_to_avg = {}
        for rank, vals in rank_to_vals.items():
            rank_to_avg[rank] = sum(vals) / len(vals)

        for idx, info in shieldings.items():
            elem = info["element"]
            avg_val = "--"
            if idx in computed_shifts:
                val = computed_shifts[idx]
                rank = self.sym_ranks.get(idx) if self.sym_ranks else None
                if rank in rank_to_avg:
                    avg_val = f"{rank_to_avg[rank]:.2f} ppm"
                else:
                    avg_val = f"{val:.2f} ppm"
            else:
                avg_val = "--"
            labels[idx] = f"{elem}{idx}: {avg_val}"

        self._show_3d_labels(labels, color='#2e7d32', title="Tantillo NMR shifts (Symmetry Avg.)")

    def _show_3d_labels(self, labels, color='#107c41', title="NMR shifts"):
        js_code = f"""
            viewer.removeAllLabels();
            var atoms = currentModel.selectedAtoms({{}});
            var labelMap = {json.dumps(labels)};
            for (var i = 0; i < atoms.length; i++) {{
                var atom = atoms[i];
                var serial = atom.serial !== undefined ? atom.serial : i;
                if (labelMap[serial] !== undefined) {{
                    viewer.addLabel(labelMap[serial], {{
                        position: {{x: atom.x, y: atom.y, z: atom.z}}, 
                        backgroundColor: '{color}', 
                        fontColor: 'white', 
                        backgroundOpacity: 0.9, 
                        fontSize: 13
                    }});
                }}
            }}
            viewer.render();
        """
        self.app_instance.web_view.page().runJavaScript(js_code)
        QMessageBox.information(self, "Success", f"{title} applied to 3D viewer.")

    def on_nmr_peak_clicked(self, atom_name):
        try:
            import re
            idx_str = re.findall(r'\d+', atom_name)
            if not idx_str:
                return
            idx = int(idx_str[0])
            
            # Highlight in 3D viewer
            js = f"highlightAtom({idx});"
            self.app_instance.web_view.page().runJavaScript(js)
            
            # Highlight standard table
            self.nmr_std_table.blockSignals(True)
            for r in range(self.nmr_std_table.rowCount()):
                item = self.nmr_std_table.item(r, 0)
                if item and item.text() == f"Atom {idx}":
                    self.nmr_std_table.setCurrentCell(r, 0)
                    self.nmr_std_table.selectRow(r)
                    break
            self.nmr_std_table.blockSignals(False)
            
            # Highlight tantillo table
            self.nmr_tantillo_table.blockSignals(True)
            for r in range(self.nmr_tantillo_table.rowCount()):
                item = self.nmr_tantillo_table.item(r, 0)
                if item and item.text() == f"Atom {idx}":
                    self.nmr_tantillo_table.setCurrentCell(r, 0)
                    self.nmr_tantillo_table.selectRow(r)
                    break
            self.nmr_tantillo_table.blockSignals(False)
        except Exception as e:
            print("Error handling NMR peak click:", e)

    def highlight_atom_from_viewer(self, atom_idx):
        if not hasattr(self, 'nmr_spec_plot'):
            return
        
        nucleus = self.nmr_nuc_combo.currentText() if hasattr(self, 'nmr_nuc_combo') else "1H"
        shieldings = self.results.get("nmr_shieldings", {})
        info = shieldings.get(str(atom_idx))
        if not info:
            return
            
        elem = info["element"]
        atom_name = f"{elem}{atom_idx}"
        expected_elem = "H" if nucleus == "1H" else "C"
        
        if elem == expected_elem:
            self.nmr_spec_plot.highlight_atom(atom_name)
            
        # Highlight standard table
        self.nmr_std_table.blockSignals(True)
        for r in range(self.nmr_std_table.rowCount()):
            item = self.nmr_std_table.item(r, 0)
            if item and item.text() == f"Atom {atom_idx}":
                self.nmr_std_table.setCurrentCell(r, 0)
                self.nmr_std_table.selectRow(r)
                break
        self.nmr_std_table.blockSignals(False)
        
        # Highlight tantillo table
        self.nmr_tantillo_table.blockSignals(True)
        for r in range(self.nmr_tantillo_table.rowCount()):
            item = self.nmr_tantillo_table.item(r, 0)
            if item and item.text() == f"Atom {atom_idx}":
                self.nmr_tantillo_table.setCurrentCell(r, 0)
                self.nmr_tantillo_table.selectRow(r)
                break
        self.nmr_tantillo_table.blockSignals(False)

    def on_std_table_selection_changed(self):
        selected_rows = self.nmr_std_table.selectedItems()
        if not selected_rows:
            return
        row = selected_rows[0].row()
        item = self.nmr_std_table.item(row, 0)
        if item:
            try:
                import re
                idx_str = re.findall(r'\d+', item.text())
                if not idx_str:
                    return
                atom_idx = int(idx_str[0])
                
                # Highlight in 3D viewer
                js = f"highlightAtom({atom_idx});"
                self.app_instance.web_view.page().runJavaScript(js)
                
                # Highlight in plot widget
                shieldings = self.results.get("nmr_shieldings", {})
                info = shieldings.get(str(atom_idx))
                if info:
                    self.nmr_spec_plot.highlight_atom(f"{info['element']}{atom_idx}")
            except Exception as e:
                print("Error from standard table selection change:", e)

    def on_tantillo_table_selection_changed(self):
        selected_rows = self.nmr_tantillo_table.selectedItems()
        if not selected_rows:
            return
        row = selected_rows[0].row()
        item = self.nmr_tantillo_table.item(row, 0)
        if item:
            try:
                import re
                idx_str = re.findall(r'\d+', item.text())
                if not idx_str:
                    return
                atom_idx = int(idx_str[0])
                
                # Highlight in 3D viewer
                js = f"highlightAtom({atom_idx});"
                self.app_instance.web_view.page().runJavaScript(js)
                
                # Highlight in plot widget
                shieldings = self.results.get("nmr_shieldings", {})
                info = shieldings.get(str(atom_idx))
                if info:
                    self.nmr_spec_plot.highlight_atom(f"{info['element']}{atom_idx}")
            except Exception as e:
                print("Error from tantillo table selection change:", e)

    def fill_orbitals_table(self):
        self.orbitals_table.setRowCount(0)
        if not hasattr(self, 'parsed_orbitals') or not self.parsed_orbitals:
            return
            
        self.orbitals_table.setRowCount(len(self.parsed_orbitals))
        homo_row = -1
        
        for row, orb in enumerate(self.parsed_orbitals):
            item_num = QTableWidgetItem(str(orb["num"]))
            item_num.setTextAlignment(Qt.AlignCenter)
            self.orbitals_table.setItem(row, 0, item_num)
            
            item_occ = QTableWidgetItem(f"{orb['occ']:.4f}")
            item_occ.setTextAlignment(Qt.AlignCenter)
            self.orbitals_table.setItem(row, 1, item_occ)
            
            item_ev = QTableWidgetItem(f"{orb['energy_ev']:.4f}")
            item_ev.setTextAlignment(Qt.AlignCenter)
            self.orbitals_table.setItem(row, 2, item_ev)
            
            type_str = ""
            if orb["is_homo"]:
                type_str = "HOMO"
                homo_row = row
            elif orb["is_lumo"]:
                type_str = "LUMO"
            
            item_type = QTableWidgetItem(type_str)
            item_type.setTextAlignment(Qt.AlignCenter)
            if type_str:
                font = item_type.font()
                font.setBold(True)
                item_type.setFont(font)
                if type_str == "HOMO":
                    item_type.setForeground(QColor("#00c853"))
                else:
                    item_type.setForeground(QColor("#d50000"))
            self.orbitals_table.setItem(row, 3, item_type)
            
        if homo_row != -1:
            self.orbitals_table.selectRow(homo_row)

    def _resolve_orca_plot(self):
        import shutil
        # 1. Try to find orca_plot directly in PATH
        resolved = shutil.which("orca_plot")
        if resolved:
            return os.path.abspath(resolved)
            
        # 2. Try to find it in the same directory as orca
        orca_path = shutil.which("orca")
        if orca_path:
            orca_dir = os.path.dirname(orca_path)
            for name in ["orca_plot.exe", "orca_plot"]:
                exe_path = os.path.join(orca_dir, name)
                if os.path.exists(exe_path):
                    return os.path.abspath(exe_path)
                    
        # 3. Fallback
        return "orca_plot.exe" if sys.platform == "win32" else "orca_plot"

    def visualize_selected_orbital(self):
        row = self.orbitals_table.currentRow()
        if row < 0 or row >= len(self.parsed_orbitals):
            QMessageBox.warning(self, "Selection Error", "Please select an orbital from the table first.")
            return
            
        orb = self.parsed_orbitals[row]
        orbital_num = orb["num"]
        isoval = self.orb_isoval_spin.value()
        
        job_dir = self.job_manager.get_job_dir(self.job_id)
        orca_plot_exe = self._resolve_orca_plot()
        
        self.app_instance.statusBar().showMessage(f"Generating cube file for Orbital {orbital_num}...")
        
        self.visualize_orb_btn.setEnabled(False)
        self.visualize_orb_btn.setText("Generiere...")
        
        from PyQt5.QtCore import QCoreApplication
        QCoreApplication.processEvents()
        
        cube_file, err_details = generate_orbital_cube(job_dir, orca_plot_exe, orbital_num)
        
        self.visualize_orb_btn.setEnabled(True)
        self.visualize_orb_btn.setText("Orbital visualisieren")
        
        if not cube_file or not os.path.exists(cube_file):
            self.app_instance.statusBar().showMessage("Error: orca_plot failed.")
            if "RESCUE" in err_details or "Cannot open GBW" in err_details:
                QMessageBox.critical(self, "Error", 
                    f"Failed to generate cube file for Orbital {orbital_num}.\n\n"
                    "The wavefunction file (.gbw) is incompatible with the currently installed ORCA version.\n"
                    "This usually happens when trying to visualize orbitals of a job calculated with an older ORCA version (e.g., ORCA 5 vs ORCA 6).")
            else:
                QMessageBox.critical(self, "Error", 
                    f"Failed to generate cube file for Orbital {orbital_num}.\n"
                    f"Make sure orca_plot is installed and in the system PATH.\n\nDetails:\n{err_details}")
            return
            
        try:
            with open(cube_file, "r", encoding="utf-8", errors="ignore") as f:
                cube_content = f.read()
                
            js = f"loadOrbital({json.dumps(cube_content)}, {isoval});"
            self.app_instance.web_view.page().runJavaScript(js)
            self.app_instance.statusBar().showMessage(f"Visualized Orbital {orbital_num} (Isovalue: {isoval})")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load orbital in 3D viewer:\n{e}")

    def visualize_density(self):
        isoval = self.orb_isoval_spin.value()
        job_dir = self.job_manager.get_job_dir(self.job_id)
        orca_plot_exe = self._resolve_orca_plot()
        
        self.app_instance.statusBar().showMessage("Generating cube file for Electron Density...")
        
        self.visualize_dens_btn.setEnabled(False)
        self.visualize_dens_btn.setText("Generiere...")
        
        from PyQt5.QtCore import QCoreApplication
        QCoreApplication.processEvents()
        
        cube_file, err_details = generate_density_cube(job_dir, orca_plot_exe)
        
        self.visualize_dens_btn.setEnabled(True)
        self.visualize_dens_btn.setText("Elektronendichte visualisieren")
        
        if not cube_file or not os.path.exists(cube_file):
            self.app_instance.statusBar().showMessage("Error: orca_plot failed.")
            if "RESCUE" in err_details or "Cannot open GBW" in err_details:
                QMessageBox.critical(self, "Error", 
                    "Failed to generate electron density cube file.\n\n"
                    "The wavefunction file (.gbw) is incompatible with the currently installed ORCA version.\n"
                    "This usually happens when trying to visualize density of a job calculated with an older ORCA version (e.g., ORCA 5 vs ORCA 6).")
            else:
                QMessageBox.critical(self, "Error", 
                    "Failed to generate electron density cube file.\n"
                    f"Make sure orca_plot is installed and in the system PATH.\n\nDetails:\n{err_details}")
            return
            
        try:
            with open(cube_file, "r", encoding="utf-8", errors="ignore") as f:
                cube_content = f.read()
                
            js = f"loadDensity({json.dumps(cube_content)}, {isoval});"
            self.app_instance.web_view.page().runJavaScript(js)
            self.app_instance.statusBar().showMessage(f"Visualized Electron Density (Isovalue: {isoval})")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load density in 3D viewer:\n{e}")

    def clear_orbital_visualization(self):
        js = "clearSurfaces();"
        self.app_instance.web_view.page().runJavaScript(js)
        if hasattr(self.app_instance, "set_method_badge"):
            self.app_instance.set_method_badge("")
        self.app_instance.statusBar().showMessage("Orbitals/Density cleared.")


class OrcaJobManagerWidget(QWidget):
    def __init__(self, workspace_dir, app_instance):
        super().__init__()
        self.workspace_dir = workspace_dir
        self.app_instance = app_instance
        self.job_manager = OrcaJobManager(workspace_dir)

        # Style
        self.setStyleSheet("""
            QWidget { background-color: #1e1e1e; color: white; }
            QTableWidget { background-color: #252525; color: white; gridline-color: #333; border: 1px solid #444; }
            QPushButton { background-color: #333; color: white; border: none; padding: 6px 12px; border-radius: 4px; }
            QPushButton:hover { background-color: #444; }
            QHeaderView::section { background-color: #2d2d2d; color: white; padding: 4px; border: 1px solid #333; }
        """)

        layout = QVBoxLayout(self)

        # Top controls
        h_ctrl = QHBoxLayout()
        self.btn_refresh = QPushButton("\u21bb Refresh Queue")
        self.btn_refresh.clicked.connect(self.refresh_queue)
        h_ctrl.addWidget(self.btn_refresh)
        
        self.btn_cancel = QPushButton("Cancel Job")
        self.btn_cancel.clicked.connect(self.cancel_selected)
        h_ctrl.addWidget(self.btn_cancel)

        self.btn_delete = QPushButton("Delete Job")
        self.btn_delete.setStyleSheet("background-color: #c42b1c;")
        self.btn_delete.clicked.connect(self.delete_selected)
        h_ctrl.addWidget(self.btn_delete)

        self.btn_log = QPushButton("Show Log")
        self.btn_log.clicked.connect(self.show_log)
        h_ctrl.addWidget(self.btn_log)

        self.btn_load_geom = QPushButton("Load Optimized Geometry")
        self.btn_load_geom.clicked.connect(self.load_geometry)
        h_ctrl.addWidget(self.btn_load_geom)

        self.btn_results = QPushButton("View Results")
        self.btn_results.setStyleSheet("background-color: #0078D4;")
        self.btn_results.clicked.connect(self.view_results)
        h_ctrl.addWidget(self.btn_results)

        h_ctrl.addStretch()
        layout.addLayout(h_ctrl)

        # Table
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Job Name", "Status", "Task", "Runtime", "Created"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.table)

        # Automatic status update timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_queue)
        self.timer.start(5000) # update status every 5s

        self.refresh_queue()

    def refresh_queue(self):
        selected_row = self.table.currentRow()
        selected_job_id = None
        if selected_row >= 0:
            selected_job_id = self.jobs[selected_row]["id"]

        self.jobs = self.job_manager.list_jobs()
        self.table.setRowCount(0)

        for job in self.jobs:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(job["name"]))
            
            # Color coding for status
            status_item = QTableWidgetItem(job["status"])
            if job["status"] == "completed":
                status_item.setForeground(QColor("#54b354"))
            elif job["status"] == "failed":
                status_item.setForeground(QColor("#f85149"))
            elif job["status"] == "running":
                status_item.setForeground(QColor("#58a6ff"))
            self.table.setItem(row, 1, status_item)

            self.table.setItem(row, 2, QTableWidgetItem(job["task"]))
            self.table.setItem(row, 3, QTableWidgetItem(job["runtime"]))
            
            created_str = job["created"]
            if "T" in created_str:
                created_str = created_str.split("T")[1][:8]
            self.table.setItem(row, 4, QTableWidgetItem(created_str))

        # Re-select row if possible
        if selected_job_id:
            for idx, job in enumerate(self.jobs):
                if job["id"] == selected_job_id:
                    self.table.selectRow(idx)
                    break

    def get_selected_job(self):
        row = self.table.currentRow()
        if row >= 0 and row < len(self.jobs):
            return self.jobs[row]
        return None

    def cancel_selected(self):
        job = self.get_selected_job()
        if job:
            self.job_manager.kill_job(job["id"])
            self.refresh_queue()

    def show_log(self):
        job = self.get_selected_job()
        if job:
            dlg = LogViewerDialog(self, job["id"], self.job_manager)
            dlg.exec_()

    def delete_selected(self):
        job = self.get_selected_job()
        if job:
            reply = QMessageBox.question(
                self, "Confirm Delete", 
                f"Are you sure you want to delete the job '{job['name']}'? All calculation files will be permanently removed.",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.job_manager.delete_job(job["id"])
                self.refresh_queue()

    def load_geometry(self, quiet=False):
        job = self.get_selected_job()
        if job:
            results = self.job_manager.parse_results(job["id"])
            if results["optimized_xyz"]:
                from rdkit import Chem
                try:
                    mol = Chem.MolFromXYZBlock(results["optimized_xyz"])
                    if mol:
                        # RDKit MolFromXYZBlock returns mol without bonds, but we can construct them from SMILES or connect atoms
                        # Standard way to keep bonds: if there is an existing structure in the viewer, apply coordinates to it!
                        task = job.get("task", "Opt")
                        use_sep = job.get("use_sep_nmr", False)
                        if "NMR" in task and use_sep:
                            func = job.get("nmr_method") or job.get("functional") or job.get("method", "B3LYP")
                            basis = job.get("nmr_basis") or job.get("basis", "")
                        else:
                            func = job.get("functional") or job.get("method", "B3LYP")
                            basis = job.get("basis", "")
                        b_str = f" / {basis}" if basis else ""
                        self.app_instance.set_method_badge(f"ORCA: {func}{b_str} ({task})")

                        if hasattr(self.app_instance, 'current_mol') and self.app_instance.current_mol:
                            target_mol = self.app_instance.current_mol
                            if target_mol.GetNumAtoms() == mol.GetNumAtoms():
                                conf = target_mol.GetConformer()
                                for i in range(mol.GetNumAtoms()):
                                    pos = mol.GetConformer().GetAtomPosition(i)
                                    conf.SetAtomPosition(i, pos)
                                self.app_instance.update_viewer(target_mol)
                                if not quiet:
                                    QMessageBox.information(self, "Success", "Applied optimized coordinates to current structure.")
                                return
                        
                        self.app_instance.statusBar().showMessage("Displaying geometry coordinates from ORCA...")
                        try:
                            from rdkit.Chem import rdDetermineBonds
                            charge = job.get("charge", 0)
                            rdDetermineBonds.DetermineBonds(mol, charge=charge)
                        except Exception as ex:
                            print("Could not determine bonds:", ex)
                        
                        self.app_instance.update_viewer(mol)
                        if not quiet:
                            QMessageBox.information(self, "Loaded", "Optimized geometry loaded directly into 3D viewer.")

                    else:
                        if not quiet:
                            QMessageBox.warning(self, "Parse Error", "Failed to build molecule from optimized XYZ.")
                except Exception as e:
                    if not quiet:
                        QMessageBox.warning(self, "Error", f"Could not load optimized geometry: {e}")
            else:
                if not quiet:
                    QMessageBox.warning(self, "No Geometry", "No optimized geometry coordinates found.")

    def view_results(self):
        job = self.get_selected_job()
        if job:
            if job["status"] == "running":
                QMessageBox.information(self, "Running", "The calculation is still running. Please wait.")
                return
            
            # Automatically load optimized geometry if available
            results = self.job_manager.parse_results(job["id"])
            if results.get("optimized_xyz"):
                self.load_geometry(quiet=True)
                
            self.results_dialog = OrcaResultsDialog(self, job["id"], self.job_manager, self.app_instance)
            self.results_dialog.setWindowModality(Qt.NonModal)
            self.results_dialog.show()
