"""Resize selected images in an unpublished scratch directory."""
import argparse
from pathlib import Path
from workflow import resize_images, read_json
if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--work-dir', type=Path, required=True)
    p.add_argument('--max-edge', type=int, default=600)
    a = p.parse_args()
    if (a.work_dir/'run.json').exists() and read_json(a.work_dir/'run.json').get('status') == 'complete':
        p.error('Published runs are immutable; use run_workflow.py --mode new')
    resize_images(a.work_dir, a.max_edge)
