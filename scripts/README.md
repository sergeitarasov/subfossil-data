# Baserow images → similarity grid → Obsidian

This workflow selects **one image per catalogue record** for a requested body part, resizes copies, extracts VGG16 features, and places the images on an editable Obsidian canvas using t-SNE and RasterFairy. Each image is named `<catalogNumber>.jpg`. Obsidian displays this filename on its standalone image card; there is no separate label or wrapper group. The selected view remains recorded in the manifest.

Adapted from the project's `pyImaging/copyImages.py`, `keras_extract.py`, and `tsne2Grid.py`. Absolute personal paths, manual CSV transfer, saliency experiments and automatic K-means assignments have been removed. VGG16 flattened convolutional features and the t-SNE → RasterFairy sequence are retained. PCA before t-SNE, explicit seeds, letterboxing, manifests and rerun protections are additions.

## Install

From the **subfossil-data repository root**, use Python **3.10–3.12**:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r scripts/requirements.txt
```

Use `python3.10` or `python3.11` if that is your installed version. On Apple Silicon, use native ARM Python, for example `/opt/homebrew/bin/python3.12`, rather than an Intel Conda environment running through Rosetta. Check first:

```bash
python3.12 -c 'import platform; print(platform.machine())'
```

Apple Silicon should report `arm64`. The pinned TensorFlow 2.16 series supports Intel macOS; newer TensorFlow releases do not all provide Intel Mac wheels. No GPU is required. The first embedding run downloads the public ImageNet VGG16 weights (about 59 MB); subsequent runs use Keras's local model cache. Installing TensorFlow also requires a larger initial package download.

## Configure Baserow

In Baserow, create a **database token with Read permission only** for the Subfossils / Specimens table. This is a database token, not your account password. The default URL and table ID are already configured for the lab's instance and table 672.

Enter the token without displaying it or placing its value in shell history:

```bash
read -s BASEROW_TOKEN
# Paste the token, then press Enter.
export BASEROW_TOKEN
```

Optional overrides:

```bash
export BASEROW_URL='https://fip-86-50-23-51.kaj.poutavm.fi'
export BASEROW_TABLE_ID=672
```

Do not put tokens in scripts, Markdown, a canvas, or Git. The workflow only reads Baserow; it does not change records or upload classifications. It requests all pages and matches the current `bodyPart` field, rather than inferring anatomy from historical catalogue names. No `completed`, island or taxonomy filter is applied.

## Run a body part

```bash
python scripts/run_workflow.py --body-part head
python scripts/run_workflow.py --body-part elytra
python scripts/run_workflow.py --body-part pronotum
```

The default `--mode new` chooses a unique timestamped run name. For a memorable name:

```bash
python scripts/run_workflow.py --body-part head --mode new --run head_review_01
```

A run name must be unique across the vault. The script locates the repository relative to its own file, so paths are not tied to one user's home directory. You can change the vault location with `--vault /absolute/path/to/vault`.

## Image selection rules

| Baserow state | Result |
|---|---|
| No image attachments | Skip and report the ID. |
| One image, blank / Not decided | Use the available image. |
| View 1 or View 2 | Use that exact view. |
| Both | Use View 1. |
| Neither | Skip and report. |
| Two images, blank / Not decided | Use View 1 and report the missing preference. |
| Selected view missing, unclear view names, more than two attachments or invalid choice | Skip and report the inconsistency; do not silently substitute another image. |

Views are identified from attachment display names such as `View 1 - ROD-SF-head-1.jpg`, or recognized catalogue filenames. Reordering attachments does not change the selected view. Unknown names in a two-image record require review.

`selection-report.md` and `.json` give counts and ID lists for missing images, undecided pairs, exclusions, selection inconsistencies and download failures. Missing-image counts include records marked Neither if they also have no images. The manifest records row IDs, selected views, selection reasons, attachment names, dimensions and SHA-256 checksums. Attachment URLs and credentials are not saved into the public manifest.

Downloads are **Baserow review attachments**, not the full-resolution originals linked from GitHub. Source attachment bytes are saved under `selected/`; originals in `data/original/` remain untouched. This workflow is for visual classification, not calibrated length measurement.

## Open the canvas

In Obsidian, choose **Open folder as vault** and select:

```text
data/classification/
```

The structure is:

```text
data/classification/                    # vault root
  README.md
  runs/
    head_review_01/
      selected/                         # downloaded JPEG attachments
      resized/                          # 600 px maximum edge, no upscaling
      selection.csv
      selection.json
      selection-report.md
      selection-report.json
      embeddings.npz
      embedding-settings.json
      layout.json
      layout-settings.json
      generated.canvas                  # machine-generated reference
      run.json                          # settings, versions, completion state
  canvas/
    baserow/
      head_review_01.canvas              # editable body-part canvas
      head_review_01_original.canvas     # reference initial layout
    species/                            # your classification canvases
  archives/                             # previous overwritten runs
  .cache/vgg16/                         # reusable feature vectors
