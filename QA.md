# Verification — preview 0.1.0

Checked on 12 November 2026.

- All ten geometries reproduce the frozen opening-area fractions and ligament
  ratios using the archived geometric functions. No solver was executed.
- All 100 saved primary static/fatigue predictions agree with an independent
  evaluation of the fixed formula within 2e-12 absolute retention.
- The source retains all 50 secondary static-model comparison rows.
- All 48 carbon paybacks and net differences at the five-million-cycle
  reference agree with the retained source arithmetic within 1e-10.
- Five Node test cases pass, covering source-factor ratios, all 500 combined
  target comparisons, both carbon cases, URL-state restoration and CSV escaping.
  The per-response static/fatigue false-pass counts are preserved (three each
  for the H/fatigue comparison). These are related comparisons, not 500
  independent experiments.
- Desktop browser checks: geometry/family selection, automatic tooth-count
  filtering, G08 large-sector referral, target 6.0, static model E and fatigue
  chart selection. Values and target decisions update correctly.
- Responsive checks use live 390- and 375-CSS-pixel frames of the same site,
  including navigation, G10 selection, 100% T share, target comparison, the
  field-image modal and changed carbon-case/fuel-saving selections. No document
  horizontal overflow was observed at those widths. This is responsive browser
  testing, not testing on a physical iPhone or in Safari.
- The result-export handler produces its prepared-download status and its CSV
  serialization is tested. The cloud browser's download-event capture timed
  out, so capture of the completed browser-generated file is not claimed.
- No site-script error appeared in the inspected console output. Browser
  extension metadata messages were unrelated to the site.
- Visual checks found missing arrow glyphs in the browser's font; these were
  replaced with inline SVG icons. Mobile chart coordinates and select text
  sizes were adjusted after inspection.

Publication is owner-private. No GitHub repository, separate atlas DOI, journal
submission, live FE service or new physical-validation experiment is claimed.

## Release 0.2.0 extension

- All 631 index rows match the exact copied source CSV, source line number
  and full SHA-256 identity. The full numerical source manifest and 38
  fitting-source bindings pass authentication. The retained-summary replay
  passed again in an isolated directory; no new raw-field solution is claimed.
- Coverage is 32, 34, 36, 38, 40, 42, 44, 46 and 48 teeth. Missing static
  data for 32 teeth and missing fatigue data for 44 teeth are left absent.
- Eight published material conditions were checked against their original
  report tables. Five cards match; three SAE 8620 cards require corrections.
  Their source values and corrected calculations are recorded in the public
  material audit. The ninth option is the explicit inherited study reference.
- Seven automated tests pass, including material scaling and all nine
  conditions across the ten test layouts. Retention remains unchanged under
  the declared homogeneous elastic assumptions; absolute factors update.
- Earlier development, previously exposed benchmark and pre-specified test
  records keep separate evidence labels. No complete independent material
  and tooth-count test matrix is claimed.
- Browser checks confirmed the source-corrected SAE 8620 core 121 properties,
  working material selection and unchanged retention, plus the explicit
  fatigue-only/static-only boundaries for 32/44 teeth. The source-report
  link points to the matching original report.
- Desktop layout and 375, 390 and 768 px iframe checks passed. At each narrow
  size, document scroll width equals client width; the research table scrolls
  inside its own container. Controls and evidence labels remain readable.
  No site-script error appeared; an extension metadata message is unrelated.
- Release 0.2 preserves the existing public audience. The owner-private
  statement above records the earlier release's initial publication state.

## SpurAtlas 0.3.0 engineering workflow

- Fifteen automated checks pass. Requirements tests reject mismatched gear
  dimensions, unsupported tooth counts, arbitrary loads, different fatigue
  exposure, malformed model choices and invalid material selections.
- Candidate comparisons preserve a fixed gear specification, both separate
  safety-factor criteria and all compatible outcomes. Large-sector referral
  remains excluded from the automatic conditional shortlist.
