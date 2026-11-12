# SpurAtlas

An interactive research atlas by **Abdulkadir Oshioze Nurudeen**
([ORCID 0000-0002-2646-5784](https://orcid.org/0000-0002-2646-5784)).

The main explorer compares ten pre-specified perforated-gear test layouts at
five saved reference-load mixtures. It presents direct numerical references
alongside fixed model estimates, preserves all safety-factor outcomes and
reports removed material at every selected target. A separate view compares
48 manufacturing/carbon scenarios for two documented 40-tooth cases.

## Run the website

The website is buildless: serve `dist/` using any static web server. No account,
database, API credentials, external fonts or third-party JavaScript libraries
are required. The hosting configuration in `.openai/hosting.json` is specific to
the current hosted Site and must be removed when importing into a different
hosting project. The static `dist/` directory can also be deployed to GitHub Pages.

The six independent pages are Home, Design check, Explore, Carbon payback,
Evidence & methods and About. `tools/build_pages.py` generates their HTML from
`src/atlas-content.html`; run it after editing that content template. The shared
modules initialize only the tools present on the current page. Applied design,
reference and research-index choices persist in the current browser session.
Explicit shared selections take precedence. Original root-section links route
to the corresponding page.

Run `npm test` for the numerical selection, carbon-arithmetic, source-ratio,
CSV, supported menus and page-navigation checks. No FE solve is run.

## Evidence and reproducibility

- [Supporting research release 2.0.0](https://doi.org/10.5281/zenodo.24144925)
- [Original benchmark release 1.0.0](https://doi.org/10.5281/zenodo.24055230)
- `dist/data/provenance.json` records exact source SHA-256 hashes and extraction checks.
- `dist/data/test-responses.csv` retains all 100 original static/fatigue comparisons.
- `dist/data/static-model-comparison.csv` retains both static formulations.
- `dist/data/carbon-scenarios.csv` retains all 48 original scenarios.
- `dist/data/atlas.json` contains the selected data and contours used by the website.

`tools/prepare_data.py --source /path/to/document-source` reconstructs the atlas
dataset from the retained research files. The source directory must contain
`release/Code_S2`, `release/Data_S1` and the supplied research `assets/`. The
script needs NumPy and SciPy and executes only the archived geometry functions,
not the solver. It checks geometric features against the frozen protocol,
recomputes all primary/fatigue predictions and checks every carbon payback.
The bundled precomputed dataset is sufficient to run or deploy the website.

## Scientific scope

The explorer uses ten independently selected geometries, not fifty independent
mixtures. Reference steel, geometry and meshes are fixed. T/P coefficients are
nonnegative with a+b=1 at the five saved mixture values. Static FE references
use the retained harmonic numerical capacity. Fatigue is assessed at five
million counted stress cycles, not measured component life. Static Model E is
the primary pre-specified formulation and Model H the secondary formulation;
all test outcomes, including Model E's 46-tooth criterion miss, remain visible.

The 40-tooth carbon examples and field illustrations are explicitly separate
from the 42/46-tooth test layouts. The illustrations are scikit-fem research
results, not ANSYS output. No map for a different gear is presented as the
selected layout's field. The earlier aluminium strain comparison does not
constitute experimental validation of every steel entry. Further production
and fatigue assessments are described in the site's methods.

## Attribution, reuse and publication

Use `CITATION.cff` to cite software release 0.6.0:
https://doi.org/10.5281/zenodo.24165269. The supporting research data retain their
own versioned DOIs. Site software is MIT-licensed; research data are CC BY 4.0
as specified by the source release. Third-party materials retain their own
licences. This software archive does not submit or publish the manuscript.
The Zenodo release includes source provenance, file checksums and replay
instructions. The live website can change; the versioned software DOI identifies
this preserved release.

The hosted Site is public. Release 0.3.0 also includes a nine-tooth-count index
of 631 traceable records and nine material options (eight published specimen
conditions plus the inherited research reference). Material calculations scale
the reference factors under the explicit homogeneous elastic assumptions.
They are not labelled as independent material validation.

Eight original material reports were retrieved and their property tables
checked for this release. Three SAE 8620 cards were corrected to the primary
reports: iterations 119, 120 and 121. The exact previous and corrected values,
PDF page locations and report hashes are in dist/data/material-audit.json.
Earlier archived manuscript/material-card inputs remain provenance records.
The supplied v22 submission supplement has been corrected separately; its
private manuscript files are not included in this public software archive.

Run tools/extend_evidence.py after prepare_data.py to build the extended
research index. The complete numerical ZIP is required for manifest
verification, rather than the compact document-source copy alone. The
reproduction check runs in a separate folder and leaves source inputs intact.

## SpurAtlas 0.3 design workflow

The new requirements check accepts only dimensions, material conditions,
operating references and fatigue exposure supported by retained case evidence.
Compatible layouts are ranked within the same gear specification. The mass
objective maximizes removal among cases meeting the recorded-factor and
conditional model-interval screens, excluding the documented large-sector
referral. The alternative objective maximizes the minimum conditional margin.
All compatible outcomes stay visible, including rejected or dominated cases.

Sensitivity intervals are conditional on the stated pointwise model-error
assumption. They are not calibrated uncertainty intervals. The original H
post-evaluation decision audit is independently replayed in software tests.
Model E remains primary and is now the default; H remains secondary.

Each of ten test layouts has SVG, sampled DXF, full-precision coordinate CSV,
authenticated mesh/topology summaries and source hashes. Original raw meshes
and one retained tooth-position displacement history per layout were fetched
and checked against archive/member/array hashes. Recovered regional stress
maxima match their stored assessments to better than 2e-9 relative error.
Case-specific T/P stress and displacement images show the axial top surface
at the retained T tooth-root-governing position. They are reference-material
plots and no new elasticity solution or physical validation is claimed.

The matched carbon calculator now uses the selected layout's exact area,
perimeter and removed mass. It exposes declared machine and service inputs,
reports energy, initial burden, mileage parity and net scenario emissions,
and compares calculated payback against designer-declared mileage in miles.
The retained roughing/finishing planner selects the case-specific cutter recipe,
including broad roughing and long-neck finishing tools where required. Applied
operations and electricity subtotals are shown and exported. The original
phase-8 planner, configuration and source hashes accompany the recipe records.
Integer flute counts, finite arithmetic and cutter limits are checked. Zero-savings
scenarios have no finite parity.
No universal manufacturing-route ranking or full LCA conformity is asserted.

Printable HTML reports embed the selected field image. JSON/CSV exports and
share links preserve applied numeric requirements. Project labels are kept
out of share links. Unapplied form or carbon edits disable exports to prevent
stale decision records. The static reproduction ZIP includes the exact
calculation modules, evidence, integrity manifest and dependency-free Node
replay, plus all tests. Production gear ratings and physical tests remain
explicitly unassessed rather than inferred from the screening factors.

Rebuild extension metadata with tools/build_engineering.py, recover images
with tools/render_case_fields.py using authenticated raw arrays, then package
with tools/package_reproduction.py. Regenerate the ZIP after every change to
its included source/data files.

## 0.3.1 comparison menus

All scientific entries in Define the comparison now use supported-choice
menus. Geometry menus are derived from complete retained case tuples; load
mixture, torque and speed are synchronized without rounding stored values.
Families update with the selected gear specification. Safety-factor choices
are 1.5–6.0 in 0.5 steps; sensitivity choices are the retained 5/10/15% tiers.
The fatigue exposure menu states the single retained five-million-cycle value.
Some dimensions have one available option; their menus remain enabled.

Results refresh after a menu choice. The optional project label remains free
text. Unsupported legacy link entries are explicitly replaced by available
menu values with a visible review notice; the numerical model still rejects
unsupported requests through its validation/replay interface. Matched-carbon
scenario inputs remain separate declared assumptions. No structural evidence,
material property, model coefficient or capacity reference was changed.

## Manufacturing fatigue-capacity requirement

Release 0.6.0 uses the terminology of the current v22 manuscript: primary
static model E with exponential load mixing, secondary static model H with
harmonic load combination, and power-law-based retention models. The selected
design now records kappa_min = required fatigue factor / recorded fatigue
factor, with a separate conditional requirement using the assumed-error lower
factor. The recorded value corresponds to manuscript Eq. (16). Neither route
is assigned an unmeasured retained capacity. Values above one are preserved.
The fixed fatigue-assessment exposure and designer-chosen mileage retain their
separate roles. JSON and printable reports include the calculation.
