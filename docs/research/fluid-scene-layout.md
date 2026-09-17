# Fluid-scene layout audit

Research date: 2026-09-17.

This audit records spatial boxes on Yale f84r and f78v. It tests whether the
visible page layout supports one scene for one writing block. It does not read
the script, assign a meaning, or infer a reading order.

## Source images and coordinates

The source is the Yale IIIF manifest for [Beinecke MS 408](https://collections.library.yale.edu/manifests/2002046).
The inspected pages are [f84r, canvas 1006226](https://collections.library.yale.edu/iiif/2/1006226/full/full/0/default.jpg)
and [f78v, canvas 1006215](https://collections.library.yale.edu/iiif/2/1006215/full/full/0/default.jpg).
The private full-image inspection copies have these dimensions and SHA-256
values:

| Folio | Image size | SHA-256 |
|---|---:|---|
| f84r | 2753 × 3745 | `7e8fa7c29b6c6ab462ad5359bdabfcd60505622700f6e5cb18478d20cbd79fbe` |
| f78v | 2841 × 3706 | `9c574f3a564cc55252633174784745a075689be93a9c7249f381f71434f282e0` |

The private images are not included in this repository. Coordinates use the
source-image pixel grid. The origin is the top-left corner. `x` increases to
the right and `y` increases down. Each box uses `[x, y, width, height]`.
The boxes are approximate outer bounds. The JSON file records uncertainty in
pixels and gives the source URLs.

The term **scene unit** is a spatial label for an enclosure with drawn figures
and a colored area. It does not identify the object or its function. The term
**writing block** means a visible dense region of writing. It does not identify
a caption, paragraph, or language.

## f84r observations

The page has three visible scene units:

| ID | Box | Nearby writing | Boundary note |
|---|---|---|---|
| `f84r-s01` | `[120, 90, 2380, 800]` | `f84r-t01` below | The lower edge reaches the green lower margin before the first writing lines. Short marks inside the enclosure are not separate blocks. |
| `f84r-s02` | `[260, 1570, 1870, 550]` | `f84r-t01` above and `f84r-t02` below | The enclosure is between two dense writing regions. |
| `f84r-s03` | `[80, 2540, 1150, 850]` | `f84r-t02` above and `f84r-t03` right | The lower-left enclosure interrupts the lower writing region. |

The writing-block boxes used for these associations are `f84r-t01`
`[180, 780, 2200, 900]`, `f84r-t02` `[200, 2070, 2100, 510]`, and
`f84r-t03` `[1030, 2520, 1280, 760]`. The first box includes the lowest
visible rows. The third box includes the leftmost rows before the block
narrows. The JSON records the larger boundary uncertainty.

The winding colored line at `[55, 280, 250, 3340]` crosses the vertical level
of all three scene units. I kept it as a separate component. It does not give
a text association.

The audit marks three writing regions. Their boundaries do not identify
which scene each region describes. `f84r-t01` lies between the first two units. `f84r-t02` approaches the
third unit, and `f84r-t03` is to its right. The image does not show which lines,
if any, belong to one unit. The associations are therefore spatial candidates,
not evidence of a one-to-one relation.

## f78v observations

The page has one large scene unit:

| ID | Box | Nearby writing | Boundary note |
|---|---|---|---|
| `f78v-s01` | `[940, 1510, 1840, 730]` | `f78v-t01` above and `f78v-t02` below | The box includes the lower outlined extension because it touches the colored area. This inclusion is uncertain. |

The writing block above is `[960, 250, 1800, 1270]`. The writing block below
is `[950, 2140, 1820, 950]`. This larger box includes the upper gallows and
first visible rows near the lower outlined extension. The winding colored line at
`[760, 420, 350, 1450]` reaches the scene boundary but has no visible writing
link.

One scene unit lies between two dense writing blocks. The layout does not show
which lines, if any, describe that unit. The page therefore does not provide a
one-to-one scene-to-writing assignment.

## Conservative conclusion

The two pages support a repeated page pattern: drawn figure-and-color units
occur near dense writing. The boxes do not establish a stable one-to-one relation
between a unit and a writing block. This finding is about visible layout only.
It does not establish that the writing is unrelated to the drawings, and it
does not refute a semantic reading.

The full coordinate record is in [fluid-scene-layout.json](fluid-scene-layout.json).

## Next observation

A manual annotation can split each writing block into line rows and test local
line-to-unit distance. Such a split must keep uncertainty markers and must not
assign a line to a unit when the image gives no boundary.
