import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tempfile
import json

from orca_manager import (
    OrcaJobManager,
    format_orca_method,
    normalize_method_alias,
    find_best_tms_match,
    find_best_tantillo_match
)

def test_method_formatting():
    print("=== 1. Testing format_orca_method & normalize_method_alias ===")
    
    # mPW1PW91
    m, b = format_orca_method("mPW1PW91")
    assert m == "mPW1PW", f"Expected mPW1PW, got {m}"
    assert b == "", f"Expected empty block, got {b}"
    assert normalize_method_alias("mPW1PW91") == "MPW1PW91"
    assert normalize_method_alias("mPW1PW") == "MPW1PW91"

    # WC04
    m, b = format_orca_method("WC04")
    assert m is None, f"Expected None, got {m}"
    assert "method dft" in b and "functional hyb_gga_xc_wc04" in b, f"Unexpected block: {b}"

    # WP04
    m, b = format_orca_method("WP04")
    assert m is None, f"Expected None, got {m}"
    assert "method dft" in b and "functional hyb_gga_xc_wp04" in b, f"Unexpected block: {b}"

    # BMK
    m, b = format_orca_method("BMK")
    assert m is None, f"Expected None, got {m}"
    assert "method dft" in b and "exchange hyb_mgga_x_bmk" in b and "correlation gga_c_bmk" in b, f"Unexpected block: {b}"
    
    # Regular method like B3LYP
    m, b = format_orca_method("B3LYP")
    assert m == "B3LYP" and b == "", f"Expected B3LYP, got {m}, {b}"

    print("PASS: format_orca_method tests passed.")

def test_tms_and_tantillo_lookup():
    print("=== 2. Testing TMS and Tantillo lookups ===")
    methods = ["BMK", "mPW1PW91", "WC04", "WP04"]
    for meth in methods:
        tms_entry = find_best_tms_match(method=meth, basis="def2-TZVP")
        print(f"TMS match for {meth}/def2-TZVP: {tms_entry}")
        assert tms_entry is not None, f"Missing TMS for {meth}"
        assert tms_entry.get("h1_shielding") is not None, f"Missing 1H TMS for {meth}"
        assert tms_entry.get("c13_shielding") is not None, f"Missing 13C TMS for {meth}"
        
        tant_entry = find_best_tantillo_match(method=meth, basis="def2-TZVP")
        print(f"Tantillo match for {meth}/def2-TZVP: {tant_entry}")
        assert tant_entry is not None, f"Missing Tantillo scaling for {meth}"
        assert tant_entry.get("c13_slope") is not None, f"Missing c13_slope for {meth}"
        assert tant_entry.get("c13_intercept") is not None, f"Missing c13_intercept for {meth}"
        
    print("PASS: TMS and Tantillo lookups passed.")

