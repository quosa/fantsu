# CI auto-deploy to Hugging Face Space

## Problem

The Fantsu Gradio app is hosted on a Hugging Face Space, but deploying meant
running `deploy_to_hf.sh` by hand after every change. We want the latest build
to ship automatically once a change lands on `main`.

## Approach

Add a `deploy` job to the existing `.github/workflows/ci.yml`:

- `needs: check` — deploy only runs if lint, typecheck, tests, and the wheel
  build all pass.
- `if: github.event_name == 'push' && github.ref == 'refs/heads/main'` — runs
  only on a merge/push to `main`. Pull requests still run `check` but never
  deploy.
- The job checks out the repo and runs the existing `./deploy_to_hf.sh`,
  passing `HF_TOKEN` from a GitHub Actions secret.

Reusing the script keeps a single source of truth for deploy logic (clone the
Space repo, copy `app.py` / `requirements.txt` / `README.md` / `fantsu/`,
commit, push) shared by local and CI runs.

### Script hardening

`deploy_to_hf.sh` relied on `hf auth login --add-to-git-credential` to make the
clone/push authenticate. That silently fails when git has no credential helper
configured — the case on a fresh machine and on CI runners — producing
`could not read Username for 'https://huggingface.co'`. The script now sets the
`store` credential helper when one isn't already configured (leaving existing
user config untouched), so `--add-to-git-credential` actually persists the token.

## Rejected alternatives

- **`workflow_run` triggered by the CI workflow.** More moving parts and a
  second workflow file to reason about; a `needs: check` job in the same
  workflow gives the same "only after green" guarantee more simply.
- **Deploy on every push to any branch.** Wasteful and would clobber the live
  Space from feature branches. Gated to `main` pushes only.
- **Inline the deploy steps in the workflow** (token-in-URL push). Duplicates
  logic already in `deploy_to_hf.sh` and risks the two drifting apart.

## One-time manual setup

Add `HF_TOKEN` as a GitHub Actions secret (repo **Settings → Secrets and
variables → Actions**) — the same fine-grained token with WRITE access to the
Space repo. The `GROQ_API_KEY` stays a Space-side secret and is unaffected.

## Verification checklist

- [ ] `HF_TOKEN` secret added to the repo's Actions secrets.
- [ ] `bash -n deploy_to_hf.sh` passes (syntax).
- [ ] On a PR: `check` runs, `deploy` is skipped.
- [ ] On merge to `main`: `check` runs, then `deploy` runs and pushes to the
      Space; the Space rebuilds to the new commit.
- [ ] A failing `check` blocks `deploy`.
