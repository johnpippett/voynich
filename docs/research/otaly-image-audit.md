# Image audit for repeated `otaly` labels

Research date: 2026-09-17.

This note checks three `Lz` loci in original Yale images. It checks written
shape only. It does not assign a language, a plaintext, or a meaning.
The results are AI image inspections. They are not palaeographic certification.

The source record is the Yale IIIF Presentation 3 manifest for Beinecke MS
408. The manifest was retrieved on 2026-09-17. Its private local copy has
SHA-256 `317d58fd9ea90392a83d9858a91eada3d0b41416a3c835857dc0154bd123a309`.
The full JPEG files were kept as private inspection copies. They are not part
of this repository. Each image came from the Yale IIIF image service.

## Position method

The IVTFF item number is a source identifier. It is not a figure number.
For each item, I used the page header, the ring description, and the clock
position in the item metadata. I then located the named ring and nymph at that
clock position in the Yale image. I used the neighbouring labels only as a
layout check.

The three source entries state:

| Locus | IVTFF layout evidence | Image position used |
|---|---|---|
| `f70v2.15,&Lz` | Pisces, outer ring, `04:30`; ZL3b lines 3454-3485 | Outer ring, lower-right sector of the Pisces panel |
| `f72v3.31,&Lz` | Leo, inner band, `08:30`; ZL3b lines 3741-3782 | Inner band, lower-left sector of the Leo panel |
| `f73r.6,@Lz` | Scorpius, outer full circle, `11:00`; ZL3b lines 3881-3896 | Outer full circle, upper-left sector |

The `f70v2` header describes two fish in the centre. This identifies the
Pisces panel in Yale canvas `1006200`, whose manifest label is `70v (part)`.
The `f72v3` header describes Leo. It identifies the left zodiac panel in
canvas `1006204`, whose manifest label is `72v (part)`. The canvas contains
more than one panel. The panel assignment is therefore a layout observation,
not a Yale label claim. Canvas `1006206` has the exact manifest label `73r`.

The same three EVA strings occur in the IT2a file at lines 2178-2193,
2355-2386, and 2457-2463. This is a transcription cross-check. It is not a
second physical image observation.

## Image records and results

| Locus | Yale canvas and image | Private source hash | Inspection crop | Result |
|---|---|---|---|---|
| `f70v2.15,&Lz` | [canvas 1006200](https://collections.library.yale.edu/manifests/oid/2002046/canvas/1006200); [full image](https://collections.library.yale.edu/iiif/2/1006200/full/full/0/default.jpg) | `062ff6a9f14d0c16eb12dc8f6dc480771b7c19746ebdb20302b998e66181ccea` | Context crop `x=2550,y=2300,w=900,h=800`; [context image](https://collections.library.yale.edu/iiif/2/1006200/2550,2300,900,800/full/0/default.jpg); SHA-256 `632388ef98dd439f4315522ed8b8a435b7b568d67acff4263c89b080db0577fe`. Complete target enclosure `x=2580,y=2680,w=400,h=330`; [target image](https://collections.library.yale.edu/iiif/2/1006200/2580,2680,400,330/full/0/default.jpg); SHA-256 `e486c5bf9d47a644a6d1d29b9bc10e4860998171234f1c2f414de8e252c396bd` | **Consistent with the transcription at the located locus.** The complete target enclosure contains the dark, oblique run below the `04:30` nymph and to the right of its star. A large upright component is near the upper-right end in the page view. This description is visual only and does not state a reading direction. This is a shape check only. |
| `f72v3.31,&Lz` | [canvas 1006204](https://collections.library.yale.edu/manifests/oid/2002046/canvas/1006204); [full image](https://collections.library.yale.edu/iiif/2/1006204/full/full/0/default.jpg) | `2552b2eafb7948d182e52ec49e96a5d92a774917924aea594fb1ac3af3bfcdc5` | `x=1550,y=2050,w=900,h=700`; [source crop](https://collections.library.yale.edu/iiif/2/1006204/1550,2050,900,700/full/0/default.jpg); SHA-256 `9fb825bece79c9d21e61c773f77b42f8d26fbc823acfde364c13ad3804a95835` | **Uncertain.** The lower-left inner-band region is present, but the ink is faint and several ring texts overlap. I cannot isolate one complete five-unit run with confidence. The unit boundaries are less visible than at the other two loci. I found no visible contradiction, but I do not count this as an image-confirmed equality. The neighbouring `f72v3.32` item is a separate `09:30` entry and was excluded. |
| `f73r.6,@Lz` | [canvas 1006206](https://collections.library.yale.edu/manifests/oid/2002046/canvas/1006206); [full image](https://collections.library.yale.edu/iiif/2/1006206/full/full/0/default.jpg) | `5bc8e07dbd61cc1f218cfc4449cd527be118aa7884878ec4c8e568e9c2d89bad` | Context crop `x=650,y=800,w=700,h=550`; [context image](https://collections.library.yale.edu/iiif/2/1006206/650,800,700,550/full/0/default.jpg); SHA-256 `577b20a2c806aaf76f79e78f90bb69db8ef54b56050ace3cb9fb24de7dab2f9d`. Target rectangle `x=800,y=950,w=260,h=220`; [target image](https://collections.library.yale.edu/iiif/2/1006206/800,950,260,220/full/0/default.jpg); SHA-256 `740b5065e5ca941991a7a8a52bab1f264961c577e96d4d238d9d0b86b71b1d69` | **Consistent with the transcription at the located locus.** The target is the short, dark run beside the `11:00` outer-circle nymph. It slants toward the upper right, with the circle boundary below it. The separate `f73r.1,@Lz` item is also recorded as `otaly`; it is a different top-four label and was not used as evidence for `.6`. |

The equality class is therefore **provisional**. Two loci are consistent with
their transcription entries in this image inspection. The `f72v3.31` image
position needs a manual annotation pass before all three loci can support one
image equality observation.

## Limits and follow-up

The crop links are direct Yale IIIF regions. They contain no added marks or
redrawn text. The full images and crops are private inspection copies only.

The next step is a manual annotation of the `f72v3` inner band. Record the
crop coordinates, ring, clock position, and glyph-unit boundary. Use a Yale
high-resolution source if the faint ink still prevents a unique boundary.
Do not infer a plaintext from this label class.

## Sources

1. [Yale IIIF manifest for Beinecke MS 408](https://collections.library.yale.edu/manifests/2002046).
2. [Yale detailed catalogue for Beinecke MS 408](https://pre1600ms.beinecke.library.yale.edu/docs/pre1600.ms408.htm).
3. [ZL3b IVTFF transcription](https://www.voynich.nu/data/ZL3b-n.txt).
4. [IT2a IVTFF transcription](https://www.voynich.nu/data/IT2a-n.txt).
