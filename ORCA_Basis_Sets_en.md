# ORCA Basis Sets: Recommended Applications and Limitations

This document describes the basis sets integrated in **LeMoVi** for **ORCA 6**, their optimal application areas, and their limitations.

---

## 1. Overview of Basis Set Families

### A. Karlsruhe / Ahlrichs Basis Sets (`def2-` Family)
The `def2` sets (developed by the Ahlrichs group) are the **de facto standard** in ORCA. They are defined consistently across the periodic table and are highly optimized for ORCA calculation accelerations (such as RI-J and RI-JK).

* **`def2-SVP`** (Split-Valence Polarization, Double-Zeta)
  * **Application:** Fast geometry optimizations, frequency calculations of very large molecules, pre-checks.
  * **Limitation:** Too inaccurate for reliable thermochemical energies (reaction barriers, binding energies).
* **`def2-TZVP`** (Triple-Zeta Valence Polarization)
  * **Application:** The "workhorse" basis set for Density Functional Theory (DFT). Excellent for reliable geometries, frequencies, and thermodynamic data.
  * **Limitation:** For high-accuracy quantum chemical post-HF methods (such as DLPNO-CCSD(T)), the polarization is sometimes insufficient.
* **`def2-TZVPP`** (Triple-Zeta Valence Double-Polarization)
  * **Application:** Standard recommendation for wavefunction methods (MP2, DLPNO-CCSD(T)). Has additional polarization functions.
* **`def2-QZVP`** (Quadruple-Zeta)
  * **Application:** Benchmarks, very high accuracy, estimating the complete basis set limit.
  * **Limitation:** Extremely computationally expensive; the gain in accuracy is often not worth the cost for standard DFT calculations.
* **`def2-mSVP`** (Modified SVP)
  * **Application:** Modified SVP basis set, optimized for semi-numerical DFT methods.

---

### B. Minimally Augmented def2 Basis Sets (`ma-def2-` Family)
To use diffuse functions (important for lone pairs, anions, and excited states), classical augmented basis sets are often extremely computationally expensive and prone to linear dependency. ORCA bypasses this with the `ma-def2` family.

* **`ma-def2-SVP` / `ma-def2-TZVP` / `ma-def2-TZVPP`**
  * **Application:** **Anions, excited states (TD-DFT), NMR shieldings, optical rotations, weak interactions (e.g., hydrogen bonds).** Diffuse functions are only appended to the most electronegative atoms.
  * **Limitation:** Slightly less accurate than fully augmented sets for extremely small systems, but this is more than offset by the drastic computational savings for medium to large systems.

---

### C. Jensen's Polarization Consistent Basis Sets (`pcseg-n` Family)
The `pcseg` family was designed by Frank Jensen specifically for **DFT calculations**.

* **`pcseg-1`** (Double-Zeta) / **`pcseg-2`** (Triple-Zeta) / **`pcseg-3`** (Quadruple-Zeta)
  * **Application:** DFT calculations of molecular properties (e.g., NMR chemical shifts, hyperfine coupling constants). They converge more systematically and faster toward the basis set limit for DFT functionals than the `def2` family.
* **`aug-pcseg-1` / `aug-pcseg-2`**
  * **Application:** As above, but for systems requiring diffuse functions (e.g., excited state molecules or anions).
  * **Limitation:** Less widely used than the `def2` family, which can make comparisons with literature values more difficult. Auxiliary basis sets for RI approximations may need to be assigned manually in some cases (though ORCA 6 solves much of this automatically).

---

## 2. Dunning's Correlation Consistent Basis Sets (`cc-pV*Z` Family)
The classical basis sets for post-Hartree-Fock methods.

* **`cc-pVDZ` / `cc-pVTZ` / `cc-pVQZ`**
  * **Application:** Systematic Complete Basis Set (CBS) limit extrapolation calculations for high-accuracy ab initio methods like CCSD(T) or MP2.
