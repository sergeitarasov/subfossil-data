"""Baserow -> VGG16 -> t-SNE/RasterFairy -> Obsidian, adapted from pyImaging.

No database writes. All source images remain unchanged.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone

DEFAULT_URL = 'https://fip-86-50-23-51.kaj.poutavm.fi'
ROOT = Path(__file__).resolve().parents[1]


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')
    tmp.replace(path)


def read_json(path):
    return json.loads(Path(path).read_text())


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def safe_name(value):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', value) or '..' in value:
        raise ValueError(f'Unsafe file identifier: {value!r}')
    return value


def value(x):
    return x.get('value', '') if isinstance(x, dict) else (x or '')


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ValueError('API redirect refused; check BASEROW_URL')


def api_json(url, token):
    # Tokens are used only for the configured API, never for attachment requests.
    request = urllib.request.Request(url, headers={'Authorization': 'Token ' + token})
    with urllib.request.build_opener(NoRedirect).open(request, timeout=60) as r:
        return json.load(r)


def fetch_rows(args):
    if args.snapshot:
        rows = read_json(args.snapshot)
        if not isinstance(rows, list):
            raise ValueError('Snapshot must be a complete JSON array, not one API page.')
    else:
        token = os.environ.get('BASEROW_TOKEN')
        if not token:
            raise ValueError('Set BASEROW_TOKEN to a read-only database token; see scripts/README.md.')
        base = args.baserow_url.rstrip('/')
        if urllib.parse.urlsplit(base).scheme != 'https':
            raise ValueError('BASEROW_URL must use HTTPS.')
        fields = api_json(f'{base}/api/database/fields/table/{args.table_id}/', token)
        names = {f['name'] for f in fields}
        required = {'catalogNumber', 'bodyPart', 'images', 'imageToUse'}
        if not required <= names:
            raise ValueError('Missing Baserow fields: ' + ', '.join(sorted(required - names)))
        rows, page = [], 1
        # Read all pages and filter locally: works with text and select bodyPart fields.
        while True:
            response = api_json(f'{base}/api/database/rows/table/{args.table_id}/?user_field_names=true&size=200&page={page}', token)
            rows.extend(response['results'])
            if not response.get('next'):
                break
            page += 1
    matching = [r for r in rows if str(value(r.get('bodyPart'))).strip().casefold() == args.body_part.casefold()]
    matching.sort(key=lambda r: r['catalogNumber'])
    ids = [r['catalogNumber'] for r in matching]
    if len(set(ids)) != len(ids):
        raise ValueError('Duplicate catalogNumber values in selected body part; resolve before running.')
    if not matching:
        raise ValueError(f'No rows for bodyPart={args.body_part!r}')
    return matching


def select_view(row):
    images = row.get('images') or []
    choice = str(value(row.get('imageToUse'))).strip()
    if choice == 'Neither':
        return None, 'excluded_neither', None
    if not images:
        return None, 'missing_images', None
    if choice not in ('', 'Not decided', 'View 1', 'View 2', 'Both'):
        return None, 'invalid_selection', None
    if len(images) > 2:
        return None, 'ambiguous_views', None
    views = {}
    for im in images:
        visible = im.get('visible_name', '')
        m = re.match(r'^View\s+([12])\s*-', visible, re.I)
        if m:
            view = int(m[1])
        elif '__view-02' in visible:
            view = 2
        elif Path(visible).stem == row['catalogNumber']:
            view = 1
        elif len(images) == 1 and choice != 'View 2':
            view = 1
        else:
            return None, 'ambiguous_views', None
        if view in views:
            return None, 'ambiguous_views', None
        views[view] = im
    if choice == 'View 2':
        selected, reason = 2, 'explicit_view_2'
    elif choice == 'View 1':
        selected, reason = 1, 'explicit_view_1'
    elif choice == 'Both':
        selected, reason = 1, 'both_use_view_1'
    elif len(images) == 2:
        selected, reason = 1, 'undecided_two_images_use_view_1'
    else:
        selected, reason = next(iter(views)), 'single_image'
    if selected not in views:
        return None, 'selected_view_missing', selected
    return views[selected], reason, selected


def download_image(image, target, image_root=None):
    if image_root:
        # Offline fixture/snapshot replay. Original visible basename must be present.
        filename = re.sub(r'^View\s+[12]\s*-\s*', '', image.get('visible_name', ''), flags=re.I)
        if not filename or Path(filename).name != filename or '\\' in filename or filename in ('.', '..'):
            raise ValueError('Unsafe attachment filename')
        stored = image.get('name', '')
        if stored and (Path(stored).name != stored or '\\' in stored or stored in ('.', '..')):
            raise ValueError('Unsafe stored attachment name')
        source = Path(image_root) / stored if stored else Path(image_root) / filename
        if not source.is_file():
            source = Path(image_root) / filename
        shutil.copyfile(source, target)
        return
    url = image.get('url', '')
    if urllib.parse.urlsplit(url).scheme != 'https':
        raise ValueError('Attachment URL must be HTTPS.')
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=90) as response, target.open('wb') as f:
                shutil.copyfileobj(response, f)
            return
        except Exception:
            target.unlink(missing_ok=True)
            if attempt == 2:
                raise
            time.sleep(attempt + 1)


def select_images(args, run_dir):
    from PIL import Image
    rows = fetch_rows(args)
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / 'selected').mkdir(exist_ok=True)
    report = {'bodyPart': args.body_part, 'matchedRecords': len(rows), 'selectedIds': [],
              'missingImageIds': [r['catalogNumber'] for r in rows if not r.get('images')],
              'undecidedTwoImageIds': [r['catalogNumber'] for r in rows if len(r.get('images') or []) == 2 and value(r.get('imageToUse')) in ('', 'Not decided')],
              'outcomes': {}, 'downloadFailures': []}
    selected = []
    for index, row in enumerate(rows):
        if index % 25 == 0:
            print(f'Selecting/downloading {index + 1}/{len(rows)}', flush=True)
        identifier = safe_name(row['catalogNumber'])
        im, reason, view = select_view(row)
        report['outcomes'].setdefault(reason, []).append(identifier)
        if im is None:
            continue
        filename = f'{identifier}.jpg'
        target = run_dir / 'selected' / filename
        try:
            download_image(im, target, args.image_root)
            with Image.open(target) as image:
                image.load()
                if image.format != 'JPEG':
                    raise ValueError('Expected JPEG attachment')
                width, height = image.size
        except Exception as exc:
            target.unlink(missing_ok=True)
            report['downloadFailures'].append({'catalogNumber': identifier, 'errorType': type(exc).__name__})
            continue
        selected.append({'rowId': row.get('id'), 'catalogNumber': identifier,
                         'bodyPart': value(row['bodyPart']), 'view': view,
                         'imageToUse': value(row.get('imageToUse')), 'selectionReason': reason,
                         'attachmentName': im.get('name'), 'visibleName': im.get('visible_name'),
                         'file': filename, 'sha256': digest(target), 'width': width, 'height': height})
        report['selectedIds'].append(identifier)
    report['selectedCount'] = len(selected)
    report['missingImageCount'] = len(report['missingImageIds'])
    report['undecidedTwoImageCount'] = len(report['undecidedTwoImageIds'])
    write_json(run_dir / 'selection.json', selected)
    write_json(run_dir / 'selection-report.json', report)
    with (run_dir / 'selection.csv').open('w', newline='') as f:
        columns = list(selected[0]) if selected else ['catalogNumber']
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(selected)
    lines = [f'# Selection report: {args.body_part}', '', f'Matched records: {len(rows)}',
             f'Successfully selected: {len(selected)}', f'Without images: {report["missingImageCount"]}',
             f'Two images, no preference: {report["undecidedTwoImageCount"]}',
             f'Download failures: {len(report["downloadFailures"])}', '']
    for title, ids in [('Without images', report['missingImageIds']), ('Two images, no preference', report['undecidedTwoImageIds']), *report['outcomes'].items()]:
        lines.extend([f'## {title} ({len(ids)})', '', ', '.join(ids) or 'None', ''])
    if report['downloadFailures']:
        lines.extend(['## Download failures', '', *[f'- {x["catalogNumber"]}: {x["errorType"]}' for x in report['downloadFailures']]])
    (run_dir / 'selection-report.md').write_text('\n'.join(lines) + '\n')
    print(f'Selected {len(selected)}/{len(rows)}; missing {report["missingImageCount"]}; undecided pairs {report["undecidedTwoImageCount"]}', flush=True)
    if report['downloadFailures']:
        raise ValueError('Downloads failed. Report saved; run will not be published. Retry after checking access.')
    if not selected:
        raise ValueError('No usable selected images. Report saved; no canvas generated.')
    return selected


def resize_images(run_dir, max_edge=600):
    from PIL import Image, ImageOps
    if max_edge < 32:
        raise ValueError('max-edge must be at least 32')
    (run_dir / 'resized').mkdir(exist_ok=True)
    for record in read_json(run_dir / 'selection.json'):
        with Image.open(run_dir / 'selected' / record['file']) as source:
            image = ImageOps.exif_transpose(source).convert('RGB')
            image.thumbnail((max_edge, max_edge), Image.Resampling.LANCZOS)
            image.save(run_dir / 'resized' / record['file'], quality=90)


def embed_images(run_dir, cache_dir, recompute=False):
    import numpy as np
    import tensorflow as tf
    from PIL import Image, ImageOps
    from tensorflow.keras.applications.vgg16 import VGG16, preprocess_input
    records = read_json(run_dir / 'selection.json')
    config = {'model': 'VGG16', 'weights': 'imagenet', 'include_top': False,
              'features': 'flatten-7x7x512', 'input': '224x224-RGB-white-letterbox-LANCZOS',
              'preprocessing': 'keras-vgg16', 'tensorflow': tf.__version__,
              'keras': getattr(tf.keras, '__version__', 'unknown')}
    cache_dir.mkdir(parents=True, exist_ok=True)
    model, features = None, []
    for i, record in enumerate(records):
        key = hashlib.sha256((record['sha256'] + json.dumps(config, sort_keys=True)).encode()).hexdigest()
        cached = cache_dir / f'{key}.npy'
        if cached.exists() and not recompute:
            vector = np.load(cached, allow_pickle=False)
        else:
            if model is None:
                model = VGG16(weights='imagenet', include_top=False)
            with Image.open(run_dir / 'selected' / record['file']) as image:
                rgb = ImageOps.exif_transpose(image).convert('RGB')
                rgb = ImageOps.pad(rgb, (224, 224), method=Image.Resampling.LANCZOS, color='white')
                batch = np.asarray(rgb, dtype=np.float32)[None, ...]
            vector = np.asarray(model(preprocess_input(batch), training=False)).reshape(-1)
            tmp = cached.with_suffix('.tmp')
            with tmp.open('wb') as f:
                np.save(f, vector, allow_pickle=False)
            tmp.replace(cached)
        if vector.shape != (25088,) or not np.isfinite(vector).all():
            raise ValueError('Invalid embedding cache; rerun with --recompute')
        features.append(vector)
        if i % 25 == 0 or i == len(records) - 1:
            print(f'Embedded {i + 1}/{len(records)}', flush=True)
    np.savez_compressed(run_dir / 'embeddings.npz', features=np.stack(features),
                        files=np.array([r['file'] for r in records]))
    write_json(run_dir / 'embedding-settings.json', config)


def grid_layout(run_dir, seed):
    import numpy as np
    records = read_json(run_dir / 'selection.json')
    n = len(records)
    with np.load(run_dir / 'embeddings.npz', allow_pickle=False) as data:
        if list(data['files']) != [r['file'] for r in records]:
            raise ValueError('Embedding filenames do not match selection')
        features = data['features']
    perplexity = None
    if n < 4 or np.allclose(features, features[0]):
        # t-SNE/RasterFairy are undefined or uninformative for these cases.
        width = math.ceil(math.sqrt(n))
        grid = np.array([(i % width, i // width) for i in range(n)])
        xy = grid.astype(float)
        algorithm = 'small-or-identical-sample-grid'
    else:
        from sklearn.decomposition import PCA
        from sklearn.manifold import TSNE
        import rasterfairy
        import importlib
        # RasterFairy 1.0.6 still uses np.float. Scope compatibility to that
        # module rather than altering NumPy globally.
        class RasterNumpy:
            float = float
            def __getattr__(self, name):
                return getattr(np, name)
        importlib.import_module('rasterfairy.rasterfairy').np = RasterNumpy()
        reduced = PCA(n_components=min(50, n - 1, features.shape[1]), random_state=seed).fit_transform(features)
        perplexity = min(30, max(1, (n - 1) / 3))
        xy = TSNE(n_components=2, perplexity=perplexity, init='random',
                  learning_rate='auto', random_state=seed).fit_transform(reduced)
        # A masked near-square grid avoids a long single row for prime counts.
        width = math.ceil(math.sqrt(n))
        height = math.ceil(n / width)
        mask = np.ones((height, width), dtype=int)
        mask.flat[:n] = 0
        target = {'width': width, 'height': height, 'mask': mask, 'count': n, 'hex': False}
        np.random.seed(seed)
        grid, _ = rasterfairy.transformPointCloud2D(xy, target=target)
        grid = np.rint(grid).astype(int)
        algorithm = 'PCA-tSNE-RasterFairy'
    if len(set(map(tuple, grid))) != n or not np.isfinite(xy).all():
        raise ValueError('Grid contains collisions or non-finite coordinates')
    layout = [dict(file=r['file'], x=int(g[0]), y=int(g[1]), tsneX=float(p[0]), tsneY=float(p[1])) for r,g,p in zip(records, grid, xy)]
    write_json(run_dir / 'layout.json', layout)
    write_json(run_dir / 'layout-settings.json', {'algorithm': algorithm, 'seed': seed, 'perplexity': perplexity})
    return layout


def create_canvas(run_dir, run_id, seed=42):
    from PIL import Image
    records = read_json(run_dir / 'selection.json')
    layout = grid_layout(run_dir, seed)
    cards = []
    for record, cell in zip(records, layout):
        identifier = record['catalogNumber']
        uid = hashlib.sha256(f'{run_id}:{identifier}'.encode()).hexdigest()[:16]
        x, y = cell['x'] * 470, cell['y'] * 530
        # Obsidian displays the catalogue filename on each standalone image card.
        with Image.open(run_dir / 'resized' / record['file']) as im:
            w, h = im.size
        scale = min(400 / w, 420 / h)
        w, h = round(w * scale), round(h * scale)
        cards.append({'id': 'i'+uid, 'type': 'file', 'x': x + (430-w)//2,
                      'y': y + 20, 'width': w, 'height': h,
                      'file': f'runs/{run_id}/resized/{record["file"]}'})
    canvas = {'nodes': cards, 'edges': []}
    write_json(run_dir / 'generated.canvas', canvas)
    return canvas


def referencing_canvases(vault, run_id):
    refs = []
    target = f'runs/{run_id}/'
    for path in (vault / 'canvas').rglob('*.canvas'):
        if path.parent == vault / 'canvas' / 'baserow' and path.name in (f'{run_id}.canvas', f'{run_id}_original.canvas'):
            continue
        # A malformed manual canvas blocks replacement rather than being ignored.
        for node in read_json(path).get('nodes', []):
            for key in ('file', 'background'):
                raw = str(node.get(key, '')).replace('\\', '/')
                normalized = os.path.normpath(raw).replace('\\', '/')
                if normalized.startswith(target):
                    refs.append(str(path.relative_to(vault)))
    return sorted(set(refs))


def publish_run(stage, vault, run_id, mode):
    target = vault / 'runs' / run_id
    canvas_dir = vault / 'canvas' / 'baserow'
    canvas_dir.mkdir(parents=True, exist_ok=True)
    paths = [canvas_dir / f'{run_id}.canvas', canvas_dir / f'{run_id}_original.canvas']
    if mode == 'new' and (target.exists() or any(p.exists() for p in paths)):
        raise ValueError('Run already exists; choose a new name')
    archive = None
    if mode == 'overwrite':
        refs = referencing_canvases(vault, run_id)
        if refs:
            raise ValueError('Run is referenced by other canvases; use --mode new: ' + ', '.join(refs))
        if not target.exists():
            raise ValueError('Overwrite target does not exist')
        archive = vault / 'archives' / (run_id + '_' + datetime.now().strftime('%Y%m%dT%H%M%S%f'))
        archive.mkdir(parents=True)
        shutil.copytree(target, archive / 'run')
        for p in paths:
            if p.exists():
                shutil.copy2(p, archive / p.name)
        # Archive canvas links must point at archived images, not replacement ones.
        for p in archive.rglob('*.canvas'):
            data = read_json(p)
            for node in data.get('nodes', []):
                for key in ('file', 'background'):
                    prefix = f'runs/{run_id}/'
                    if str(node.get(key, '')).startswith(prefix):
                        node[key] = str((archive / 'run').relative_to(vault)) + '/' + node[key][len(prefix):]
            write_json(p, data)
    rollback = stage.parent / (stage.name + '-old')
    try:
        if target.exists():
            target.rename(rollback)
        stage.rename(target)
        canvas = read_json(target / 'generated.canvas')
        for p in paths:
            write_json(p, canvas)
    except Exception:
        if not rollback.exists() and target.exists():
            target.rename(stage)
            for p in paths:
                p.unlink(missing_ok=True)
        if rollback.exists():
            if target.exists():
                shutil.rmtree(target)
            rollback.rename(target)
            for p in paths:
                old = archive / p.name
                if old.exists():
                    data = read_json(old)
                    prefix = str((archive / 'run').relative_to(vault)) + '/'
                    for node in data.get('nodes', []):
                        for key in ('file', 'background'):
                            if str(node.get(key, '')).startswith(prefix):
                                node[key] = f'runs/{run_id}/' + node[key][len(prefix):]
                    write_json(p, data)
        raise
    if rollback.exists():
        shutil.rmtree(rollback)
    return paths[0]


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--body-part', required=True)
    p.add_argument('--vault', type=Path, default=ROOT / 'data' / 'classification')
    p.add_argument('--mode', choices=['new', 'overwrite'], default='new')
    p.add_argument('--run', help='Run name; required for overwrite')
    p.add_argument('--baserow-url', default=os.environ.get('BASEROW_URL', DEFAULT_URL))
    p.add_argument('--table-id', type=int, default=int(os.environ.get('BASEROW_TABLE_ID', '672')))
    p.add_argument('--snapshot', type=Path, help='Offline complete API-row array')
    p.add_argument('--image-root', type=Path, help='Offline attachments named as visible filenames')
    p.add_argument('--max-edge', type=int, default=600)
    p.add_argument('--seed', type=int, default=42)
    p.add_argument('--recompute', action='store_true')
    return p


def main():
    args = parser().parse_args()
    safe_name(args.body_part)
    import platform
    import subprocess
    if sys.platform == 'darwin' and platform.machine() == 'x86_64':
        arm = subprocess.run(['sysctl', '-n', 'hw.optional.arm64'], capture_output=True, text=True)
        if arm.stdout.strip() == '1':
            raise ValueError('Intel Python under Rosetta cannot run these TensorFlow wheels. Use native ARM Python 3.10-3.12; see README.')
    if args.mode == 'overwrite' and not args.run:
        raise ValueError('--mode overwrite requires --run')
    vault = args.vault.resolve()
    vault.mkdir(parents=True, exist_ok=True)
    lock = vault / '.workflow.lock'
    try:
        lock.mkdir()
    except FileExistsError:
        raise ValueError('Workflow lock exists. Check for another process; see README before removing a stale lock.')
    stage = None
    try:
        run_id = safe_name(args.run) if args.run else f'{args.body_part}_{datetime.now():%Y-%m-%d_%H%M%S}_{time.time_ns()%1000000:06d}'
        target = vault / 'runs' / run_id
        if args.mode == 'new' and target.exists():
            raise ValueError('Run exists; choose a new --run')
        if args.mode == 'overwrite':
            if not target.exists():
                raise ValueError('Overwrite target does not exist')
            if read_json(target / 'run.json')['bodyPart'] != args.body_part:
                raise ValueError('Body part differs from existing run')
            refs = referencing_canvases(vault, run_id)
            if refs:
                raise ValueError('Run referenced by classification canvases; use new: ' + ', '.join(refs))
        stage = vault / 'runs' / ('.staging-' + run_id)
        if stage.exists():
            raise ValueError('Staging folder exists; inspect it before retrying with another run name')
        stage.mkdir(parents=True)
        write_json(stage / 'run.json', {'run': run_id, 'bodyPart': args.body_part,
                   'createdUTC': datetime.now(timezone.utc).isoformat(), 'seed': args.seed,
                   'maxEdge': args.max_edge, 'source': 'snapshot' if args.snapshot else 'baserow',
                   'tableId': args.table_id, 'status': 'building'})
        select_images(args, stage)
        resize_images(stage, args.max_edge)
        embed_images(stage, vault / '.cache' / 'vgg16', args.recompute)
        create_canvas(stage, run_id, args.seed)
        import importlib.metadata
        metadata = read_json(stage / 'run.json')
        metadata['status'] = 'complete'
        metadata['packages'] = {n: importlib.metadata.version(n) for n in ['numpy','Pillow','tensorflow','scikit-learn','rasterfairy']}
        write_json(stage / 'run.json', metadata)
        (vault / 'canvas' / 'species').mkdir(parents=True, exist_ok=True)
        canvas = publish_run(stage, vault, run_id, args.mode)
        print(f'Open vault: {vault}\nCanvas: {canvas}\nReport: {target / "selection-report.md"}')
    except Exception:
        if stage and stage.exists():
            print(f'Incomplete staging output retained for diagnosis: {stage}', file=sys.stderr)
        raise
    finally:
        lock.rmdir()


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(f'Workflow stopped ({type(exc).__name__}): {exc}', file=sys.stderr)
        sys.exit(1)
