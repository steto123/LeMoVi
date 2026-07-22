# ORCA Basissätze: Empfohlene Anwendungen und Limitierungen

Dieses Dokument beschreibt die in **LeMoVi** integrierten Basissätze für **ORCA 6**, ihre optimalen Anwendungsbereiche sowie ihre Limitierungen.

---

## 1. Übersicht der Basissatz-Familien

### A. Karlsruhe / Ahlrichs Basissätze (`def2-` Familie)
Die `def2`-Sätze (entwickelt von der Arbeitsgruppe Ahlrichs) sind der **De-facto-Standard** in ORCA. Sie sind über das gesamte Periodensystem hinweg konsistent definiert und hochgradig für ORCA-Rechenbeschleunigungen (wie RI-J und RI-JK) optimiert.

* **`def2-SVP`** (Split-Valence Polarization, Double-Zeta)
  * **Anwendung:** Schnelle Geometrieoptimierungen, Frequenzberechnungen sehr großer Moleküle, Vorab-Checks.
  * **Limitierung:** Zu ungenau für verlässliche thermochemische Energien (Reaktionsbarrieren, Bindungsenergien).
* **`def2-TZVP`** (Triple-Zeta Valence Polarization)
  * **Anwendung:** Der "Workhorse"-Basissatz für Dichtefunktionaltheorie (DFT). Hervorragend für verlässliche Geometrien, Frequenzen und thermodynamische Daten.
  * **Limitierung:** Für hochgenaue quantenchemische Post-HF-Methoden (wie DLPNO-CCSD(T)) ist die Polarisierung teilweise nicht ausreichend.
* **`def2-TZVPP`** (Triple-Zeta Valence Double-Polarization)
  * **Anwendung:** Standardempfehlung für Wellenfunktions-Methoden (MP2, DLPNO-CCSD(T)). Besitzt zusätzliche Polarisationsfunktionen.
* **`def2-QZVP`** (Quadruple-Zeta)
  * **Anwendung:** Benchmarks, sehr hohe Genauigkeit, Abschätzung des Basissatz-Limits.
  * **Limitierung:** Extrem rechenintensiv; der Gewinn an Genauigkeit steht für Standard-DFT-Rechnungen oft in keinem Verhältnis zum Rechenaufwand.
* **`def2-mSVP`** (Modified SVP)
  * **Anwendung:** Modifizierter SVP-Basissatz, optimiert für semi-numerische DFT-Methoden.

---

### B. Minimally Augmented def2 Basissätze (`ma-def2-` Familie)
Um diffuse Funktionen zu nutzen (wichtig für freie Elektronenpaare, Anionen und angeregte Zustände), sind klassische augmented Basissätze oft extrem rechenaufwendig und neigen zu linearer Abhängigkeit. ORCA umgeht dies mit der `ma-def2`-Familie.

* **`ma-def2-SVP` / `ma-def2-TZVP` / `ma-def2-TZVPP`**
  * **Anwendung:** **Anionen, angeregte Zustände (TD-DFT), NMR-Schirmungen, optische Rotationen, schwache Wechselwirkungen (z. B. Wasserstoffbrücken).** Es werden nur an den elektronegativsten Atomen diffuse Funktionen angefügt.
  * **Limitierung:** Leicht ungenauer als vollstängig augmentierte Sätze bei extrem kleinen Systemen, was jedoch bei mittleren bis großen Systemen durch die drastische Rechenzeitersparnis mehr als wettgemacht wird.

---

### C. Jensen's Polarization Consistent Basissätze (`pcseg-n` Familie)
Die `pcseg`-Familie wurde von Frank Jensen gezielt für **DFT-Berechnungen** entworfen.

* **`pcseg-1`** (Double-Zeta) / **`pcseg-2`** (Triple-Zeta) / **`pcseg-3`** (Quadruple-Zeta)
  * **Anwendung:** DFT-Berechnungen von Moleküleigenschaften (z. B. NMR-chemische Verschiebungen, Hyperfeinstruktur-Kopplungen). Sie konvergieren für DFT-Funktionale systematischer und schneller gegen das Basissatzlimit als die `def2`-Familie.
* **`aug-pcseg-1` / `aug-pcseg-2`**
  * **Anwendung:** Wie oben, jedoch für Systeme, die diffuse Funktionen erfordern (z. B. Moleküle im angeregten Zustand oder Anionen).
  * **Limitierung:** Weniger verbreitet als die `def2`-Familie, weshalb Vergleiche mit Literaturwerten schwerer fallen können. Auxiliary-Basissätze für RI-Näherungen müssen in manchen Fällen manuell zugewiesen werden (obwohl ORCA 6 vieles automatisch löst).

