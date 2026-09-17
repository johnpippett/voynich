# f84r local repeat image audit

Date: 2026-09-17.

This audit checks the two fixed `visual_six` certificates selected before image review. It does not translate the text. It does not select a different certificate because it is easier to see.

## Sources and method

The fixed protocol is [the local cyclic falsification plan](../plans/vms-local-cyclic-falsification-v1.md). The source records are `data/raw/ZL3b-n.txt` and `data/raw/IT2a-n.txt`. The strict extractor is `experiments/local_cyclic/certificate.py`. The result records are:

- `results/vms-local-cyclic-falsification-v1/ZL3b-n-visual_six.json`
- `results/vms-local-cyclic-falsification-v1/IT2a-n-visual_six.json`

The inspected Yale image is [the full Yale IIIF image](https://collections.library.yale.edu/iiif/2/1006226/full/full/0/default.jpg). Its canvas is [Yale canvas 1006226](https://collections.library.yale.edu/manifests/oid/2002046/canvas/1006226). The local file is `assets/yale-folio-84r.jpg`, with dimensions 2753 x 3745 pixels and SHA-256 `7e8fa7c29b6c6ab462ad5359bdabfcd60505622700f6e5cb18478d20cbd79fbe`.

Coordinates use the image pixel grid. The origin is the top-left corner. The boxes below are review boxes. They are not palaeographic boundary claims.

## ZL certificate

The predetermined record is source record index 3213, locus `f84r.13,@P0`, candidate word index 2, unit index 3, and unit span `[3,4]`. The selected unit label is `e`. The source line is 5053 in `data/raw/ZL3b-n.txt`.

The locus is the first body line below the upper green pool. Candidate index 2 is the third candidate on that line. A conservative candidate review box is `[500,790,300,180]`. The approximate review box for the selected adjacent unit span is `[620,790,120,180]`. Allow at least 60 pixels of positional uncertainty because the line is slanted and the source word boundaries are not drawn on the image.

The line and the third candidate region are image-located. The image status is `image_uncertain`. The selected source span is not independently visible as two atomic `e` units. Some strokes can be parts of a larger glyph or ligature. The image therefore cannot confirm the unit boundary or the linguistic status of the repeated unit.

## IT certificate

The predetermined record is source record index 3200, locus `f84r.6,@Ln`, candidate word index 0, unit index 2, and unit span `[2,3]`. The selected unit label is `i`. The source line is 3368 in `data/raw/IT2a-n.txt`.

This locus is in the upper label band above the figures. The source order identifies the label record, but it does not provide a pixel coordinate. A broad review box for the likely central label band is `[1250,300,650,250]`. A smaller pair review area is not reported because the neighboring label runs cannot be separated with confidence from this image view. Allow at least 120 pixels of positional uncertainty.

The label band is image-checked, but the target label and the selected adjacent span are not uniquely isolated. The image status is `image_uncertain`. The image cannot confirm two atomic `i` units, and it cannot establish that the selected source units correspond to separate historical glyph units.

## Result boundary

Both records remain valid data-level certificates for the fixed `visual_six` source-unit model. This image audit does not strengthen them into palaeographic or historical readings. A visual check can test location and visible form. It cannot, by itself, prove the source unitization, a glyph boundary, a ligature split, or a plaintext symbol.

The two fixed certificates are therefore `image_uncertain`, with no image-verified atomic repeat. A future manual annotation should mark every visible stroke group and its uncertainty before any claim about glyph identity. Keep that annotation separate from the fixed source-unit result.
