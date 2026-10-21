# Brand assets

The README uses a raster wordmark with printed registration traces: a reference line and an observed line that diverges. The earlier companion invoice illustration is archived and no longer displayed in the README.

Both PNGs were generated specifically for the project with OpenAI image generation. Keep the complete compositions and their text legible. See [provenance](PROVENANCE.md) for the distinction between artwork and executable evidence.

| Current README asset | Use |
|---|---|
| `assets/readme-header.png` | project title and comparison motif |
| `assets/invoice-check.png` | archived invoice illustration; not displayed in the README |

## Legacy signal assets

The earlier mark is a continuous signal between two endpoints. Its navy-to-blue-to-mint path represents one declared scenario moving across implementations while preserving its returned value and observable effects. These assets remain available but are no longer used by the README.

## Files

| Asset | Use |
|---|---|
| `assets/logo.svg` | primary transparent vector on light backgrounds |
| `assets/logo-dark.svg` | accessible transparent vector on dark backgrounds |
| `assets/logo-ai-master.png` | transparent raster master preserved from the selected generated concept |
| `assets/logo-512.png` | general-purpose transparent raster |
| `assets/logo-dark-512.png` | dark-background transparent raster |
| `assets/favicon-32.png` | compact UI and browser use |
| `assets/favicon-64.png` | high-density compact UI use |
| `assets/social-preview.svg` | editable 1280 x 640 repository preview source |
| `assets/social-preview.png` | rendered repository social preview |

## Palette

| Name | Hex | Role |
|---|---|---|
| Signal navy | `#081b37` | first endpoint and light-background anchor |
| Signal blue | `#1e96f5` | comparison pulse |
| Signal teal | `#28b9c7` | transition |
| Signal mint | `#43d3a1` | second endpoint and successful parity |
| Dark-mode anchor | `#d9ecff` | accessible replacement for navy on dark backgrounds |

Keep the mark upright, preserve clear space of at least one endpoint width, and use the dark variant whenever the navy endpoint loses contrast. Do not place the mark inside an additional rounded-square app tile, redraw the signal, or recolor individual sections independently.

For the legacy signal mark, SVG files preserve the editable source. Its raster master records the earlier generated direction; its smaller PNGs are deterministic renders of those tracked vectors. The current README images are independent raster originals.