- The conditional H sensitivity audit reproduces all 3,000 retained decisions.
  This is not interpreted as a calibrated probability or uniform error bound.
- Sixty new manufacturing/road fixtures computed by the original archived
  Python route equation match the JavaScript implementation. Tests cover zero
  fuel saving, added burdens, exposure boundaries and cutter curvature failure.
- All ten mesh and selected tooth-history files were retrieved from matching
  Dropbox archives. Archive, member and displacement-array hashes passed.
  Regional stress recovery reproduces recorded maxima with relative mismatch
  at most 2.23e-16. Images show genuine T/P reference fields on the axial top
  surface at each layout's T tooth-root-governing position. No new solve ran.
- The replay ZIP was extracted to an isolated directory and generated JSON
  and a self-contained printable HTML report. Its software checks pass.
- Browser review confirms the default G03 conditional candidate; a 46-tooth
  all-mixture request produces only six compatible layouts, ranks G10 first
  under the default mass objective and keeps G08 as a direct-FE referral.
  A 32-tooth design request returns an explicit unsupported-scope decision.
- Zero fuel-saving input produces no finite carbon crossing. Editing applied
  requirements or carbon inputs locks exports until recalculation. Share
  links omit project labels; exact case selection is preserved in new links.
- Browser report preparation reaches the prepared-download status and the
  same HTML serialization passes independent tests. Browser download-event
  capture timed out; retrieval of that completed browser file is not claimed.
- Mobile 375/390/768 px iframe checks show equal document client/scroll width
  after fixing overflow around matched-carbon and model-evidence tables.
  Wide engineering tables scroll inside their own containers.
- Native rendering of a recovered case image was visually checked. Field
  figures retain units, common T/P color ranges, material/reference labels and
  undeformed outlines. The two original 40-tooth figures retain separate scope.
- Certification, exact-case continuum convergence, full gear ratings, steel
  component tests and complete LCA conformity are not claimed. The UI and
  exports state their established status and required evidence explicitly.

## 0.3.1 supported comparison menus

- All scientific Define the comparison fields are enabled selects; only the
  optional project label remains a text input. Single-value study dimensions
  and exposure are visibly presented as current available menu options.
- Eighteen automated checks pass. The new menu tests cover every offered
  gear/load/safety-factor/sensitivity combination, synchronized torque/speed
  choices, family refresh and explicit normalization of obsolete shared links.
- Browser tests confirm changing tooth count updates available families and
  results immediately. Selecting torque or speed updates both coupled values
  exactly. The selected/all-five assessment menu refreshes the result without
  an extra submit step. Normal menu choices do not reach an unsupported-scope
  message; stricter numerical request validation remains in place.
- Unsupported values in an old link produce a visible review notice and a
  supported comparison. No unsupported engineering capacity is inferred.
- Mobile 375 px iframe review passes: the document has no horizontal overflow,
  dropdown controls remain enabled and their arrows are visible. The existing
  evidence, material verification, calculations and field plots are unchanged.

## 0.4.0 independent navigation pages

- Home, Design check, Explore, Carbon payback, Evidence & methods and About
  are six distinct static documents. Each has one main heading and each
  section page identifies the active menu item. Internal file and fragment
  links were checked across all six pages; no missing targets or duplicate IDs.
- Twenty-one automated checks pass, including storage failure handling,
  explicit shared-link precedence and routing original root links to their
  new page. Calculations and source data are unchanged apart from release
  metadata; the complete atlas dataset was compared with the previous commit.
- Browser navigation preserved a 46-tooth G08 comparison, SAE 8620 core 121,
  static factor 4, project label and applied matched-carbon fuel saving 0.26.
  Explorer G10/factor 4 and the 32-tooth research record also restored exactly.
  The separate carbon page retained its sector/0.26 settings.
- The evidence field dialog opens and closes on its page; the About citation
  loads the current release. An original root explorer link redirects to the
  correct page with its layout and target preserved.