* **`aug-cc-pVDZ` / `aug-cc-pVTZ` / `aug-cc-pVQZ`**
  * **Application:** As above, but with diffuse functions for excited states (CASSCF/NEVPT2/TD-DFT) and dispersion interactions.
  * **Limitation:** **Very high computational cost.** On large molecules, diffuse functions on hydrogens (`aug-`) tend to cause numerical instabilities (linear dependencies in the basis set). For DFT calculations, these sets are usually inefficient; use `def2-TZVP` or `pcseg-2` instead.

---

## 3. Pople Basis Sets (The Classics)
* **`6-31G` / `6-31G*` / `6-31G**` / `6-31+G*` / `6-31++G**`
  * **Application:** Comparison with older literature data or legacy projects.
  * **Limitation:** **Obsolete.** For modern calculations, Pople basis sets should be avoided. They exhibit systematic errors (especially for transition metals, where they are often not well-defined) and offer a worse ratio of calculation time to accuracy compared to the modern `def2` family (e.g., `def2-SVP` is almost always better and faster than `6-31G*`).

---

## 4. Practical Recommendations for Typical Tasks in ORCA 6

| Task | Recommended Basis Set | Additional Tip |
| :--- | :--- | :--- |
| **DFT Geometry Optimization / Freq** | `def2-TZVP` | Standard for reliable structures and thermochemistry. |
| **Fast Screening / Huge Systems** | `def2-SVP` | For structure pre-selections. |
| **Post-HF / Wavefunction (DLPNO-CCSD(T))**| `def2-TZVPP` or `cc-pVTZ` | Important for accurate correlation energies. |
| **NMR Chemical Shifts** | `pcseg-2` or `ma-def2-TZVP` | Diffuse/polarized functions are critical here. |
| **Anions / Rydberg States** | `ma-def2-TZVP` | Minimizes calculation time while maintaining high quality for diffuse charges. |
| **Crystal Packings / Weak Interactions** | `def2-TZVP` + Dispersion (`D4`) | Dispersion corrections correct for basis set superposition error (BSSE). |

---

## 5. Important Rules & Limitations in ORCA

1. **No Mixed Basis Sets within a Molecule:**
   Avoid mixing different basis set families (e.g., `6-31G*` for carbon and `def2-SVP` for hydrogen) unless you are explicitly doing so in a QM/MM or ONIOM calculation. This leads to unphysical charge distributions and errors.
2. **Utilize the RI Approximation (Resolution of Identity):**
   ORCA defaults to RI for DFT and MP2. ORCA automatically selects the appropriate auxiliary basis set (e.g., `def2/J` or `def2-TZVP/C`). When using Dunning sets or highly exotic basis sets, ORCA might not find a matching auxiliary basis set in its internal library.
3. **Heavy Elements (Transition Metals from Period 4 onwards, Lanthanides):**
   Effective Core Potentials (ECPs) must be used for elements heavier than Krypton. The `def2` basis sets have built-in ECPs for these elements, making them extremely user-friendly. Pople sets (`6-31G*`) often do not support these elements at all or do so inadequately.

---

## 6. Advanced ORCA Features in the LeMoVi Interface

### A. Pre-Flight Assistant (Input Validation)
Before sending a job, LeMoVi performs automatic sanity checks:
* **Spin Multiplicity:** Checks if the specified multiplicity matches the electron count (even electron count $\rightarrow$ odd multiplicity; odd electron count $\rightarrow$ even multiplicity). If there is an error, a suggestion for automatic correction is shown.
* **Heavy Element Warning:** If the molecule contains elements with an atomic number $Z > 20$ (e.g., transition metals) and a Pople basis set (`6-31G`) is selected, the system warns the user of inaccurate results and recommends using `def2` basis sets.
* **Accessibility Check:** The system verifies if the `orca` executable is available in the PATH and warns if the calculation cannot be started.

