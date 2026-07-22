import os
import sys
import json
import re
import subprocess
from datetime import datetime

# Standard reference isotropic shieldings (approximate values for TMS at DFT/def2-TZVP level)
DEFAULT_NMR_REFS = {
    "1H": 31.92,      # TMS (B3LYP/def2-TZVP)
    "13C": 183.80,    # TMS (B3LYP/def2-TZVP)
    "15N": -244.6,    # Nitromethane or Ammonia depending on scale
    "19F": 162.0,     # CFCl3
    "29Si": 314.71,   # TMS (B3LYP/def2-TZVP)
    "31P": 328.5      # H3PO4
}

DEFAULT_TMS_REFERENCES = [
  {"geom_method": "-", "geom_basis": "-", "method": "Experiment (Gas)", "basis": "-", "h1_shielding": 30.783, "c13_shielding": 188.0, "source": "[3, 4]"},
  {"geom_method": "-", "geom_basis": "-", "method": "Experiment (Flüssigkeit/rein)", "basis": "-", "h1_shielding": 32.873, "c13_shielding": None, "source": "[3]"},
  {"geom_method": "-", "geom_basis": "-", "method": "Experiment (Flüssigkeit/zylindrisch)", "basis": "-", "h1_shielding": 32.775, "c13_shielding": None, "source": "[3]"},
  {"geom_method": "HF", "geom_basis": "STO-3G", "method": "HF", "basis": "STO-3G", "h1_shielding": 33.7573, "c13_shielding": 249.4485, "source": "[2]"},
  {"geom_method": "HF", "geom_basis": "STO-6G", "method": "HF", "basis": "STO-6G", "h1_shielding": 34.185, "c13_shielding": 251.8526, "source": "[2]"},
  {"geom_method": "HF", "geom_basis": "3-21G", "method": "HF", "basis": "3-21G", "h1_shielding": 33.8334, "c13_shielding": 214.6567, "source": "[2]"},
  {"geom_method": "HF", "geom_basis": "6-31G", "method": "HF", "basis": "6-31G", "h1_shielding": 33.6781, "c13_shielding": 208.236, "source": "[2]"},
  {"geom_method": "HF", "geom_basis": "6-31G*", "method": "HF", "basis": "6-31G*", "h1_shielding": 32.9035, "c13_shielding": 201.7285, "source": "[2]"},
  {"geom_method": "HF", "geom_basis": "6-31+G*", "method": "HF", "basis": "6-31+G*", "h1_shielding": 32.819, "c13_shielding": 201.8459, "source": "[2]"},
  {"geom_method": "HF", "geom_basis": "6-31++G*", "method": "HF", "basis": "6-31++G*", "h1_shielding": 32.8185, "c13_shielding": 202.1032, "source": "[2]"},
  {"geom_method": "HF", "geom_basis": "6-31G**", "method": "HF", "basis": "6-31G**", "h1_shielding": 32.3358, "c13_shielding": 203.1555, "source": "[2]"},
  {"geom_method": "HF", "geom_basis": "6-31+G**", "method": "HF", "basis": "6-31+G**", "h1_shielding": 32.2849, "c13_shielding": 203.1713, "source": "[2]"},
  {"geom_method": "HF", "geom_basis": "6-31++G**", "method": "HF", "basis": "6-31++G**", "h1_shielding": 32.2918, "c13_shielding": 203.5056, "source": "[2]"},
  {"geom_method": "HF", "geom_basis": "6-311G", "method": "HF", "basis": "6-311G", "h1_shielding": 33.6399, "c13_shielding": 203.5439, "source": "[2]"},
  {"geom_method": "HF", "geom_basis": "6-311G*", "method": "HF", "basis": "6-311G*", "h1_shielding": 32.8505, "c13_shielding": 195.989, "source": "[2]"},
  {"geom_method": "HF", "geom_basis": "6-311+G*", "method": "HF", "basis": "6-311+G*", "h1_shielding": 32.7994, "c13_shielding": 195.9349, "source": "[2]"},
  {"geom_method": "HF", "geom_basis": "6-311++G*", "method": "HF", "basis": "6-311++G*", "h1_shielding": 32.7887, "c13_shielding": 196.15, "source": "[2]"},
  {"geom_method": "HF", "geom_basis": "6-311G**", "method": "HF", "basis": "6-311G**", "h1_shielding": 32.4875, "c13_shielding": 196.2165, "source": "[2]"},
  {"geom_method": "HF", "geom_basis": "6-311+G**", "method": "HF", "basis": "6-311+G**", "h1_shielding": 32.4645, "c13_shielding": 195.9187, "source": "[2]"},
  {"geom_method": "HF", "geom_basis": "6-311++G**", "method": "HF", "basis": "6-311++G**", "h1_shielding": 32.4549, "c13_shielding": 196.1819, "source": "[2]"},
  {"geom_method": "k.A.", "geom_basis": "k.A.", "method": "HF", "basis": "def2-TZVPP", "h1_shielding": None, "c13_shielding": 194.1, "source": "[4]"},
  {"geom_method": "B3LYP", "geom_basis": "6-31G*", "method": "B3LYP", "basis": "6-31G*", "h1_shielding": 32.5976, "c13_shielding": 199.9853, "source": "[2]"},
  {"geom_method": "B3LYP", "geom_basis": "6-31G(d)", "method": "B3LYP", "basis": "6-31G(d)", "h1_shielding": 32.3, "c13_shielding": 190.4, "source": "[3, 4]"},
  {"geom_method": "B3LYP-D3BJ (CPCM)", "geom_basis": "def2-TZVP", "method": "B3LYP", "basis": "def2-TZVP", "h1_shielding": 31.93, "c13_shielding": None, "source": "[3]"},
  {"geom_method": "k.A.", "geom_basis": "k.A.", "method": "B3LYP", "basis": "def2-TZVPP", "h1_shielding": None, "c13_shielding": 184.3, "source": "[4]"},
  {"geom_method": "B3LYP-D3BJ (CPCM)", "geom_basis": "def2-TZVP", "method": "MP2", "basis": "def2-TZVP", "h1_shielding": 31.81, "c13_shielding": None, "source": "[3]"},
  {"geom_method": "k.A.", "geom_basis": "k.A.", "method": "BP86", "basis": "def2-TZVPP", "h1_shielding": None, "c13_shielding": 184.8, "source": "[4]"},
  {"geom_method": "B3LYP-D3 (CPCM)", "geom_basis": "def2-TZVP", "method": "B97-2", "basis": "pcS-3", "h1_shielding": None, "c13_shielding": 184.1, "source": "[4]"},
  {"geom_method": "CCSD(T)", "geom_basis": "cc-pVQZ", "method": "DSD-PBEP86", "basis": "pcSseg-3", "h1_shielding": None, "c13_shielding": 185.9, "source": "[4]"},
  {"geom_method": "B3LYP-D3 (PCM)", "geom_basis": "6-311G(d p)", "method": "WP04", "basis": "6-311++G(2d p)", "h1_shielding": 31.6, "c13_shielding": None, "source": "[3]"},
  {"geom_method": "N/A", "geom_basis": "N/A", "method": "ORCA Example Values (Reference)", "basis": "-", "h1_shielding": 31.77, "c13_shielding": 188.1, "source": "[1]"}

]

