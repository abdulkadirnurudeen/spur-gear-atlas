# SpurAtlas on GitHub Pages

The website is published from dist/ by .github/workflows/pages.yml after the
software checks pass. Its pages, engineering data, numerical models and
appearance come from SpurAtlas release 0.6.0. Hosting links are recorded in
CITATION.cff and GITHUB_PAGES_PROVENANCE.json.

On the first run, the workflow verifies the uploaded source archive against
its SHA-256 identity, imports the source and adjusts the website links.
Subsequent runs use the tracked source directly. The reproduction package is
rebuilt after changes to its included files. No finite-element solve is run.

The earlier hosted Atlas remains available. GitHub publication does not add
physical validation or production qualification to the retained research.

Software archive: https://doi.org/10.5281/zenodo.24165269
Supporting numerical release: https://doi.org/10.5281/zenodo.24144925
Original benchmark: https://doi.org/10.5281/zenodo.24055230

Software: MIT. Research data: CC BY 4.0. Third-party rights are retained.