### B. Thermodynamics Summary Card
After running frequency calculations (`Freq`), the results dialog displays the following values under **Thermodynamics**:
* **Enthalpy ($H$)** and **Gibbs Free Energy ($G$)** in Hartree ($E_h$).
* **Entropy Correction ($T \cdot S$)** at $298.15\text{ K}$.
* **Dipole Moment** in Debye (including directional components).

### C. NMR Chemical Shifts & TMS Reference Database
Calculated isotropic shieldings ($\sigma$) are converted to chemical shifts ($\delta$, ppm) using standard or customized TMS reference shielding values:
$$\delta = \sigma_{\text{ref}} - \sigma_{\text{calculated}}$$

LeMoVi includes an integrated, fully extensible **TMS Reference Database** (`tms_references.json`) containing over 30 quantum-chemical and experimental reference values for $^1\text{H}$ and $^{13}\text{C}$ (e.g. HF, B3LYP, MP2, BP86, WP04, as well as experimental gas and liquid values).
* **Automatic Recommendation:** After completing an NMR job, the system automatically suggests the best-matching TMS reference value for the chosen functional, basis set, solvents, and solvation models (analogous to Tantillo shift scaling).
* **User Customization:** Via the **TMS-Referenzen...** button, users can view, filter, edit, add, or delete any reference values. The database supports mapping geometry and NMR solvents as well as solvation models.
* **Tantillo Shift Scaling (`tantillo_scaling.json`):** In addition to standard TMS subtraction, LeMoVi supports linear scaling per Tantillo et al. ($\delta = (\sigma_{\text{calc}} - \text{Intercept}) / \text{Slope}$). Via the **Tantillo-Skalierungen...** button, users can manage, edit, add, or reset all slope and intercept parameters.
* **Symmetry Averaging:** The system automatically calculates symmetry ranks for all atoms using RDKit topological and fragment geometry analysis. An additional column for symmetry-averaged chemical shifts is displayed in the NMR tables.
* **3D Viewer & Spectrum Integration:** Calculated chemical shifts (either standard or symmetry-averaged) can be overlaid on the 3D molecule viewer as interactive labels or plotted in the NMR Spectrum tab.

### D. Specialized NMR Density Functionals (WC04, WP04, BMK, mPW1PW91)
For high-accuracy NMR predictions, LeMoVi supports established specialized functionals from the literature:
* **`WC04` (Wiitala-Cramer 2004):** Hybrid GGA functional parameterized specifically to minimize mean errors in $^{13}\text{C}$ chemical shifts. Combines modified Becke exchange with modified correlation. Seamlessly integrated via LibXC (`functional hyb_gga_xc_wc04`) in ORCA 6.
* **`WP04` (Wiitala-Peverati 2004/2007):** Companion functional to WC04, specifically optimized for $^1\text{H}$ chemical shifts. Seamlessly integrated via LibXC (`functional hyb_gga_xc_wp04`).
* **`BMK` (Boese-Martin for Kinetics):** Meta-GGA hybrid functional with 42% HF exchange. In addition to reaction barriers and kinetics, it is widely utilized in CHESHIRE and Tantillo linear scaling NMR protocols. Integrated via LibXC (`exchange hyb_mgga_x_bmk`, `correlation gga_c_bmk`).
* **`mPW1PW91` (modified PW91):** One of the most popular benchmarking standards for DFT NMR calculations (including Tantillo and Sarotti linear scaling). Handled natively in ORCA via the `mPW1PW` keyword.
* **Automated ORCA 6 Syntax Handling:** LeMoVi automatically determines whether a functional requires simple keyword specification or a `%method ... end` LibXC block, formatting both single-step and two-step (`%Compound` Opt + NMR) inputs error-free. Calibrated TMS reference shieldings and linear scaling factors are preloaded.

### E. IR Spectra & Vibration Animations
Under **Vibrational Frequencies**, all calculated normal modes are listed with frequencies and IR intensities:
* Selecting a row and clicking **Animate Selected Mode** will animate the molecule's vibration in the 3D viewer based on the actual quantum-chemical displacement vectors.
* Clicking it again stops the animation and restores the static structure.