def load_tms_references(workspace_dir=None):
    """Loads TMS reference dataset from json file or returns default list."""
    paths_to_check = []
    if workspace_dir:
        paths_to_check.append(os.path.join(workspace_dir, "tms_references.json"))
    paths_to_check.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "tms_references.json"))

    for path in paths_to_check:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading TMS references from {path}: {e}")
    return list(DEFAULT_TMS_REFERENCES)

def save_tms_references(tms_list, workspace_dir=None):
    """Saves TMS reference dataset to JSON file in workspace_dir or app dir."""
    target_path = os.path.join(workspace_dir, "tms_references.json") if workspace_dir else os.path.join(os.path.dirname(os.path.abspath(__file__)), "tms_references.json")
    try:
        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(tms_list, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error saving TMS references: {e}")
        return False

def find_best_tms_match(method, basis, tms_list=None):
    """Finds matching TMS reference entry by method and basis set."""
    if tms_list is None:
        tms_list = load_tms_references()
    method_clean = str(method).strip().upper()
    basis_clean = str(basis).strip().upper()

    # Exact match (Method and Basis)
    for entry in tms_list:
        e_method = str(entry.get("method", "")).strip().upper()
        e_basis = str(entry.get("basis", "")).strip().upper()
        if e_method == method_clean and e_basis == basis_clean:
            return entry

    # Fallback: Method match
    for entry in tms_list:
        e_method = str(entry.get("method", "")).strip().upper()
        if e_method == method_clean:
            return entry

DEFAULT_TANTILLO_SCALING = [
  {"geom_method": "B3LYP", "geom_basis": "6-31G(d)", "geom_solvent": "Gas", "method": "B3LYP", "basis": "6-31G(d)", "nmr_solvent": "Gas", "solvent_model": None, "h1_slope": -0.9957, "h1_intercept": 32.2884, "c13_slope": -0.9269, "c13_intercept": 187.4743, "source": "CHESHIRE Table #1a (Gas, G03/G09)"},
  {"geom_method": "B3LYP", "geom_basis": "6-31G(d)", "geom_solvent": "Gas", "method": "B3LYP", "basis": "6-31+G(d,p)", "nmr_solvent": "Gas", "solvent_model": None, "h1_slope": -1.0381, "h1_intercept": 31.7427, "c13_slope": -0.9468, "c13_intercept": 189.4397, "source": "CHESHIRE Table #1a (Gas, G03/G09)"},
  {"geom_method": "B3LYP", "geom_basis": "6-31+G(d,p)", "geom_solvent": "Gas", "method": "B3LYP", "basis": "6-311+G(2d,p)", "nmr_solvent": "Gas", "solvent_model": None, "h1_slope": -1.0592, "h1_intercept": 31.9654, "c13_slope": -1.0311, "c13_intercept": 180.7713, "source": "CHESHIRE Table #1a (Gas, G03/G09)"},
  {"geom_method": "B3LYP", "geom_basis": "6-311+G(2d,p)", "geom_solvent": "Gas", "method": "B3LYP", "basis": "6-311+G(2d,p)", "nmr_solvent": "Gas", "solvent_model": None, "h1_slope": -1.0593, "h1_intercept": 32.0706, "c13_slope": -1.0228, "c13_intercept": 181.3782, "source": "CHESHIRE Table #1a (Gas, G03/G09)"},
  {"geom_method": "B3LYP", "geom_basis": "6-31+G(d,p)", "geom_solvent": "Gas", "method": "B3LYP", "basis": "aug-cc-pVDZ", "nmr_solvent": "Gas", "solvent_model": None, "h1_slope": -1.059, "h1_intercept": 31.7312, "c13_slope": -0.9842, "c13_intercept": 190.0157, "source": "CHESHIRE Table #1a (Gas, G03/G09)"},
  {"geom_method": "MP2", "geom_basis": "6-31+G(d,p)", "geom_solvent": "Gas", "method": "MP2", "basis": "6-31+G(d,p)", "nmr_solvent": "Gas", "solvent_model": None, "h1_slope": -1.0565, "h1_intercept": 32.0189, "c13_slope": -0.9077, "c13_intercept": 202.752, "source": "CHESHIRE Table #1a (Gas, G03/G09)"},
  {"geom_method": "MP2", "geom_basis": "6-31+G(d,p)", "geom_solvent": "Gas", "method": "MP2", "basis": "6-311+G(2d,p)", "nmr_solvent": "Gas", "solvent_model": None, "h1_slope": -1.0735, "h1_intercept": 32.0981, "c13_slope": -0.9889, "c13_intercept": 194.2927, "source": "CHESHIRE Table #1a (Gas, G03/G09)"},
  {"geom_method": "M06-2X", "geom_basis": "6-31G(d)", "geom_solvent": "Gas", "method": "M06-2X", "basis": "6-31G(d)", "nmr_solvent": "Gas", "solvent_model": None, "h1_slope": -1.1082, "h1_intercept": 32.6273, "c13_slope": -1.0591, "c13_intercept": 195.8694, "source": "CHESHIRE Table #1a (Gas, G03/G09)"},
  {"geom_method": "M06-2X", "geom_basis": "6-31G(d)", "geom_solvent": "Gas", "method": "M06-2X", "basis": "6-31+G(d,p)", "nmr_solvent": "Gas", "solvent_model": None, "h1_slope": -1.1398, "h1_intercept": 32.1078, "c13_slope": -1.0741, "c13_intercept": 197.1285, "source": "CHESHIRE Table #1a (Gas, G03/G09)"},
  {"geom_method": "M06-2X", "geom_basis": "6-31+G(d,p)", "geom_solvent": "Gas", "method": "M06-2X", "basis": "6-311+G(2d,p)", "nmr_solvent": "Gas", "solvent_model": None, "h1_slope": -1.1556, "h1_intercept": 32.3008, "c13_slope": -1.1491, "c13_intercept": 188.4206, "source": "CHESHIRE Table #1a (Gas, G03/G09)"},
  {"geom_method": "M06-2X", "geom_basis": "6-311+G(2d,p)", "geom_solvent": "Gas", "method": "M06-2X", "basis": "6-311+G(2d,p)", "nmr_solvent": "Gas", "solvent_model": None, "h1_slope": -1.1562, "h1_intercept": 32.4045, "c13_slope": -1.14, "c13_intercept": 188.8523, "source": "CHESHIRE Table #1a (Gas, G03/G09)"}
]

def load_tantillo_scaling(workspace_dir=None):
    """Loads Tantillo scaling dataset from json file or returns default list."""
    paths_to_check = []
    if workspace_dir:
        paths_to_check.append(os.path.join(workspace_dir, "tantillo_scaling.json"))
    paths_to_check.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "tantillo_scaling.json"))

    for path in paths_to_check:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading Tantillo scaling from {path}: {e}")
    return [dict(e) for e in DEFAULT_TANTILLO_SCALING]

