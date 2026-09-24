# LeMoVi - Ideen zur Weiterentwicklung

1. ~~**Drag & Drop-Unterstützung**: Ermögliche es, eine Moleküldatei (z. B. `.sdf` oder `.mol`) einfach von einem Ordner direkt in das Fenster der Anwendung zu ziehen, woraufhin es sofort in 3D gerendert wird.~~
2. ~~**"Zuletzt geöffnet"-Historie**: Füge dem Dateimenü einen Unterpunkt "Zuletzt verwendet" hinzu, der die letzten 5 bis 10 geöffneten oder gespeicherten Moleküle auflistet, um schnellen Zugriff zu ermöglichen.~~
3. ~~**Bild- und Video-Export**: Neben den reinen Strukturdaten könnte man eine Funktion "Als Bild speichern..." (z.B. PNG/JPEG mit transparentem Hintergrund) oder sogar einen "Spinning-Export" (kurzes GIF oder MP4 des rotierenden Moleküls) für Präsentationen anbieten.~~
4. ~~**Integration einer Datenbank-Suche (z.B. PubChem)**~~ *(Erledigt)*: Anstatt nur lokale Dateien zu importieren, könnte es eine Option "Aus Datenbank importieren..." geben. Man tippt einfach den Namen (z.B. "Aspirin") ein, und die App lädt die Struktur automatisch aus dem Internet herunter. (Integrierbar über die PubChem PUG REST API).
5. **Kopieren & Einfügen (Clipboard-Support)**: Erlaube es dem Nutzer, einen SMILES-String oder einen ganzen MOL-Block aus einer anderen Anwendung zu kopieren und einfach per `Strg+V` in LeMoVi einzufügen (und umgekehrt per `Strg+C` zu exportieren).
6. **Export für den 3D-Druck**: Eine Option, die Moleküloberfläche oder die Kugel-Stab-Modelle im `.stl`- oder `.obj`-Format zu exportieren, sodass Nutzer ihre Moleküle direkt auf einem 3D-Drucker ausdrucken können.
7. **Sitzungen speichern (Projekt-Dateien)**: Anstatt nur das nackte Molekül zu exportieren, könnte man ein eigenes Dateiformat (z. B. `.lemovi`) schaffen, das *alles* speichert: das Molekül, den aktuellen Kamerawinkel, eingeblendete Oberflächen und gemessene Abstände.
8. ~~**Galerie-/Batch-Modus für SDF-Dateien**~~ *(Erledigt)*: SDF-Dateien enthalten oft hunderte Moleküle. Anstatt nur das erste zu laden, könnte man Pfeiltasten ("Nächstes/Vorheriges") einblenden, um durch eine ganze Bibliothek von Molekülen zu blättern.
9. ~~**Molekül-Overlay (Vergleichs-Import)**~~ *(Erledigt)*: Eine Funktion "Molekül hinzufügen...", die das aktuelle Molekül nicht ersetzt, sondern das neue Molekül *zusätzlich* in den Viewer lädt. So könnte man zwei Strukturen übereinanderlegen und visuell vergleichen.
10. **Metadaten- und Eigenschaften-Export**: Beim Exportieren als CSV oder erweiterte SDF-Datei könnten nicht nur die Koordinaten, sondern auch die in LeMoVi berechneten Eigenschaften (Gasteiger-Ladungen, LogP-Werte oder berechnete Abstände) als Metadaten mit in die Datei geschrieben werden.

# Orca- Interface

1.  ~~Im Reiter Thermodynamics die Informationen über verwendete Basissätze und Methode mit aufnehmen~~ 
2.  ~~Bei Geometrieoptimierungen den verwendeten Basissätze und Methode oben rechts einblenden~~
3. ~~Bei Kombinationsrechnungen ( beispielsweise opt + NMR) unterschiedliche Methoden für die einzelnen Schritte anbieten. Eventuell per Radiobutton oder wie bisher als Liste die Art der Rechnung und dann die Eingabemaske dynamisch anpassen. Als Voreinstellung dann überall die gleich Methode verwenden. Nutzer ändert bei Bedarf~~
4. ~~Darstellung eventuell berechneter Spektren dynamisch als extra Reiter im Ergebnisfenster anbieten~~
5. ~~Lösungsmittelmodell explizit mit aufnehmen (auch für NMR Berechnungen)~~



# Generell

1.  Alles in englisch übersetzen und Versionsnummern einfügen
2.  spalsh screen (Nild überprüfen)


27.08. 2026
Listed directory LeMoVi
Viewed README_de.md:1-60
Viewed Ideen.md:1-28
Viewed notizen.md:1-46

Hier sind **5 kreative und innovative Ideen**, um LeMoVi noch leistungsfähiger, benutzerfreundlicher und einzigartiger für Lehre und Forschung zu machen:

---

### ~~1. Interaktive Spektren-Struktur-Kopplung (Spectra-to-Structure Mapping)~~
* ~~**Die Idee:** Wenn Benutzer ORCA-NMR- oder IR-Berechnungen durchführen, wird das Spektrum meist als Diagramm angezeigt. Diese Idee verbindet das Spektrum direkt mit der 3D-Ansicht:~~
  * ~~**Peak $\rightarrow$ Atom:** Ein Klick auf ein Signal (Peak) im NMR-Spektrum hebt das/die zugehörige(n) Atom(e) in der 3D-Struktur farblich hervor.~~
  * ~~**Atom $\rightarrow$ Peak:** Ein Klick auf ein Atom im 3D-Modell markiert die chemische Verschiebung (den Peak) im Spektrum.~~
