ISV Ecosystem Cards (France)

Static site that renders per‑ISV cards summarizing SI/GSI ecosystems in France. Data is extracted from `system-integrator-litt.docx`.

Quick Start (Local)
- Build data: `python3 scripts/extract_isv_profiles.py`
- Serve: `python3 -m http.server 8000 -d web`
- Open: http://localhost:8000

Deploy to GitHub Pages (CLI)
- Requires GitHub CLI (`gh auth login`). Creates a new repo, pushes this project, and enables Pages from `docs/`.
- Run: `./scripts/publish_to_github.sh <repo-name>`
  - Example: `./scripts/publish_to_github.sh ecosystem-research`
  - Private: `VISIBILITY=private ./scripts/publish_to_github.sh my-private-repo`

What the script does
- Generate `web/data/isv_profiles.json` from the DOCX
- Sync `web/` → `docs/`
- Initialize git (if needed), commit, create the GitHub repo, and push
- Enable GitHub Pages (branch: `main`, path: `/docs`)
- Print your site URL

Notes
- Keep `system-integrator-litt.docx` in the repo root; the extractor reads it directly.
- `.gitignore` excludes `tmp_docx/` and typical local artifacts.
- If you update the DOCX, rerun the extractor and re‑push to refresh the site.