```

Open `canvas/baserow/head_review_01.canvas`. **Catalogue numbers appear as the image filenames.** Move or copy the image card itself; its catalogue identity remains visible in any canvas without copying a separate label. The layout uses a 400 px-wide display area, with image aspect ratio preserved.

You can sort within the body-part canvas, or create your own canvases in `canvas/species/` and copy image cards there. Canvas cards reference the existing image files, so do not move the JPEGs manually or rename the `runs/` folders. You can add named species or morphotype groups. Only manually created species/morphotype groups are needed.

Species-assignment export and Baserow write-back are **not implemented in this first version**. The stable manifest and ordinary image file references preserve the information needed for that next step. A future exporter must check duplicate assignments and ambiguous overlapping species groups.

## Rerunning: new versus overwrite

**New is the recommended default.** It retrieves the current Baserow choices and generates a separate run and canvas. Your earlier work stays intact.

```bash
python scripts/run_workflow.py --body-part head --mode new --run head_review_02
```

To replace a specific existing run deliberately:

```bash
python scripts/run_workflow.py --body-part head --mode overwrite --run head_review_01
```

Before replacement, the workflow:

1. Refuses if another canvas under `canvas/` references the run's images, including species canvases. Use a new run instead.
2. Builds the replacement in a staging directory. Failed downloads or embedding/layout errors do not replace the old run.
3. Archives the old run and both body-part canvases. Archived image paths are rewritten to the archived image copies, preserving the old canvas layout and manual changes.
4. Replaces the run and its two body-part canvases, restoring the prior run on ordinary publication errors.

**Overwrite resets manual edits to the targeted body-part canvas** after archiving them. It never edits species canvases. Close the target canvas during overwrite and avoid simultaneous collaborators editing references while the workflow is running. Publication spans several filesystem operations; do not interrupt it or treat it as a substitute for backups.

Embeddings are cached by source-image checksum, model, preprocessing and framework version. Unchanged images can reuse those vectors even in a new run. For fresh model computation:

```bash
python scripts/run_workflow.py --body-part head --recompute
```

`--seed 42` controls the layout, and `--max-edge 600` controls preview size. Exact repeatability also depends on package versions and platform; installed versions are recorded in `run.json`.

A failed run retains `.staging-...` with its reports for diagnosis. Retry with a new run name after correcting the issue. A `.workflow.lock` directory prevents simultaneous pipeline runs. If a process was forcibly terminated, confirm that no workflow process is running before removing that empty lock directory.

## Individual stages and offline inputs

Most users should use `run_workflow.py`. The stage scripts are for inspecting intermediate results in a **new scratch directory**:

```bash
python scripts/select_images.py --body-part head --work-dir /tmp/head-scratch
python scripts/resize_images.py --work-dir /tmp/head-scratch --max-edge 600
python scripts/embed_images.py --work-dir /tmp/head-scratch --cache-dir /tmp/head-features
python scripts/create_canvas.py --work-dir /tmp/head-scratch --run scratch-head
```

The last command produces a scratch `generated.canvas` whose paths expect `runs/scratch-head/` inside a vault. It does not publish the run. Use the complete workflow for automatically installed, linked canvases. Stage scripts refuse to regenerate a completed run's images/features or an existing generated canvas.

For a complete saved API-row array, use `--snapshot /path/rows.json`. The JSON must contain `id`, `catalogNumber`, `bodyPart`, `imageToUse` and `images` with Baserow attachment metadata. Do not pass only one page of API results. With `--image-root /path/attachments`, the workflow reads local JPEGs named by Baserow storage name, falling back to visible filenames, instead of downloading. Storage names avoid collisions between repeated camera filenames. This is useful for tests and offline replay. Snapshots may contain access URLs; keep them outside Git.

## Interpretation and validation

VGG16 is a general image model. t-SNE proximity and grid neighbours are suggestions for browsing, **not inferred species or evolutionary relationships**. Orientation, colour, preservation and background can drive similarity. Images are letterboxed rather than stretched for the 224 × 224 model input; no automatic rotation, segmentation or magnification correction is applied.

Tiny or identical-feature collections use a simple grid because t-SNE would be uninformative. Larger runs use up to 50 PCA components, t-SNE with a sample-adjusted perplexity, then RasterFairy on a near-square masked grid (including prime image counts). RasterFairy 1.0.6's obsolete `np.float` call is handled inside its module without changing NumPy globally.

Run the regression checks from the repository root:

```bash
python -m unittest discover -s tests -v
```

Tests cover selection policy, reversed attachment order, catalogue filenames and image links, overwrite refusal when species canvases reference images, and archival link preservation.

Generated runs, caches and machine-specific Obsidian settings are ignored by Git by default to avoid accidentally uploading duplicated image data or personal layouts. After reviewing what should be shared, add specific run folders and canvases explicitly (with `git add -f` for ignored paths), including every image they reference. The scripts, requirements and documentation are tracked normally.
