# Mascarene dung beetle subfossil images

Original-resolution stacked photographs for the study of dung beetle subfossils from Rodrigues and Mauritius, with dry reference specimens identified in the collection documentation.

The collection contains 1,658 JPEGs (approximately 5.56 GB), organized as:

```text
data/original/MAU/<body-part>/<voucher-ID>.jpg
data/original/ROD/<body-part>/<voucher-ID>.jpg
```

See [the collection README](data/original/README.md) for image counts, multiple images per voucher, normalized names, and dry reference material. The [image manifest](data/original/image-manifest.json) records original source paths and SHA-256 checksums.

Images retain their original bytes. Additional images of the same voucher have a `__view-02` suffix. This suffix distinguishes files; anatomical views and identifications still require curation.

A full clone downloads approximately 5.56 GB of photographs plus Git history. Individual images can also be accessed through GitHub. Camera frames and stacking-project files are held separately in the source archive.

## Baserow → Obsidian classification workflow

See [installation and run instructions](scripts/README.md) to select images by body part, build labelled similarity grids, and manage new or overwritten runs. Open `data/classification/` as the Obsidian vault.