- A 375 px iframe review confirms the design menu exposes all five section
  links, highlights the active page and closes after page navigation. Design
  and Evidence documents have equal client and scroll widths.

## 0.5.0 milling recipe and designer mileage

- Recovered the unchanged LCA08 geometry planner from the authenticated
  original archive (SHA-256 dc3adbcb91dc33a758659dbaeea761a924e84ca6096f6c89c8ebd0862c435c04).
  Applied its roughing/finishing selection to all ten complete retained cases.
  Circles and superellipses use one 20 mm cutter in two operations; the two
  sectors use a 12 mm rougher and a 3 mm long-neck finisher from two faces.
- Sixty fresh original-Python route calculations (ten layouts, three grid
  factors, two routes) agree with browser arithmetic to 2e-12 relative tolerance.
  Removed-volume fractions and operation, non-cutting and chip-press electricity
  reconcile. The two original nominal case recipes reconcile with their
  immutable source inventories. The recipe panel records reference tools,
  applied feeds, speeds, depths, engagement, times and electricity subtotals.
- Fractional flute counts, invalid cutter limits, nonfinite values and arithmetic
  overflow reject the calculation. A browser link with 1.5 flutes disables report
  and JSON export; restoring the recommended recipe resolves the error.
- Service distance, payback, fuel-saving units and exposure mapping display in
  miles. Exact conversion preserves the 18,631.80492601933-mile default.
  At 1,000 miles both G07 routes are flagged; at 200,000 miles both are within the
  chosen mileage, while the fixed five-million-cycle fatigue scope remains a
  separate statement. Zero mileage and blank input are handled explicitly;
  an extreme finite chart horizon contains no NaN/Infinity coordinates.
- Shared design links carry explicit mile-based inputs and restore the same
  case and tool conditions. Mileage persists between Design and Carbon pages.
  The original carbon page shows its exact nominal recipe as well as its
  retained scenario range. Its chart uses miles on the horizontal axis.
- At a 375 px iframe width, both pages have equal client and scroll widths;
  long operation tables scroll within their panel. Tool cards remain readable.
- All 26 automated checks pass. A JSON exported through the browser is replayed
  through the isolated download package with identical contents except for the
  regenerated timestamp; printable reports embed their selected field image.
- Atlas mechanical, material and original carbon records match the previous
  version exactly after excluding the release field. engineering.json and all
  previously retained case/material/source assets are byte-identical. The
  archived sources, case-study files and physical-validation scope are unchanged.

## 0.6.0 manuscript terminology and production capacity

- Terminology follows the current v22 manuscript whose PDF matches the author's
  attachment SHA-256 3211ac39f5c9ce55751d9b962d9c92039502b956611f64a2f587e9f31472a44a.
  Primary static model E and secondary static model H retain their original
  definitions, mathematical parameters and primary/secondary evaluation roles.
- The minimum retained fatigue-capacity requirement follows main Eq. (16).
  Recorded-factor and assumed-error conditional requirements are shown separately;
  unmeasured milling and EDM capacity ratios remain null. Values over 100% are
  preserved. Materials, safety-factor targets and all-mixture comparisons update
  the requirement. Mileage edits do not change its five-million-cycle basis.
- The manuscript fine-mesh examples and the G07 reference factor reproduce the
  threshold arithmetic. Browser G07 at a required factor of 3 gives 52.96% from
  the recorded factor and 59.63% with the declared 10% error assumption. G08 at
  required factor 6 displays requirements over 100% and retains its FE referral.
- At a 375 px frame width the capacity table is readable and the document has
  equal client and scroll widths. The existing recipe table scrolls internally.
- All 29 automated tests pass. Browser JSON and printable exports include the
  same production-capacity values; the isolated reproduction package replays the
  JSON exactly apart from the regenerated timestamp.
- All original mechanical data, material data, manufacturing recipes, coefficients
  and carbon scenarios remain byte-identical apart from interface release metadata.
