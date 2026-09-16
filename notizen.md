
Ich habe die TMS-Referenzwerte für NMR-Berechnungen überprüft und mit einer dedizierten ORCA-Berechnung (B3LYP/def2-TZVP mit vollständiger Geometrieoptimierung und GIAO-NMR-Rechnung) kalibriert. 

### Kalibrierte und aktualisierte Referenzwerte in [orca_manager.py](file:///f:/projekte26/lemovi-for-windows/LeMoVi/orca_manager.py#L9-L16):

1. **Silizium ($^{29}\text{Si}$):** Fehlte bisher komplett. Ich habe die Berechnung durchgeführt und einen Referenzwert von **`314.71 ppm`** ermittelt und in die `DEFAULT_NMR_REFS`-Tabelle eingetragen.
2. **Wasserstoff ($^1\text{H}$):** Auf **`31.92 ppm`** kalibriert (vorher `31.88 ppm`).
3. **Kohlenstoff ($^{13}\text{C}$):** Auf **`183.80 ppm`** kalibriert (vorher `184.80 ppm`).

### Weitere relevante Kerne und deren Referenzen (Liste für zukünftige Rechnungen):
Falls Berechnungen für andere häufige Kerne durchgeführt werden sollen, müssen diese bei demselben Funktional und Basissatz (B3LYP/def2-TZVP) gegen ihre jeweiligen Referenzsubstanzen berechnet werden. Hier ist die Liste der noch ausstehenden Referenzen:

| Kern | Standard-Referenzsubstanz | Status | Benötigte Berechnung |
| :--- | :--- | :--- | :--- |
| **$^{15}\text{N}$** | Flüssiges Ammoniak ($\text{NH}_3$) / Nitromethan ($\text{CH}_3\text{NO}_2$) | Vorläufiger Richtwert (`-244.6`) | GIAO-NMR an optimiertem $\text{NH}_3$ / $\text{CH}_3\text{NO}_2$ |
| **$^{19}\text{F}$** | Trichlorfluoromethan ($\text{CFCl}_3$) | Vorläufiger Richtwert (`162.0`) | GIAO-NMR an optimiertem $\text{CFCl}_3$ |
| **$^{31}\text{P}$** | 85%-ige Phosphorsäure ($\text{H}_3\text{PO}_4$) | Vorläufiger Richtwert (`328.5`) | GIAO-NMR an optimiertem $\text{H}_3\text{PO}_4$ |
| **$^{11}\text{B}$** | Bortrifluorid-Etherat ($\text{BF}_3 \cdot \text{OEt}_2$) | Nicht in Code | GIAO-NMR an $\text{BF}_3 \cdot \text{OEt}_2$ |
| **$^{17}\text{O}$** | Flüssiges Wasser ($\text{H}_2\text{O}$) | Nicht in Code | GIAO-NMR an flüssigkeits-simuliertem (CPCM) $\text{H}_2\text{O}$ |



# Synchronisieren github und git.up



Ja, das ist ab jetzt sehr einfach und problemlos möglich! Da beide Repositories als separate „Remotes“ (Gegenstellen) in deinem lokalen Projekt hinterlegt sind, kannst du neue Änderungen mit jeweils einem Befehl auf beide Plattformen übertragen:

### 1. Änderungen auf GitHub hochladen:
```bash
git push origin main
```
*(Hinweis: Auf GitHub heißt der Hauptzweig aktuell noch `master`. Wenn du ihn dort auch in `main` umbenennen möchtest, kannst du das einfach in den GitHub-Einstellungen der Webseite tun und danach dorthin pushen).*

### 2. Änderungen auf das Universitäts-Git hochladen:
```bash
git push uni main
```

### Tipps für ein einfaches Management:
* **Gemeinsamer Push-Befehl (optional)**: Man kann Git auch so konfigurieren, dass ein einziger Befehl (`git push all`) zu beiden Repositories gleichzeitig pusht. Wenn du das in Zukunft möchtest, sag einfach Bescheid.
* **Tags (Releases)**: Wenn du ein neues Release veröffentlichst, kannst du die Versionsmarkierungen ebenfalls mit `--tags` an beide senden:
  ```bash
  git push origin --tags
  git push uni --tags
  ```




  ## 27.08. 2026


  Ich habe auch Idee 4 (Interaktiver Symmetrie- & Punktgruppen-Trainer) erfolgreich umgesetzt!

Zusammenfassung der Änderungen
Symmetrieberechnung (

symmetry_finder.py
):

Es wurde ein neues Python-Modul zur automatischen Punktgruppenbestimmung implementiert. Es zentriert das Molekül am Massenschwerpunkt, ermittelt Trägheitsachsen und sucht gezielt nach allen Rotationsachsen ($C_n$), Spiegelebenen ($\sigma$) und Inversionszentren ($i$), indem es Koordinatentransformationen prüft.
3D-Darstellung & UI-Kopplung (

app.py
):

3D-Zeichnen: HTML_3DMOL wurde um JS-Methoden erweitert, die Drehachsen als Zylinder ($C_n$), Spiegelebenen als transparente Kreisscheiben ($\sigma$) und das Inversionszentrum ($i$) als Kugel darstellen.
Benutzeroberfläche: In der Menüleiste gibt es nun den neuen Punkt Symmetry $\rightarrow$ Analyze Molecule Symmetry.... Dieser öffnet einen Dialog, der die ermittelte Punktgruppe mit Erklärung anzeigt und es erlaubt, die Symmetrieelemente per Checkbox live ein- und auszublenden.
Alle Details und geänderten Code-Abschnitte findest du im aktualisierten 
walkthrough.md
. LeMoVi ist jetzt bereit für das Testen von Symmetrieelementen!