---

### D. Dunning's Korrelationskonsistente Basissätze (`cc-pV*Z` Familie)
Die klassischen Basissätze für Post-Hartree-Fock-Verfahren.

* **`cc-pVDZ` / `cc-pVTZ` / `cc-pVQZ`**
  * **Anwendung:** Systematische Extrapolationsrechnungen (Complete Basis Limit - CBS) für hochgenaue Ab-initio-Methoden wie CCSD(T) oder MP2.
* **`aug-cc-pVDZ` / `aug-cc-pVTZ` / `aug-cc-pVQZ`**
  * **Anwendung:** Wie oben, jedoch mit diffusen Funktionen für angeregte Zustände (CASSCF/NEVPT2/TD-DFT) und Dispersionswechselwirkungen.
  * **Limitierung:** **Sehr hoher Rechenaufwand.** Auf großen Molekülen neigen die diffusen Funktionen auf Wasserstoffen (`aug-`) zu numerischen Instabilitäten (lineare Abhängigkeiten im Basissatz). Für DFT-Rechnungen sind diese Sätze meist ineffizient; nutzen Sie stattdessen `def2-TZVP` oder `pcseg-2`.

---

### E. Pople-Basissätze (Die Klassiker)
* **`6-31G` / `6-31G*` / `6-31G**` / `6-31+G*` / `6-31++G**`
  * **Anwendung:** Vergleich mit älteren Literaturdaten oder Legacy-Projekten.
  * **Limitierung:** **Veraltet.** Für moderne Rechnungen sollten Pople-Basissätze vermieden werden. Sie weisen systematische Fehler auf (insbesondere bei Übergangsmetallen, wo sie oft nicht wohldefiniert sind) und bieten ein schlechteres Verhältnis von Rechenzeit zu Genauigkeit im Vergleich zur modernen `def2`-Familie (z.B. ist `def2-SVP` fast immer besser und schneller als `6-31G*`).

---

## 2. Praktische Empfehlungen für typische Aufgaben in ORCA 6

| Aufgabe | Empfohlener Basissatz | Zusatz-Tipp |
| :--- | :--- | :--- |
| **DFT Geometrieoptimierung / Frequenzen** | `def2-TZVP` | Standard für zuverlässige Strukturen und Thermochemie. |
| **Schnelles Screening / Riesige Systeme** | `def2-SVP` | Für Struktur-Vorauswahlen. |
| **Post-HF / Wellenfunktion (DLPNO-CCSD(T))** | `def2-TZVPP` oder `cc-pVTZ` | Wichtig für genaue Korrelationsenergien. |
| **NMR Chemische Verschiebungen** | `pcseg-2` oder `ma-def2-TZVP` | Diffuse/polarisierte Funktionen sind hier kritisch. |
| **Berechnung von Anionen / Rydberg-Zuständen** | `ma-def2-TZVP` | Minimiert Rechenzeit bei hoher Qualität für diffuse Ladungen. |
| **Kristallpackungen / Schwache Wechselwirkungen** | `def2-TZVP` + Dispersion (`D4`) | Dispersionkorrekturen korrigieren Basissatz-Superpositionsfehler (BSSE). |

---

## 3. Wichtige Regeln & Limitierungen in ORCA

1. **Kein "Mischmasch" innerhalb eines Moleküls:**
   Vermeiden Sie es, verschiedene Basissatz-Familien (z. B. `6-31G*` für Kohlenstoff und `def2-SVP` für Wasserstoff) zu mischen, es sei denn, Sie tun dies gezielt im Rahmen einer QM/MM- oder ONIOM-Rechnung. Dies führt zu unphysikalischen Ladungsverteilungen und Fehlern.
2. **Nutzen Sie die RI-Näherung (Resolution of Identity):**
   ORCA verwendet standardmäßig RI für DFT und MP2. ORCA wählt automatisch den passenden Hilfsbasissatz (Auxiliary Basis Set, z. B. `def2/J` oder `def2-TZVP/C`). Bei Verwendung von Dunning-Sätzen oder sehr exotischen Basissätzen kann es vorkommen, dass ORCA keine passenden Hilfsbasissätze in der internen Bibliothek findet.