def save_tantillo_scaling(tantillo_list, workspace_dir=None):
    """Saves Tantillo scaling dataset to JSON file in workspace_dir or app dir."""
    target_path = os.path.join(workspace_dir, "tantillo_scaling.json") if workspace_dir else os.path.join(os.path.dirname(os.path.abspath(__file__)), "tantillo_scaling.json")
    try:
        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(tantillo_list, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error saving Tantillo scaling: {e}")
        return False

def find_best_tantillo_match(method, basis, geom_method=None, geom_basis=None, tantillo_list=None,
                             nmr_solvent=None, solvent_model=None):
    """Finds the best matching Tantillo/CHESHIRE scaling entry.

    Matching priority (highest to lowest):
    1. NMR method + basis + nmr_solvent + solvent_model + geom_method + geom_basis (full match)
    2. NMR method + basis + nmr_solvent + solvent_model
    3. NMR method + basis + nmr_solvent (any model)
    4. NMR method + basis + geom_method + geom_basis (Gas only)
    5. NMR method + basis (Gas, any geom)
    6. None
    """
    if tantillo_list is None:
        tantillo_list = load_tantillo_scaling()

    method_clean = str(method).strip().upper()
    basis_clean = str(basis).strip().upper()
    gm_clean = str(geom_method).strip().upper() if geom_method else None
    gb_clean = str(geom_basis).strip().upper() if geom_basis else None
    solv_clean = str(nmr_solvent).strip().upper() if nmr_solvent else "GAS"
    model_clean = str(solvent_model).strip().upper() if solvent_model else None

    def match_nmr(e):
        return (str(e.get("method", "")).strip().upper() == method_clean and
                str(e.get("basis", "")).strip().upper() == basis_clean)

    def match_solvent(e):
        return str(e.get("nmr_solvent", "Gas")).strip().upper() == solv_clean

    def match_model(e):
        em = e.get("solvent_model")
        return (str(em).strip().upper() if em else None) == model_clean

    def match_geom(e):
        return (str(e.get("geom_method", "")).strip().upper() == gm_clean and
                str(e.get("geom_basis", "")).strip().upper() == gb_clean)

    # Priority 1: full exact match
    if gm_clean and gb_clean and model_clean:
        for e in tantillo_list:
            if match_nmr(e) and match_solvent(e) and match_model(e) and match_geom(e):
                return e

    # Priority 2: NMR method/basis + solvent + model
    if model_clean:
        for e in tantillo_list:
            if match_nmr(e) and match_solvent(e) and match_model(e):
                return e

    # Priority 3: NMR method/basis + solvent (any model)
    if solv_clean != "GAS":
        for e in tantillo_list:
            if match_nmr(e) and match_solvent(e):
                return e

    # Priority 4: NMR method/basis + geom (Gas)
    if gm_clean and gb_clean:
        for e in tantillo_list:
            gs = str(e.get("nmr_solvent", "Gas")).strip().upper()
            if match_nmr(e) and match_geom(e) and gs == "GAS":
                return e

    # Priority 5: NMR method/basis, Gas, any geom
    for e in tantillo_list:
        gs = str(e.get("nmr_solvent", "Gas")).strip().upper()
        if match_nmr(e) and gs == "GAS":
            return e

    return None



class OrcaJobManager:

    def __init__(self, workspace_dir):
        self.workspace_dir = workspace_dir
        self.jobs_dir = os.path.join(workspace_dir, "orca_jobs")
        if not os.path.exists(self.jobs_dir):
            os.makedirs(self.jobs_dir)

    def get_job_dir(self, job_id):
        return os.path.join(self.jobs_dir, job_id)

    def list_jobs(self):
        """Lists all jobs in the orca_jobs directory and updates their state."""
        jobs = []
        if not os.path.exists(self.jobs_dir):
            return jobs

        for folder in os.listdir(self.jobs_dir):
            folder_path = os.path.join(self.jobs_dir, folder)
            if os.path.isdir(folder_path):
                meta_file = os.path.join(folder_path, "job_meta.json")
                if os.path.exists(meta_file):
                    try:
                        with open(meta_file, "r") as f:
                            meta = json.load(f)
                        
                        # Dynamically check status of active jobs
                        if meta.get("status") == "running":
                            self._update_job_status(folder, meta)
                            
                        jobs.append(meta)
                    except Exception as e:
                        print(f"Error reading metadata for {folder}: {e}")
        return sorted(jobs, key=lambda x: x.get("created", ""), reverse=True)

    @staticmethod
    def _build_solvent_block(model, solvent, use_draco=False):
        """Generates ORCA %cpcm block for SMD, CPCM, or PCM solvation."""
        if not model or model.lower() in ("none", "keines (gas)", "gas"):
            return ""
        block = "%cpcm\n"
        if model.upper() == "SMD":
            block += "  smd true\n"
            block += f'  SMDsolvent "{solvent}"\n'
        else:  # CPCM or PCM
            block += "  smd false\n"
            block += f'  solvent "{solvent}"\n'
        if use_draco:
            block += "  draco true\n"
        block += "end\n"
        return block

    def create_job(self, name, xyz_content, charge=0, multiplicity=1, task="Opt",
                   method="B3LYP", basis="def2-SVP", dispersion="D4", nprocs=1, maxcore=2000,
                   custom_keywords="", use_sep_nmr=False, nmr_method=None, nmr_basis=None,
                   opt_solvent_model="None", opt_solvent="Chloroform",
                   nmr_solvent_model="None", nmr_solvent="Chloroform",
                   use_draco=False):
        """Creates a new job directory and generates files (supports % Compound multi-step jobs)."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = re.sub(r'[^a-zA-Z0-9_]', '_', name)
        job_id = f"job_{timestamp}_{safe_name}"
        job_dir = self.get_job_dir(job_id)
        os.makedirs(job_dir)

        geom_m = method
        geom_b = basis
        nmr_m = nmr_method if (use_sep_nmr and nmr_method) else method
        nmr_b = nmr_basis if (use_sep_nmr and nmr_basis) else basis

        opt_solv_block = self._build_solvent_block(opt_solvent_model, opt_solvent, use_draco)
        nmr_solv_block = self._build_solvent_block(nmr_solvent_model, nmr_solvent, use_draco)

        if use_sep_nmr and ("NMR" in task) and ("Opt" in task):
            # Generate ORCA % Compound multi-step input
            opt_task = "Opt Freq" if "Freq" in task else "Opt"
            opt_kws = [opt_task, geom_m]
            if geom_b and "None" not in geom_b: opt_kws.append(geom_b)
            if dispersion and dispersion.lower() != "none": opt_kws.append(dispersion)
            if custom_keywords: opt_kws.append(custom_keywords)

            nmr_kws = ["NMR", nmr_m]
            if nmr_b and "None" not in nmr_b: nmr_kws.append(nmr_b)

            inp_content = "% Compound\n"
            inp_content += "  New_Step\n"
            inp_content += f"    ! {' '.join(opt_kws)}\n"
            if opt_solv_block:
                # indent each line of the block by 4 spaces inside New_Step
                for bl in opt_solv_block.splitlines():
                    inp_content += f"    {bl}\n"
            inp_content += "  End_Step\n"
            inp_content += "  New_Step\n"
            inp_content += f"    ! {' '.join(nmr_kws)}\n"
            if nmr_solv_block:
                for bl in nmr_solv_block.splitlines():
                    inp_content += f"    {bl}\n"
            inp_content += "  End_Step\n"
            inp_content += "End\n"
            inp_content += f"%maxcore {maxcore}\n"
            if nprocs > 1:
                inp_content += f"%pal\n  nprocs {nprocs}\nend\n"
            inp_content += f"\n* xyz {charge} {multiplicity}\n"
            inp_content += xyz_content.strip() + "\n"
            inp_content += "*\n"
        else:
            # Build single-step keyword line
            keywords = []
            task_kw = task
            if task == "NMR": task_kw = "NMR"
            elif task == "Opt+Freq": task_kw = "Opt Freq"
            elif task == "Opt+NMR": task_kw = "Opt NMR"
            elif task == "Opt+Freq+NMR": task_kw = "Opt Freq NMR"

            keywords.append(task_kw)
            keywords.append(method)
            if basis and "None" not in basis:
                keywords.append(basis)

            if dispersion and dispersion.lower() != "none":
                keywords.append(dispersion)

            if custom_keywords:
                keywords.append(custom_keywords)

            keyword_line = " ".join(keywords)

            # For single-step jobs, use opt_solvent if it's an NMR-only job,
            # otherwise use the more relevant block
            has_nmr = "NMR" in task_kw
            single_solv_block = nmr_solv_block if has_nmr else opt_solv_block
            if has_nmr and not nmr_solv_block:
                single_solv_block = opt_solv_block  # fallback

            inp_content = f"! {keyword_line}\n"
            inp_content += f"%maxcore {maxcore}\n"
            if nprocs > 1:
                inp_content += f"%pal\n  nprocs {nprocs}\nend\n"
            if single_solv_block:
                inp_content += single_solv_block

            inp_content += f"\n* xyz {charge} {multiplicity}\n"
            inp_content += xyz_content.strip() + "\n"
            inp_content += "*\n"

        # Save files
        with open(os.path.join(job_dir, "orca_input.inp"), "w") as f:
            f.write(inp_content)
        
        # Write initial coordinates also as backup
        with open(os.path.join(job_dir, "input_geom.xyz"), "w") as f:
            num_atoms = len(xyz_content.strip().split("\n"))
            f.write(f"{num_atoms}\nCreated by LeMoVi\n{xyz_content.strip()}\n")

        # Save initial metadata
        meta = {
            "id": job_id,
            "name": name,
            "status": "pending",
            "task": task,
            "method": method,
            "basis": basis,
            "geom_method": geom_m,
            "geom_basis": geom_b,
            "nmr_method": nmr_m,
            "nmr_basis": nmr_b,
            "use_sep_nmr": use_sep_nmr,
            "opt_solvent_model": opt_solvent_model,
            "opt_solvent": opt_solvent,
            "nmr_solvent_model": nmr_solvent_model,
            "nmr_solvent": nmr_solvent,
            "use_draco": use_draco,
            "charge": charge,
            "multiplicity": multiplicity,
            "dispersion": dispersion,
            "nprocs": nprocs,
            "maxcore": maxcore,
            "created": datetime.now().isoformat(),
            "pid": None,
            "runtime": "0s"
        }
        
        self._write_meta(job_dir, meta)
        return job_id

    def start_job(self, job_id, orca_path="orca"):
        """Launches ORCA 6 in the background as a detached process."""
        import shutil
        resolved_path = shutil.which(orca_path) or orca_path
        orca_path = os.path.abspath(resolved_path)

        job_dir = self.get_job_dir(job_id)
        meta_file = os.path.join(job_dir, "job_meta.json")
        
        if not os.path.exists(meta_file):
            return False

        with open(meta_file, "r") as f:
            meta = json.load(f)

        inp_file = os.path.join(job_dir, "orca_input.inp")
        out_file = os.path.join(job_dir, "orca_output.out")

        # Set environment or flags to run detached on Windows without showing a console window
        creationflags = 0
        if sys.platform == "win32":
            creationflags = subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP

        try:
            stdout_handle = open(out_file, "w")
            proc = subprocess.Popen(
                [orca_path, "orca_input.inp"],
                cwd=job_dir,
                stdout=stdout_handle,
                stderr=subprocess.STDOUT,
                creationflags=creationflags
            )
            
            meta["status"] = "running"
            meta["pid"] = proc.pid
            meta["started"] = datetime.now().isoformat()
            self._write_meta(job_dir, meta)
            return True
        except Exception as e:
            print(f"Failed to start ORCA process: {e}")
            meta["status"] = "failed"
            meta["error"] = str(e)
            self._write_meta(job_dir, meta)
            return False

    def kill_job(self, job_id):
        """Kills the background ORCA process."""
        job_dir = self.get_job_dir(job_id)
        meta_file = os.path.join(job_dir, "job_meta.json")
        if not os.path.exists(meta_file):
            return False

        with open(meta_file, "r") as f:
            meta = json.load(f)

        pid = meta.get("pid")
        if pid:
            try:
                if sys.platform == "win32":
                    subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
                else:
                    os.kill(pid, 9)
            except Exception as e:
                print(f"Failed to kill process {pid}: {e}")
        
        meta["status"] = "cancelled"
        meta["ended"] = datetime.now().isoformat()
        self._write_meta(job_dir, meta)
        return True

    def delete_job(self, job_id):
        """Kills the job and deletes its directory."""
        self.kill_job(job_id)
        job_dir = self.get_job_dir(job_id)
        if os.path.exists(job_dir):
            import shutil
            try:
                shutil.rmtree(job_dir)
                return True
            except Exception as e:
                print(f"Failed to delete job directory {job_id}: {e}")
                return False
        return False

    def _update_job_status(self, job_id, meta):
        """Checks if process is still active, updates status based on process status and log content."""
        job_dir = self.get_job_dir(job_id)
        pid = meta.get("pid")
        
        # Check if process is running
        process_alive = False
        if pid:
            if sys.platform == "win32":
                try:
                    out = subprocess.check_output(
                        ["tasklist", "/FI", f"PID eq {pid}"], 
                        text=True, 
                        creationflags=subprocess.CREATE_NO_WINDOW
                    )
                    if str(pid) in out:
                        process_alive = True
                except:
                    pass
            else:
                try:
                    os.kill(pid, 0)
                    process_alive = True
                except OSError:
                    pass

        # Parse log file for completion status
        out_file = os.path.join(job_dir, "orca_output.out")
        status = "running"
        error_msg = ""
        
        if os.path.exists(out_file):
            # Check last few lines of output
            try:
                with open(out_file, "rb") as f:
                    # Read last 4KB
                    f.seek(0, os.SEEK_END)
                    size = f.tell()
                    seek_pos = max(0, size - 4096)
                    f.seek(seek_pos)
                    tail = f.read().decode("utf-8", errors="ignore")
                    
                if "****ORCA TERMINATED NORMALLY****" in tail:
                    status = "completed"
                elif "ORCA TERMINATED ABNORMALLY" in tail or "aborting the run" in tail.lower() or "an error has occurred" in tail.lower() or "[error]" in tail.lower():
                    status = "failed"
                    # Try to extract the error message
                    err_lines = [l for l in tail.split("\n") if "error" in l.lower() or "abort" in l.lower()]
                    if err_lines:
                        error_msg = err_lines[-1]
                elif not process_alive:
                    # Process died without normal termination OR explicit error
                    status = "failed"
                    error_msg = "Process terminated unexpectedly."
            except Exception as e:
                print(f"Error checking log for {job_id}: {e}")

        # Update metadata if changed
        if status != "running" or not process_alive:
            meta["status"] = status
            meta["ended"] = datetime.now().isoformat()
            if error_msg:
                meta["error"] = error_msg
            
            # Calculate final runtime
            if "started" in meta:
                start_dt = datetime.fromisoformat(meta["started"])
                end_dt = datetime.fromisoformat(meta["ended"])
                diff = end_dt - start_dt
                meta["runtime"] = f"{int(diff.total_seconds())}s"
            self._write_meta(job_dir, meta)
        else:
            # Update running time
            if "started" in meta:
                start_dt = datetime.fromisoformat(meta["started"])
                diff = datetime.now() - start_dt
                meta["runtime"] = f"{int(diff.total_seconds())}s"
                self._write_meta(job_dir, meta)

    def _write_meta(self, job_dir, meta):
        with open(os.path.join(job_dir, "job_meta.json"), "w") as f:
            json.dump(meta, f, indent=4)

    def parse_results(self, job_id):
        """Parses job output files and returns coordinates, energy, frequencies, and NMR shieldings."""
        job_dir = self.get_job_dir(job_id)
        out_file = os.path.join(job_dir, "orca_output.out")
        xyz_file = os.path.join(job_dir, "orca_input.xyz")
        
        results = {
            "energies": [],
            "frequencies": [],
            "nmr_shieldings": {},
            "optimized_xyz": None,
            "trajectory": []
        }

        if not os.path.exists(out_file):
            return results

        # 1. Parse energy steps (SCF Energies and Opt steps)
        # Look for "FINAL SINGLE POINT ENERGY" or "SCF ERG"
        try:
            with open(out_file, "r") as f:
                content = f.read()

            # Find all SCF energies
            energy_matches = re.findall(r"FINAL SINGLE POINT ENERGY\s+(-?\d+\.\d+)", content)
            if not energy_matches:
                energy_matches = re.findall(r"SCF ERG\s+=\s+(-?\d+\.\d+)", content)
            
            results["energies"] = [float(e) for e in energy_matches]

            # 2. Parse optimized coordinates (fallback if orca_input.xyz isn't there)
            # Find the last cartesian coordinate block
            coord_blocks = re.findall(
                r"CARTESIAN COORDINATES\s+\((?:ANGSTROMS|ANGSTROEM)\)\n-+\n(.*?)\n\n", 
                content, 
                re.DOTALL | re.IGNORECASE
            )
            if coord_blocks:
                last_block = coord_blocks[-1].strip().split("\n")
                xyz_lines = []
                for line in last_block:
                    parts = line.split()
                    if len(parts) == 4:
                        xyz_lines.append(f"{parts[0]} {parts[1]} {parts[2]} {parts[3]}")
                if xyz_lines:
                    results["optimized_xyz"] = f"{len(xyz_lines)}\nParsed from output\n" + "\n".join(xyz_lines)

            # If the output .xyz file exists, use it as primary
            if os.path.exists(xyz_file):
                with open(xyz_file, "r") as f:
                    results["optimized_xyz"] = f.read()

            # 2.5 Parse optimization trajectory (.trj.xyz or from output coord blocks)
            trj_file = os.path.join(job_dir, "orca_input_trj.xyz")
            if os.path.exists(trj_file):
                try:
                    with open(trj_file, "r") as f:
                        trj_content = f.read()
                    lines = trj_content.strip().splitlines()
                    if lines:
                        try:
                            n_atoms = int(lines[0].strip())
                            block_len = n_atoms + 2
                            for i in range(0, len(lines), block_len):
                                block_lines = lines[i:i+block_len]
                                if len(block_lines) >= 2:
                                    results["trajectory"].append("\n".join(block_lines))
                        except ValueError:
                            pass
                except Exception as e:
                    print("Error parsing trajectory file:", e)

            if not results["trajectory"] and coord_blocks:
                for block in coord_blocks:
                    block_lines = block.strip().splitlines()
                    xyz_lines = []
                    for line in block_lines:
                        parts = line.split()
                        if len(parts) == 4:
                            xyz_lines.append(f"{parts[0]} {parts[1]} {parts[2]} {parts[3]}")
                    if xyz_lines:
                        results["trajectory"].append(f"{len(xyz_lines)}\nParsed from output\n" + "\n".join(xyz_lines))

            # 3. Parse Vibrational Frequencies & IR Intensities
            ir_intensities = {}

            # A) Try parsing IR SPECTRUM table from main output
            ir_match = re.search(r"IR SPECTRUM\r?\n-+(.*?)(?=THERMOCHEMISTRY|NORMAL MODES|---|$\n)", content, re.DOTALL | re.IGNORECASE)
            if ir_match:
                ir_lines = ir_match.group(1).strip().splitlines()
                for line in ir_lines:
                    m = re.match(r"\s*(\d+):\s*(-?\d+\.\d+)\s+(?:[\d\.\-]+)\s+([\d\.\-]+)", line)
                    if m:
                        idx = int(m.group(1))
                        freq = float(m.group(2))
                        inten = float(m.group(3))
                        ir_intensities[idx] = (freq, inten)

            # B) Try parsing VIBRATIONAL FREQUENCIES section
            freq_section = re.search(r"VIBRATIONAL FREQUENCIES\r?\n-+(.*?)(?=NORMAL MODES|IR SPECTRUM|THERMOCHEMISTRY|---|$\n)", content, re.DOTALL | re.IGNORECASE)
            if freq_section:
                freq_lines = freq_section.group(1).strip().splitlines()
                for line in freq_lines:
                    m = re.match(r"\s*(\d+):\s*(-?\d+\.\d+)", line)
                    if m:
                        idx = int(m.group(1))
                        val = float(m.group(2))
                        if idx not in ir_intensities:
                            ir_intensities[idx] = (val, 1.0)

            # C) Fallback: Check for orca_input.hess file if present in job_dir
            hess_file = os.path.join(job_dir, "orca_input.hess")
            if not ir_intensities and os.path.exists(hess_file):
                try:
                    with open(hess_file, "r") as f:
                        h_content = f.read()
                    vib_match = re.search(r"\$vibrational_frequencies\n\s*(\d+)\n(.*?)(?=\n\$|\Z)", h_content, re.DOTALL)
                    if vib_match:
                        for line in vib_match.group(2).strip().splitlines():
                            parts = line.split()
                            if len(parts) >= 2:
                                try:
                                    idx = int(parts[0])
                                    val = float(parts[1])
                                    ir_intensities[idx] = (val, 1.0)
                                except ValueError:
                                    pass
                except Exception as ex_h:
                    print("Hessian parse fallback notice:", ex_h)

            # Populate results["frequencies"]
            for idx in sorted(ir_intensities.keys()):
                freq_val, int_val = ir_intensities[idx]
                results["frequencies"].append({
                    "index": idx,
                    "frequency": freq_val,
                    "intensity": max(0.0, int_val)
                })

            results["vibrational_frequencies"] = results["frequencies"]

            # 4. Parse NMR Shielding constants
            summary_match = re.search(
                r"CHEMICAL SHIELDING SUMMARY \(ppm\).*?----\s*----\s*------------\s+------------\n(.*?)(?:\n\n|\n\s*\n|---|$)",
                content,
                re.DOTALL
            )
            if summary_match:
                table_lines = summary_match.group(1).strip().splitlines()
                for line in table_lines:
                    parts = line.split()
                    if len(parts) >= 3:
                        try:
                            atom_idx = int(parts[0])
                            element = parts[1]
                            shielding = float(parts[2])
                            results["nmr_shieldings"][atom_idx] = {
                                "element": element,
                                "shielding": shielding
                            }
                        except ValueError:
                            continue

            # Fallback for NMR: Look for individual nucleus blocks:
            if not results["nmr_shieldings"]:
                nucleus_matches = re.finditer(
                    r"Nucleus\s+(\d+)([A-Za-z]+)\s*:\s*\n.*?Total\s+(?:-?\d+\.\d+\s+){3}iso=\s+(-?\d+\.\d+)",
                    content,
                    re.DOTALL
                )
                for m in nucleus_matches:
                    atom_idx = int(m.group(1))
                    element = m.group(2)
                    shielding = float(m.group(3))
                    results["nmr_shieldings"][atom_idx] = {
                        "element": element,
                        "shielding": shielding
                    }

            # 5. Parse Thermodynamics
            enthalpy_match = re.search(r"(?:Enthalpy \(H\)|Total Enthalpy)\s*\.+\s*(-?\d+\.\d+)\s+Eh", content)
            results["enthalpy"] = float(enthalpy_match.group(1)) if enthalpy_match else None

            gibbs_match = re.search(r"(?:Gibbs free enthalpy \(G\)|Final Gibbs Free Enthalpy|Gibbs free energy)\s*\.+\s*(-?\d+\.\d+)\s+Eh", content)
            results["gibbs_energy"] = float(gibbs_match.group(1)) if gibbs_match else None

            entropy_match = re.search(r"(?:Total Entropy Correction|Entropy correction)\s*\.+\s*(-?\d+\.\d+)\s+Eh", content)
            if entropy_match:
                results["entropy_correction"] = float(entropy_match.group(1))
            else:
                entropy_match_cal = re.search(r"Total Entropy\s*\.+\s*(-?\d+\.\d+)\s+cal/mol", content)
                results["entropy_correction"] = float(entropy_match_cal.group(1)) * 298.15 * 1.5936e-6 if entropy_match_cal else None

            dipole_match = re.search(r"Magnitude \(Debye\)\s*:\s*(\d+\.\d+)", content)
            results["dipole_magnitude"] = float(dipole_match.group(1)) if dipole_match else None

            # 6. Parse Normal Modes displacements
            normal_modes_match = re.search(r"NORMAL MODES\r?\n-+(.*?)(?=IR SPECTRUM|THERMOCHEMISTRY|---|$\n)", content, re.DOTALL | re.IGNORECASE)
            results["normal_modes"] = {}
            if normal_modes_match:
                nm_block = normal_modes_match.group(1)
                displacements = {}
                active_modes = []
                for line in nm_block.strip().splitlines():
                    parts = line.split()
                    if not parts:
                        continue
                    if all(p.isdigit() for p in parts) and len(parts) <= 6:
                        active_modes = [int(p) for p in parts]
                        for m_idx in active_modes:
                            if m_idx not in displacements:
                                displacements[m_idx] = []
                        continue
                    if active_modes and len(parts) >= len(active_modes) + 1:
                        try:
                            int(parts[0])
                            vals = [float(x) for x in parts[1:len(active_modes)+1]]
                            for col_i, m_idx in enumerate(active_modes):
                                displacements[m_idx].append(vals[col_i])
                        except ValueError:
                            continue
                
                for m_idx, disp_list in displacements.items():
                    coords = []
                    for i in range(0, len(disp_list), 3):
                        if i + 2 < len(disp_list):
                            coords.append([disp_list[i], disp_list[i+1], disp_list[i+2]])
                    results["normal_modes"][m_idx] = coords

        except Exception as e:
            print(f"Error parsing ORCA results: {e}")

        return results


    def count_electrons(self, xyz_content, charge=0):
        try:
            from rdkit import Chem
            pt = Chem.GetPeriodicTable()
        except ImportError:
            pt = None
        common_z = {
            "H": 1, "He": 2, "Li": 3, "Be": 4, "B": 5, "C": 6, "N": 7, "O": 8, "F": 9, "Ne": 10,
            "Na": 11, "Mg": 12, "Al": 13, "Si": 14, "P": 15, "S": 16, "Cl": 17, "Ar": 18,
            "K": 19, "Ca": 20, "Sc": 21, "Ti": 22, "V": 23, "Cr": 24, "Mn": 25, "Fe": 26,
            "Co": 27, "Ni": 28, "Cu": 29, "Zn": 30, "Br": 35, "I": 53
        }

        total_protons = 0
        for line in xyz_content.strip().split("\n"):
            parts = line.split()
            if not parts:
                continue
            sym = parts[0]
            if re.match(r"^[A-Za-z]{1,2}$", sym):
                sym = sym.capitalize()
                z = 0
                if pt:
                    try:
                        z = pt.GetAtomicNumber(sym)
                    except Exception:
                        pass
                if z == 0:
                    z = common_z.get(sym, 0)
                total_protons += z
                
        return total_protons - charge

    def validate_spin_multiplicity(self, xyz_content, charge, multiplicity):
        """
        Validates spin multiplicity against total electron count.
        Returns (is_valid, expected_multiplicity_desc, correct_multiplicity)
        """
        n_electrons = self.count_electrons(xyz_content, charge)
        if n_electrons <= 0:
            return True, "", multiplicity
            
        even = (n_electrons % 2 == 0)
        is_valid = True
        correct_mult = multiplicity
        
        if even:
            if multiplicity % 2 == 0:
                is_valid = False
                correct_mult = 1 if multiplicity < 2 else multiplicity - 1
            expected = "odd"
        else:
            if multiplicity % 2 != 0:
                is_valid = False
                correct_mult = 2 if multiplicity < 2 else multiplicity - 1
            expected = "even"
            
        if multiplicity - 1 > n_electrons:
            is_valid = False
            max_possible = n_electrons + 1
            if even and max_possible % 2 == 0:
                max_possible -= 1
            elif not even and max_possible % 2 != 0:
                max_possible -= 1
            correct_mult = max_possible
            expected = f"{expected} and <= {n_electrons + 1}"
            
        return is_valid, expected, correct_mult

