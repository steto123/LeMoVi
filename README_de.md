# LeMoVi - Lehniner Molekül Visualisierer

<p align="center">
  <img src="lemovi-logo.png" alt="LeMoVi Logo" width="400">
</p>

Dieses Projekt ermöglicht die Eingabe von chemischen Strukturen über den 2D-Editor **Ketcher**, führt eine Geometrieoptimierung durch (mittels **RDKit** oder **xTB**) und stellt das Ergebnis interaktiv in **3D** (3Dmol.js) dar.

## Start
1. Führen Sie `create_portable_python.bat` aus, um die notwendige Python-Umgebung zu erstellen (nur beim ersten Mal).
2. Starten Sie das Programm mit `start.bat`.

## Funktionen
- **2D-Input**: Vollständiger Ketcher-Editor integriert.
- **Geometrie-Optimierung**: 
  - Schnelle molekülmechanische Optimierung (**MMFF94** via RDKit) inklusive automatischer Retry-Logik und Fallback auf UFF bei fehlenden Parametern.
  - Präzise semiempirische quantenchemische Optimierung (**GFN2-xTB**) (siehe Setup unten) mit robustem Restart-Mechanismus.
- **Visualisierung**: Interaktive 3D-Ansicht (Vollständig Offline-fähig). Wahlweise Sticks, CPK, Wireframe oder Ball & Stick.
- **Interaktive Messungen**: Klicken Sie in der 3D-Ansicht auf Atome, um diese zu vermessen (inklusive visueller Verbindungslinien):
  - 2 Atome = Bindungslänge / Distanz (Å)
  - 3 Atome = Bindungswinkel (°)
  - 4 Atome = Torsions- / Diederwinkel (°)
- **Oberflächen-Visualisierung**: Berechnung und Darstellung molekularer Eigenschaften:
  - **Molekulare Oberflächen**: Van der Waals (VDW), Solvent Accessible Surface (SAS) und Connolly-Oberfläche (Molecular Surface).
  - **Elektrostatisches Potential (ESP)**: Farbzuordnung basierend auf Gasteiger-Partialladungen (Rot = negativ, Blau = positiv).
  - **Hydrophobizität (LogP)**: Visualisierung von polaren und lipophilen Regionen basierend auf Crippen-LogP-Beiträgen.
  - **Polarisierbarkeit (MR)**: Visuelle Darstellung der Molaren Refraktivität / Deformierbarkeit.
  - **Wasserstoffbrücken**: Hervorhebung von H-Brücken-Akzeptoren (Rot) und Donatoren (Blau).
- **Dateiverwaltung & Integrationen**:
  - **Dateimenü**: Importieren und Exportieren von Molekülen in verschiedenen Formaten (SDF, MOL, PDB, SMILES).
  - **PubChem Integration**: Suche und importiere Moleküle direkt über ihren Namen aus der PubChem-Datenbank.
  - **Molecule-Overlay**: Lade mehrere Moleküle in den gleichen Viewer, um ihre Strukturen direkt miteinander zu vergleichen.
  - **Setup-Dialog**: Intuitiver Dialog zur Konfiguration quantenchemischer Rechnungen (Aufgaben: `Opt`, `Freq`, `NMR`, `Single Point` sowie Kombinationen; Methoden: DFT-Funktionale wie `B3LYP`, `PBE0`, `wB97X-D4`, `r2SCAN-3c`, HF/semi-empirisch oder Post-HF wie `MP2` und `DLPNO-CCSD(T)`).
  - **Umfangreiche Basissätze**: Einfache Auswahl von Ahlrichs `def2`, minimal augmentierten `ma-def2`, Jensens `pcseg` (für DFT-Eigenschaften), Dunnings korrelationskonsistenten `cc-pV*Z` (für Wellenfunktionsmethoden) und älteren Pople `6-31G`-Basissätzen. Siehe [ORCA_Basis_Sets_de.md](file:///f:/projekte26/lemovi-for-windows/LeMoVi/ORCA_Basis_Sets_de.md) für detaillierte Richtlinien.
  - **Lösungsmittelmodelle & DRACO**: Auswahl impliziter Lösungsmittelmodelle (`CPCM`, `SMD` oder `PCM`) für 12 gängige Lösungsmittel (z.B. Chloroform, DMSO, Aceton). Lösungsmittel können für die Geometrieoptimierung und den NMR-Schritt **separat** konfiguriert werden. Unterstützt die Aktivierung von `DRACO`-Radien für ORCA 6+.
  - **Tantillo/CHESHIRE Skalierung**: Anwendung von Skalierungsfaktoren ($ \delta = \text{intercept} + \text{slope} \times \sigma $) für GIAO-NMR-Berechnungen direkt aus einer Datenbank mit 64 vordefinierten CHESHIRE-Literaturwerten. Das System wählt automatisch den besten Treffer basierend auf NMR-Methode, Basissatz und Lösungsmittel/Modell aus. Enthält einen interaktiven Betrachter und Editor für die Skalierungsdatenbank.
  - **Dispersionskorrekturen**: Native Unterstützung für Grimmes `D4`- und `D3BJ`-Dispersionskorrekturen.
  - **Job-Manager**: Hintergrund-Job-Warteschlange. Überwache den Ausführungsstatus, betrachte das Live-Protokoll (`orca_output.out`), beende Berechnungen und lade optimierte Geometrien direkt zurück in den 3D-Viewer.

## xTB Integration (Optional)
Um die xTB-Optimierung nutzen zu können, muss die externe Binary hinterlegt werden:
1. Laden Sie die aktuelle Windows-Version von xTB (`xtb-X.X.X-windows-x86_64.zip`) herunter: [Grimme-Lab xTB Releases](https://github.com/grimme-lab/xtb/releases)
2. Entpacken Sie die Datei.
3. Erstellen Sie im Verzeichnis `LeMoVi` einen neuen Unterordner namens `xtb`.
4. Kopieren Sie die ausführbare Datei `xtb.exe` in diesen Ordner. Der Pfad muss lauten: `LeMoVi\xtb\xtb.exe`
5. Das Programm erkennt xTB nun automatisch bei der Auswahl im Dropdown-Menü.

## ORCA-Integration einrichten (Optional)
Um ORCA-Berechnungen durchzuführen, muss ORCA auf Ihrem System installiert sein:
1. Laden Sie ORCA (vorzugsweise Version 6.x) aus dem offiziellen [Orca Forum / Portal](https://orcaforum.kofo.mpg.de/) herunter.
2. Installieren Sie ORCA auf Ihrem System und fügen Sie das Verzeichnis mit der `orca.exe`-Datei zur System-Umgebungsvariable `PATH` hinzu.
3. LeMoVi ruft `orca` direkt auf. Stellen Sie sicher, dass die ausführbare Datei über die Befehlszeile erreichbar ist (Sie können dies überprüfen, indem Sie `orca` in einer Eingabeaufforderung eingeben).

## Anforderungen
Das Programm ist als portable Anwendung konzipiert und benötigt eine installierte Python-Umgebung im Unterordner `portable_python` (wird durch das Skript erstellt).
Benötigte Bibliotheken:
- PyQt5
- PyQtWebEngine
- rdkit
