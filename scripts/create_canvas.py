"""Generate a scratch canvas; normal users should use run_workflow.py."""
import argparse
from pathlib import Path
from workflow import create_canvas, safe_name, read_json
if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--work-dir', type=Path, required=True)
    p.add_argument('--run', required=True)
    p.add_argument('--seed', type=int, default=42)
    a = p.parse_args()
    if (a.work_dir/'generated.canvas').exists():
        p.error('Canvas already exists; use a fresh scratch directory')
    create_canvas(a.work_dir, safe_name(a.run), a.seed)
