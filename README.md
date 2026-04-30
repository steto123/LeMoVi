# LeMoVi - Lehniner Molekül Visualisierer

Dieses Projekt ermöglicht die Eingabe von chemischen Strukturen über den 2D-Editor **Ketcher**, führt eine Geometrieoptimierung durch (mittels **RDKit** oder **xTB**) und stellt das Ergebnis interaktiv in **3D** (3Dmol.js) dar.

## Start
1. Führen Sie `create_portable_python.bat` aus, um die notwendige Python-Umgebung zu erstellen (nur beim ersten Mal).
2. Starten Sie das Programm mit `start.bat`.

## Funktionen
- **2D-Input**: Vollständiger Ketcher-Editor integriert.
- **Geometrie-Optimierung**: 
  - Schnelle molekülmechanische Optimierung (**MMFF94** via RDKit).
  - Präzise semiempirische quantenchemische Optimierung (**GFN2-xTB**) (siehe Setup unten).
- **Visualisierung**: Interaktive 3D-Ansicht (Vollständig Offline-fähig). Wahlweise Sticks, CPK, Wireframe oder Ball & Stick.
- **Interaktive Messungen**: Klicken Sie in der 3D-Ansicht auf Atome, um diese zu vermessen:
  - 2 Atome = Bindungslänge / Distanz (Å)
  - 3 Atome = Bindungswinkel (°)
  - 4 Atome = Torsions- / Diederwinkel (°)
- **Oberflächen-Visualisierung**: Berechnung und Darstellung molekularer Oberflächen:
  - **Van der Waals (VDW)** und **Solvent Accessible Surface (SAS)**.
  - **Electrostatic Potential (ESP)**: Farbzuordnung basierend auf Gasteiger-Partialladungen (Rot = negativ, Blau = positiv).
  - **Hydrophobicity (LogP)**: Visualisierung von polaren und lipophilen Regionen basierend auf Crippen-LogP-Beiträgen.

## xTB Integration (Optional)
Um die xTB-Optimierung nutzen zu können, muss die externe Binary hinterlegt werden:
1. Laden Sie die aktuelle Windows-Version von xTB (`xtb-X.X.X-windows-x86_64.zip`) herunter: [Grimme-Lab xTB Releases](https://github.com/grimme-lab/xtb/releases)
2. Entpacken Sie die Datei.
3. Erstellen Sie im Verzeichnis `LeMoVi` einen neuen Unterordner namens `xtb`.
4. Kopieren Sie die ausführbare Datei `xtb.exe` in diesen Ordner. Der Pfad muss lauten: `LeMoVi\xtb\xtb.exe`
5. Das Programm erkennt xTB nun automatisch bei der Auswahl im Dropdown-Menü.

## Anforderungen
Das Programm ist als portable Anwendung konzipiert und benötigt eine installierte Python-Umgebung im Unterordner `portable_python` (wird durch das Skript erstellt).
Benötigte Bibliotheken:
- PyQt5
- PyQtWebEngine
- rdkit
