"""Regression check: report-writing scripts must create their output
directories even when they are absent (the qc/ FileNotFoundError bug).

Runs 18_extraction_bias.py with qc/ temporarily removed and asserts the
report file is (re)created. Run from the project root:
    python scripts/34_regression_output_dirs.py
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QC = os.path.join(ROOT, "qc")
TARGET = os.path.join(QC, "extraction_selection_bias.md")


def main():
    assert not os.path.exists(QC) or os.path.isdir(QC)
    if os.path.exists(TARGET):
        os.remove(TARGET)
    # simulate the failure condition: qc/ absent at script start
    moved = QC + ".regression_bak"
    had_qc = os.path.exists(QC)
    if had_qc:
        os.rename(QC, moved)
    try:
        r = subprocess.run(
            [sys.executable,
             os.path.join(ROOT, "scripts", "18_extraction_bias.py")],
            cwd=ROOT, capture_output=True, text=True)
        assert r.returncode == 0, r.stderr[-2000:]
        assert os.path.exists(TARGET), "report not recreated"
        print("PASS: qc/ absent -> 18_extraction_bias recreated "
              "qc/extraction_selection_bias.md")
    finally:
        # merge the recreated qc back and restore
        if os.path.exists(TARGET) and had_qc:
            import shutil
            os.makedirs(moved, exist_ok=True)
            shutil.copy2(TARGET, os.path.join(
                moved, "extraction_selection_bias.md"))
            os.remove(TARGET)
            try:
                os.rmdir(QC)
            except OSError:
                pass
        if had_qc:
            os.rename(moved, QC)


if __name__ == "__main__":
    main()
