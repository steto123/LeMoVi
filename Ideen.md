# LeMoVi - Ideen zur Weiterentwicklung

1. **Drag & Drop-Unterstützung**: Ermögliche es, eine Moleküldatei (z. B. `.sdf` oder `.mol`) einfach von einem Ordner direkt in das Fenster der Anwendung zu ziehen, woraufhin es sofort in 3D gerendert wird.
2. **"Zuletzt geöffnet"-Historie**: Füge dem Dateimenü einen Unterpunkt "Zuletzt verwendet" hinzu, der die letzten 5 bis 10 geöffneten oder gespeicherten Moleküle auflistet, um schnellen Zugriff zu ermöglichen.
3. **Bild- und Video-Export**: Neben den reinen Strukturdaten könnte man eine Funktion "Als Bild speichern..." (z.B. PNG/JPEG mit transparentem Hintergrund) oder sogar einen "Spinning-Export" (kurzes GIF oder MP4 des rotierenden Moleküls) für Präsentationen anbieten.
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
