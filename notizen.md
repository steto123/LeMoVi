
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