3. **Schwere Elemente (Übergangsmetalle ab der 4. Periode, Lanthanoide):**
   Für Elemente schwerer als Krypton müssen Pseudopotentiale (ECPs) verwendet werden. Die `def2`-Basissätze haben eingebaute ECPs für diese Elemente, was sie extrem benutzerfreundlich macht. Pople-Sätze (`6-31G*`) unterstützen diese Elemente oft gar nicht oder nur unzureichend.

---

## 4. Fortgeschrittene Orca-Features im LeMoVi-Interface

### A. Pre-Flight-Assistent (Eingabeprüfung)
Vor dem Abschicken eines Jobs führt LeMoVi automatische Überprüfungen durch:
* **Spin-Multiplizität:** Prüft, ob die angegebene Multiplizität physikalisch zur Elektronenanzahl passt (Gerade Elektronenanzahl $\rightarrow$ ungerade Multiplizität; ungerade Elektronenanzahl $\rightarrow$ gerade Multiplizität). Bei Fehlern wird ein Vorschlag zur automatischen Korrektur angezeigt.
* **Schwermetall-Warnung:** Enthält das Molekül Elemente mit einer Ordnungszahl $Z > 20$ (wie Übergangsmetalle) und ist ein Pople-Basissatz (`6-31G`) ausgewählt, warnt das System vor ungenauen Ergebnissen und empfiehlt `def2`-Basissätze.
* **Erreichbarkeitsprüfung:** Das System prüft, ob die ausführbare Datei `orca` im Pfad liegt und warnt, falls die Berechnung nicht gestartet werden kann.

### B. Thermodynamik-Zusammenfassung
Nach Frequenzrechnungen (`Freq`) werden im Ergebnis-Dialog unter **Thermodynamics** folgende Werte übersichtlich aufgeführt:
* **Enthalpie ($H$)** und **Gibbs freie Energie ($G$)** in Hartree ($E_h$).
* **Entropie-Korrektur ($T \cdot S$)** bei $298.15\text{ K}$.
* **Dipolmoment** in Debye (inklusive der Richtungskomponenten).

### C. NMR Chemische Verschiebungen & TMS-Referenzdatenbank
Berechnete isotrope Abschirmungen ($\sigma$) werden anhand standardisierter oder benutzerspezifischer TMS-Referenzwerte in chemische Verschiebungen ($\delta$, ppm) umgerechnet:
$$\delta = \sigma_{\text{ref}} - \sigma_{\text{berechnet}}$$

LeMoVi enthält eine integrierte, vollständig erweiterbare **TMS-Referenzdatenbank** (`tms_references.json`) mit über 30 Quantenchemie- und Experiment-Referenzwerten für $^1\text{H}$ und $^{13}\text{C}$ (z. B. HF, B3LYP, MP2, BP86, WP04 sowie experimentelle Gas- und Flüssigkeitswerte).
* **Automatische Empfehlung:** Nach Abschluss eines NMR-Jobs schlägt das System automatisch den optimal passenden TMS-Referenzwert für das gewählte Funktional und den Basissatz vor.
* **Benutzerdefinierte Anpassung:** Über den Button **TMS-Referenzen...** können Anwender beliebige Referenzwerte einsehen, filtern, bearbeiten, neue Werte hinzufügen oder Einträge löschen.
* **Tantillo-Skalierung (`tantillo_scaling.json`):** Neben der TMS-Standardmethode unterstützt LeMoVi die lineare Skalierung nach Tantillo et al. ($\delta = (\sigma_{\text{calc}} - \text{Intercept}) / \text{Slope}$). Über den Button **Tantillo-Skalierungen...** können Nutzer alle Steigungen und Achsenabschnitte für verschiedene Funktional/Basissatz-Kombinationen ansehen, bearbeiten und neue hinzufügen.
* **3D-Darstellung:** Die berechneten Verschiebungen können als schwebende Labels direkt im interaktiven 3D-Viewer auf den jeweiligen Atomen angezeigt werden.



### D. IR-Spektren & Schwingungs-Animationen
Unter **Vibrational Frequencies** werden alle berechneten Moden mit Frequenzen und IR-Intensitäten gelistet:
* Durch Auswählen einer Zeile und Klicken auf **Animate Selected Mode** wird die Schwingung des Moleküls basierend auf den echten quantenchemischen Verschiebungsvektoren im 3D-Viewer animiert.
* Ein erneuter Klick stoppt die Animation und stellt die Ausgangsgeometrie wieder her.