* ~~**Mehrwert:** Dies macht die Interpretation von Spektren extrem intuitiv und eignet sich hervorragend für Studierende, um NMR-Kopplungen und chemische Umgebungen zu verstehen.~~

---

### 2. Visueller Reaktionspfad- & Übergangszustands-Planer (NEB / TS Visualizer)
* **Die Idee:** Erweitere die App von statischen Molekülen hin zu chemischen Reaktionen. Der Nutzer zeichnet im 2D-Editor das Edukt und das Produkt. LeMoVi generiert automatisch die Zwischenschritte (z. B. über xTB- oder ORCA-Methoden wie *Nudged Elastic Band* / NEB).
  * **Interaktiver Graph:** Ein Diagramm zeigt die Energiebarriere der Reaktion.
  * **Animation:** Der Nutzer kann per Slider oder Play-Button die chemische Reaktion als flüssige 3D-Animation ablaufen lassen, um die Bewegung der Atome beim Bindungsbruch und der Bindungsbildung zu beobachten.
* **Mehrwert:** Übergangszustände (Transition States) sind oft schwer zu visualisieren. Ein intuitiver Pfad-Viewer macht Reaktionsbarrieren direkt begreifbar.

---

### ~~3. Direkte Molekülorbital-Visualisierung (HOMO/LUMO & Elektronendichte)~~
* ~~**Die Idee:** Integration einer Visualisierung für Molekülorbitale (insbesondere HOMO und LUMO) sowie elektrostatische Potentialflächen als 3D-Volumendaten (Isosurfaces).~~
  * ~~Da ORCA oder xTB bei Berechnungen Wellenfunktionsdateien erzeugen, könnten die Orbitale über einen automatischen Hintergrundschritt (z. B. mit `orca_plot` oder `xtb --molden`) als 3D-Gitter berechnet und in `3Dmol.js` als rote/blaue oder grüne/orange transparente Wolken über das Molekül gelegt werden.~~
* ~~**Mehrwert:** Orbitalwechselwirkungen (wie bei Diels-Alder-Reaktionen oder nucleophilen Angriffen) können so direkt in der App ohne Drittsoftware (wie Avogadro oder VMD) analysiert werden.~~

---

### 4. Multikonformer-Vergleichsansicht (Conformer Ensemble Analysis)
* **Die Idee:** Bei energiearmen Molekülen oder bei Simulationen entstehen oft mehrere leicht unterschiedliche 3D-Strukturen (Konformere). Statt nur ein einziges Bild anzuzeigen, könnte die App alle berechneten Konformere nebeneinander in einer Kachelansicht darstellen.
  * **Side-by-Side-Vergleich:** Die Ansicht zeigt alle Konformere nebeneinander, farblich markiert nach Energie (z. B. mit einer Farbverlaufslegende von Rot für "hoch" zu Grün für "niedrig").
  * **Dynamische Animation:** Ein "Animation Play"-Button könnte sanft zwischen den Strukturen hin- und herblenden, um die flexiblen Bereiche des Moleküls hervorzuheben.
* **Mehrwert:** Essentiell für das Verständnis von Molekülflexibilität, z. B. bei Medikamenten-Wirkstoff-Bindungen oder bei sterisch anspruchsvollen organischen Verbindungen.

---

### 5. Smart AI Chemistry Assistant (Natürlich-sprachliche Steuerung)
* **Die Idee:** Ein kleines Textfeld an der Seite, in das der Nutzer Befehle in natürlicher Sprache eingeben kann (lokal oder per API angebunden).
  * **Beispiele:** 
    * *„Ersetze die Methylgruppe an Kohlenstoff 3 durch ein Chloratom und optimiere mit xTB.“*
    * *„Zeige mir alle Wasserstoffbrückenbindungen im aktuellen Molekül.“*
    * *„Erstelle ein Konformeren-Ensemble für dieses Molekül und zeige das stabilste Konformer.“*
  * Das System übersetzt den Befehl im Hintergrund in entsprechende RDKit-Operationen oder GUI-Aktionen.
* **Mehrwert:** Eine barrierefreie Schnittstelle, die komplexe Modifikationen und Berechnungen auch für Nutzer ohne Programmier- oder tiefe Chemieinformatik-Kenntnisse sofort zugänglich macht.





# ToDo



- [x] Spiegelebene in einem helleren Blau / Grün verbessert (konfigurierbar: Hellblau/Cyan, Hellgrün/Mint, Mehrfarbig, Transparenz & Rand)

IR Spektren Berechnungen (Implementierung eines Assistenten der durch die Rechnungen führt)

NMR Zuordnungen mit Auswahl der Kalibriermethode und pyDP4 sowie DP4-AI Integration  (diese auch in der NMR APP einführen, Apps getrennt lassen weil ich LeMoVi als Visualisierung für kleine Moleküle und Orca Interface separat lassen möchte)

SLURM Job Manager als separate App  und späterer Integration in den Orca Job Manager