def test_job_input_generation():
    print("=== 3. Testing Job Input Generation ===")
    test_dir = tempfile.mkdtemp(prefix="lemovi_test_")
    manager = OrcaJobManager(test_dir)
    
    # Minimal XYZ (raw atom lines as expected by LeMoVi)
    xyz = "C 0 0 0\nH 0 0 1.09\nH 1.02 0 -0.36\nH -0.51 0.89 -0.36\nH -0.51 -0.89 -0.36\n"
    
    for meth in ["BMK", "mPW1PW91", "WC04", "WP04"]:
        # A. Single-step NMR
        job_id = manager.create_job(
            name=f"test_nmr_{meth}",
            xyz_content=xyz,
            task="NMR",
            method=meth,
            basis="def2-SVP",
            nprocs=1
        )
        job_dir = manager.get_job_dir(job_id)
        inp_file = os.path.join(job_dir, "orca_input.inp")
        with open(inp_file, "r") as f:
            content = f.read()
        print(f"--- Single-step input for {meth} ---\n{content.strip()}")
        assert "NMR" in content and "def2-SVP" in content
        assert "D4" not in content, "Dispersion should not be present in NMR single step"
        if meth == "mPW1PW91":
            assert "mPW1PW" in content
        elif meth == "WC04":
            assert "functional hyb_gga_xc_wc04" in content
        elif meth == "WP04":
            assert "functional hyb_gga_xc_wp04" in content
        elif meth == "BMK":
            assert "exchange hyb_mgga_x_bmk" in content

        # B. Two-step %Compound Opt + NMR
        comp_job_id = manager.create_job(
            name=f"test_comp_{meth}",
            xyz_content=xyz,
            task="Opt+NMR",
            method="r2SCAN-3c",
            basis="def2-mSVP",
            use_sep_nmr=True,
            nmr_method=meth,
            nmr_basis="def2-TZVP",
            nprocs=1
        )
        comp_job_dir = manager.get_job_dir(comp_job_id)
        comp_inp_file = os.path.join(comp_job_dir, "orca_input.inp")
        with open(comp_inp_file, "r") as f:
            comp_content = f.read()
        print(f"--- Compound input for {meth} ---\n{comp_content.strip()}")
        assert "%Compound" in comp_content
        assert "New_Step" in comp_content
        assert "NMR" in comp_content and "def2-TZVP" in comp_content
        if meth == "mPW1PW91":
            assert "mPW1PW" in comp_content
        elif meth == "WC04":
            assert "functional hyb_gga_xc_wc04" in comp_content
        elif meth == "WP04":
            assert "functional hyb_gga_xc_wp04" in comp_content
        elif meth == "BMK":
            assert "exchange hyb_mgga_x_bmk" in comp_content

    print("PASS: Job input generation passed.")

def test_live_orca_nmr():
    print("=== 4. Testing Live ORCA Execution with WC04 ===")
    import shutil
    import time
    if not shutil.which("orca"):
        print("SKIP: ORCA executable not found in PATH.")
        return
        
    test_dir = tempfile.mkdtemp(prefix="lemovi_live_test_")
    manager = OrcaJobManager(test_dir)
    xyz = "C 0 0 0\nH 0 0 1.09\nH 1.02 0 -0.36\nH -0.51 0.89 -0.36\nH -0.51 -0.89 -0.36\n"
    
    job_id = manager.create_job(
        name="live_test_wc04",
        xyz_content=xyz,
        task="NMR",
        method="WC04",
        basis="def2-SVP",
        nprocs=2
    )
    job_dir = manager.get_job_dir(job_id)
    print(f"Starting job {job_id}...")
    success = manager.start_job(job_id)
    assert success, f"Failed to start job {job_id}"
    
    # Wait for completion (max 60s)
    final_st = None
    for _ in range(60):
        time.sleep(1)
        jobs = manager.list_jobs()
        match = next((j for j in jobs if j["id"] == job_id), None)
        if match and match["status"] in ("completed", "failed"):
            final_st = match
            break
            
    out_file = os.path.join(job_dir, "orca_output.out")
    if os.path.exists(out_file):
        with open(out_file, "r") as f:
            print(f"--- ORCA Output ---\n{f.read()}")
            
    print(f"Job status: {final_st['status'] if final_st else 'TIMEOUT'}")
    assert final_st is not None and final_st["status"] == "completed", f"Job did not complete: {final_st}"
    
    # Parse results
    res = manager.parse_results(job_id)
    assert res is not None, "parse_results returned None"
    nmr_shieldings = res.get("nmr_shieldings", {})
    print(f"Parsed NMR shieldings count: {len(nmr_shieldings)}")
    assert len(nmr_shieldings) == 5, f"Expected 5 nuclei, got {len(nmr_shieldings)}"
    
    for atom_idx, entry in nmr_shieldings.items():
        print(f"  Atom {atom_idx} {entry['element']}: shielding={entry['shielding']}")
        assert entry.get("shielding") is not None
        
    print("PASS: Live ORCA calculation with WC04 completed and parsed successfully.")

if __name__ == "__main__":
    test_method_formatting()
    test_tms_and_tantillo_lookup()
    test_job_input_generation()
    test_live_orca_nmr()
    print("\nALL UNIT, SYNTAX, AND LIVE EXECUTION TESTS PASSED SUCCESSFULLY!")
