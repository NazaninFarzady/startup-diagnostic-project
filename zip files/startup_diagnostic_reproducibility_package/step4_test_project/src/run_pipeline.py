"""Run the startup-diagnostic pipeline in order.

Run from any folder with:
    python src/run_pipeline.py

To restart from a later step:
    python src/run_pipeline.py --from-step 6
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK_DIR = PROJECT_ROOT / "notebooks"

NOTEBOOK_STEPS = {
    4: "Step_4_Build_Analysis_Ready_Tables.ipynb",
    5: "Step_5_Engineer_Useful_Features.ipynb",
    6: "04_Exploratory_Analysis_Reviewed.ipynb",
    7: "05_Answer_Three_Diagnostic_Questions.ipynb",
    8: "06_Validate_Findings.ipynb",
    9: "07_Convert_Findings_Into_Diagnostics.ipynb",
    10: "08_Save_And_Reproduce_Pipeline.ipynb",
}


def run_python_script(script_name):
    script_path = PROJECT_ROOT / "src" / script_name
    if not script_path.exists():
        raise FileNotFoundError(f"Missing pipeline script: {script_path}")

    print(f"\nRunning {script_name}")
    subprocess.run([sys.executable, str(script_path)], check=True)


def run_notebook(notebook_name):
    """Execute code cells without requiring the Jupyter command-line package."""
    notebook_path = NOTEBOOK_DIR / notebook_name
    if not notebook_path.exists():
        raise FileNotFoundError(f"Missing notebook: {notebook_path}")

    print(f"\nRunning {notebook_name}")
    notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
    namespace = {"__name__": "__main__"}

    previous_directory = Path.cwd()
    os.chdir(PROJECT_ROOT)

    try:
        for cell_number, cell in enumerate(notebook["cells"], start=1):
            if cell["cell_type"] != "code":
                continue

            source = cell.get("source", "")
            if isinstance(source, list):
                source = "".join(source)

            exec(
                compile(source, f"{notebook_name}:cell_{cell_number}", "exec"),
                namespace,
            )

            # Close displayed figures after each cell. Saved figures remain on disk.
            if "plt" in namespace:
                namespace["plt"].close("all")
    finally:
        os.chdir(previous_directory)


def main():
    parser = argparse.ArgumentParser(
        description="Run the startup diagnostic data pipeline."
    )
    parser.add_argument(
        "--from-step",
        type=int,
        choices=range(2, 11),
        default=2,
        help="First step to run. Default: 2",
    )
    args = parser.parse_args()

    # Use a non-interactive plotting backend during automated runs.
    os.environ.setdefault("MPLBACKEND", "Agg")

    if args.from_step <= 2:
        run_python_script("01_data_quality_audit.py")

    if args.from_step <= 3:
        run_python_script("02_clean_and_standardize.py")

    for step_number, notebook_name in NOTEBOOK_STEPS.items():
        if step_number >= args.from_step:
            run_notebook(notebook_name)

    print("\nPipeline completed successfully.")


if __name__ == "__main__":
    main()
