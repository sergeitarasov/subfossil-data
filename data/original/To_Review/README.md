# Specimen review guide for Giulio

Prepared 6 October 2026. This review is required before using the collection for morphological measurements, classification, stratigraphic comparisons or evolutionary analyses.

The aim is to establish which specimen each record and photograph represents, verify its collecting information, choose suitable images, and resolve or explicitly document uncertainties. Do not fill gaps by guessing. An unresolved record is useful if its limitations remain visible.

## Where to work

Use the **Subfossils workspace → Subfossil collection → Specimens** table in [Baserow](https://fip-86-50-23-51.kaj.poutavm.fi/database/206/table/672/2810) as the working review database. Access requires a collaborator account. The [Excel review workbook](../../../To-Review/subfossil-review.xlsx) is an initial snapshot; it will not automatically reflect Baserow edits. If reviewing offline, arrange how corrections will be reconciled before editing both copies.

Consult the original label workbook, [Morphotypes_labels.xlsx](../Morphotypes_labels.xlsx), and [subfossil_magnification_Giulio.xlsx](../subfossil_magnification_Giulio.xlsx), using the sheet and row references in `labelSource` and `giulioSource`. The [image README](../README.md) and [image manifest](../image-manifest.json) document original paths, naming exceptions and checksums.

The initial import contains **1,720 catalogue records**, with **1,658 images matched to 1,641 identifiers**; **79 records have no matched image**, and **17 identifiers have two images**. These are import counts, not current review progress or counts of biological individuals.

## 1. Verify identity and detect mislabelling

- Match `catalogNumber` to the source label, original specimen folder and photograph. Check for a photograph assigned to the wrong voucher, duplicated identifiers, switched labels, or inconsistent body-part codes.
- Retain stable identifiers and the historical `bodyPartID`. Correct `bodyPart` when anatomy was misidentified; do not rename an identifier merely to make it agree with the corrected anatomy.
- If an identifier actually represents two specimens, record the evidence and flag it for coordinated correction of the database, filenames and links. Do not silently merge or split records.
- Distinguish repeated photographs of one fragment from different fragments or biological individuals. Record known associations between body parts only when supported by specimen documentation.

**Priority cases:**

| Record(s) | What needs checking |
|---|---|
| `ROD-SF-head-134` | Two labels assign the same identifier to **10–15 cm** and **95–100 cm**, with competing morphotypes. Establish whether this is duplicate transcription or two different vouchers. Preserve both labels until resolved. A source note mentions aDNA extraction (`aDNA16`); verify its association. |
| `ROD-SF-pyg-8` | Both sources annotate it as an **elytron**, despite the historical pygidium identifier. Verify the photograph and correct `bodyPart` if confirmed. |
| `ROD-SF-pron-220`–`ROD-SF-pron-229` | Source folders had a trailing ` 2`, removed during filename normalization. Confirm voucher identity; the suffix itself does not establish a second specimen or second view. See the image README for the unavailable unsuffixed `220` entry. |

## 2. Verify locality, sample and label information

Check each record against its source label, and use field notes or physical labels when the spreadsheets disagree.

| Field | Review required |
|---|---|
| `island` | Confirm Mauritius or Rodrigues from collecting evidence, not only the ID prefix. |
| `locality` | Confirm the site and its spelling, including Grotte Fougere or Mare Aux Songes where applicable. Retain more detailed collecting information for dry reference specimens. |
| `depthCm` | Confirm the complete sediment interval, such as `5-10` or `30-60`. Preserve it as an interval. Leave unknown values blank rather than assigning zero or a midpoint. |
| `fieldNumber` | Verify Mauritius sample codes such as `MRU_MAS...` against the label. Confirm what each code identifies; do not infer a depth from it. |
| `verbatimLabel` | Check transcription against the source. Keep the wording of the actual label; place interpretations and explanations in the structured fields and `notes`. Retain unchanged `sourceLabel1` and `sourceLabel2`. |
| `recordedBy` | Initially Nick Porch for wet material and Owen Griffiths for dry material, as instructed by the project owner. Verify exceptions. This is the collector, not the photographer or taxonomic identifier. |
| `preparations` | Confirm `wet` or `dry`. Preparation alone does not establish geological age. |
| `batch` | Preserve the sheet-based assignment below; do not infer it from specimen numbering, depth or photographic date. |

Batch assignments: `SubFoss_I_batch` and `SubFoss_I_batch_MUR` → **1**; `SubFoss_II_batch_30-60` → **2**; the nine `Dry_specimens_ROD` records → **NA**, as explicitly requested.

**Depth is not an age estimate.** Later temporal analyses require independently supported dates or an age–depth model linked to the appropriate site and sample. Do not assume equivalent depths on different islands represent equivalent ages. Keep dry reference material distinguishable from the subfossil series.

## 3. Review images and choose those to use

- Inspect the attached preview, then open `originalURL1` and, where present, `originalURL2` for full-resolution assessment. Baserow attachments are reduced review copies; use original-resolution images for quantitative annotation.
- Verify specimen identity and anatomy, focus, stacking artefacts, visibility of margins, orientation, oblique views and whether the part is complete or broken. Record anything that limits measurement or identification.
- Set `imageToUse` to **View 1**, **View 2**, **Both**, or **Neither**. Leave **Not decided** while unresolved. For one usable image, choose View 1. If Both is selected, explain each image's role; two photographs must not automatically become two independent specimens or measurements.
- View numbering follows file ordering, not quality or anatomical orientation. `__view-02` only distinguishes the second file. Confirm view identity using the original URLs.
- For missing images, check the OneDrive source folders and specimen records. Record whether an image was never taken, was not matched, needs recovery, or requires new photography. Missing imagery does not by itself invalidate the label record.
- Preserve every original image, even if unsuitable. Explain rejection or replacement in `notes`; do not delete originals or overwrite their content.

For elytron and pronotum length, identify whether both required anatomical endpoints are present. A broken fragment's visible length must not be reported as complete organ length. Oblique views can underestimate length even with a correct calibration.

## 4. Resolve magnification and validate calibration

Compare `sourceMagnificationLabels` with `sourceMagnificationGiulio`, consult acquisition notes, and enter a supported working value in `magnification`. Preserve both source values and explain the decision in `notes`.

The 5 October audit found **68 conflicting records**: 66 with images and two without. **None was independently resolved by that audit.** All 66 conflicting stacked images lacked EXIF metadata, and their inspected Zerene projects had empty magnification fields. Equal image dimensions do not establish equal physical scale.

For example, `ROD-SF-elytra-259` has **4x** in the label workbook versus **3x** in Giulio's workbook. Do not choose one simply because the resulting beetle size seems plausible.

To resolve a conflict, seek an explicit acquisition-setting record, independently measure the same physical fragment, or compare the same fragment with an image whose scale is verified. Document the evidence. If it remains unresolved, leave the working magnification blank and retain the competing values in the source fields and notes.

Calibration photographs are in the OneDrive `General/subfossil_pictures/Magnification_index` folder. Before using them to convert pixels into millimetres:

- Confirm the ruler units and smallest division. **0.1 mm is currently a provisional interpretation, not independently verified.**
- Establish which microscope, camera adapter, additional lens, image resolution and processing settings apply to each specimen image. The calibration photographs date to January 2023; applicability to earlier images must be established.
- Keep **5.5x** and **5.5x + lens** distinct. The photographed tick spacings differ by approximately a factor of 1.61; the nominal setting alone is insufficient.
- Record a traceable calibration reference and pixels per millimetre for each image used for measurement. Account for resizing and any relevant stacking scale changes; cropping alone does not establish a new pixel scale.

Pixel-coordinate annotations can be collected before calibration is resolved, but physical lengths must remain unavailable or explicitly provisional until calibration is verified. Do not infer scale from expected body size or surface texture.

## 5. Review anatomy, taxonomy and morphotypes

- Verify `bodyPart`, including unknown material and combined head/pronotum preparations.
- Review `family`: **Scarabaeidae was prefilled and is not a verified identification**. “Not a dung beetle” does not by itself establish another family. Confirm a supported family or leave the identification unresolved with an explanation.
- Pay particular attention to source exclusions or doubts for `MAU-SF-head-7`, `ROD-SF-head-153`, `ROD-SF-head-344`, `ROD-SF-metast-20` and `ROD-SF-metast-133`.
- Fill `genus` and `specificEpithet` only to the supported identification level. `specificEpithet` contains the epithet alone, without the genus. Document uncertainty and the basis of identification in `notes`.
- Check `tentativeMorphotype` against `sourceMorphotype` and the image. Confirm what each code means within its anatomical and source context. Do not assume identical codes across body parts imply the same species.
- Preserve non-target material in the catalogue and record why it should be excluded from a particular analysis.

## 6. Record decisions and complete the review

`reviewFlags` contains findings from the initial import and **does not automatically update after corrections**. Address each flag in `notes`, preserving the source fields as evidence. Review unflagged records too: absence of a flag is not verification.

Use a consistent note format, for example:

```text
YYYY-MM-DD | Giulio | field/issue | previous value -> reviewed value
Evidence: workbook/sheet/row, physical label, acquisition log or image reference.
Remaining uncertainty: ...
Analysis use: eligible / hold / exclude for [named analysis], with reason.
```

This is a note convention, not an additional database field. Do not record a hypothetical correction as if verified.

Fill `reviewedBy` and `reviewedDate`. Check **completed** only after identity, label/locality information, anatomy/taxonomy, image selection and source conflicts have been reviewed and their outcomes documented. Leave it unchecked when a required decision is still pending. A deliberately unresolved identification can remain unknown if the evidence limit and analytical implications are explicit.

**Completed is a review status, not blanket permission to include the record in every analysis.** Apply the following criteria when assembling downstream datasets:

| Intended use | Minimum requirements |
|---|---|
| Image-based classification | Secure image-to-voucher match; suitable chosen image; reviewed anatomy and relevant identification or morphotype; non-target material handled explicitly. |
| Length measurement in mm | Secure identity; suitable original image; agreed anatomical endpoints and completeness; verified image-specific pixel calibration; saved endpoint coordinates and measurement provenance. |
| Stratigraphic or temporal comparison | Secure site/sample/depth assignment; dry reference material distinguished; independent chronological evidence when numerical ages are needed. |
| Evolutionary analysis | Explicit taxonomic/morphotype treatment, justified specimen associations, analysis-specific inclusion decisions, and no accidental counting of duplicate views or associated fragments as independent individuals. |

The review deliverable is a curated Baserow table with justified corrections, selected images, reviewer/date information, and a clear list of unresolved cases. Preserve original files and source values so all decisions can be traced and the dataset can be revised without losing evidence.
