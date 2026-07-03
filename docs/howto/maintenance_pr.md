# Documentation Maintenance & PR Quality Gate

This document outlines the rules and verification checklists required to maintain documentation accuracy and prevent drift between codebase implementation and system specifications.

---

## 1. Docs-as-Code Maintenance Creed

The documentation repository is a first-class citizen of the codebase. We enforce the following principles:
- **No Orphan Code Changes**: Any PR modifying public APIs, risk limits, model formulations, or database schemas **must** contain corresponding updates to the markdown documentation within the same commit.
- **Strict Verification Gate**: Code merges are blocked on any lint errors, unit test failures, or broken local documentation links.
- **Docstring Completeness**: All public classes, methods, and functions in the `src/wc2026/` directory must maintain complete docstrings conforming to the NumPy/JAX documentation style.

---

## 2. Pull Request Review Checklist

When submitting or reviewing a Pull Request, verify the following:

### 2.1 Code & Schema Verification
- [ ] If a model parameter or weight is modified, has [`configs/default.yaml`](file:///Users/shreejitverma/github/footbal_prediction/configs/default.yaml) and [`docs/reference/configuration.md`](file:///Users/shreejitverma/github/footbal_prediction/docs/reference/configuration.md) been updated?
- [ ] If a database table column is added or dropped, is the table schema updated in [`docs/reference/data_dictionary.md`](file:///Users/shreejitverma/github/footbal_prediction/docs/reference/data_dictionary.md)?
- [ ] If a FastAPI route is changed, does it match [`docs/reference/api_openapi.md`](file:///Users/shreejitverma/github/footbal_prediction/docs/reference/api_openapi.md)?

### 2.2 Link & Typo Checks
- [ ] Run the link verification script locally before pushing:
  ```bash
  make docs-verify
  ```
- [ ] Confirm there are no dead anchor fragments (`#`) or broken relative file paths.

---

## 3. Pre-commit Hook Integration

To automate documentation link audits, the pre-commit framework is configured to run link-checks on every git commit.

### Setup Pre-commit Hook
Run the setup target:
```bash
make hooks
```
This appends the execution block to `.git/hooks/pre-commit`:
```bash
#!/bin/bash
# Pre-commit hook to verify documentation links
echo "Auditing documentation links..."
make docs-verify || { echo "[FAIL] Commit aborted due to broken documentation links."; exit 1; }
```

---

## 4. Documentation Hosting & Build Pipeline

The documentation site is generated statically via MkDocs and can be deployed to any static host.

### 4.1 Local Server Serving
To spin up a local preview server tracking source file changes:
```bash
make docs-serve
```
*Accessible locally at: `http://127.0.0.1:8001`*

### 4.2 GitHub Pages Deploy
To compile the static pages and push directly to the `gh-pages` branch:
```bash
uv run mkdocs gh-deploy
```

### 4.3 CI/CD Automation
The GitHub Actions workflow [`.github/workflows/ci.yml`](file:///Users/shreejitverma/github/footbal_prediction/.github/workflows/ci.yml) builds and asserts doc compilation accuracy on every merge to `main`:
```yaml
jobs:
  docs-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - name: Install dependencies
        run: |
          pip install uv
          uv sync --extra dev
      - name: Verify Documentation Links
        run: make docs-verify
```
