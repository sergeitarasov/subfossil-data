"""Select Baserow attachments into a NEW scratch directory (no canvas yet)."""
from pathlib import Path
from workflow import parser, select_images
if __name__ == '__main__':
    p = parser()
    p.add_argument('--work-dir', type=Path, required=True)
    a = p.parse_args()
    if a.work_dir.exists():
        p.error('--work-dir must not already exist; use a new scratch folder')
    select_images(a, a.work_dir)
