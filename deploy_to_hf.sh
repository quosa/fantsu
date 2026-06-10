#!/usr/bin/env bash
#
# Deploy the Fantsu Gradio app to a Hugging Face Space.
#
# Run this from a session/machine where:
#   - HF_TOKEN is set (fine-grained token with WRITE access to the Space repo).
#     In Claude Code on the web, add it as an environment SECRET — never paste it
#     in chat.
#   - huggingface.co is reachable (add it to the environment's network allowlist,
#     along with cdn-lfs.huggingface.co for LFS).
#
# The script copies the app files into the Space repo and pushes. It does NOT set
# GROQ_API_KEY — add that in the Space UI: Settings -> Variables and secrets ->
# Secret named GROQ_API_KEY.
#
# Usage:
#   ./deploy_to_hf.sh [space_id]
#   space_id defaults to jussikuosa/fantsu

set -euo pipefail

SPACE_ID="${1:-jussikuosa/fantsu}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ -z "${HF_TOKEN:-}" ]]; then
  echo "ERROR: HF_TOKEN is not set. Add it as an environment secret." >&2
  exit 1
fi

if ! command -v hf >/dev/null 2>&1; then
  echo "Installing huggingface_hub CLI ..."
  pip install -q -U "huggingface_hub[cli]"
fi

# Authenticate (reads the token from the env var; nothing is printed) and wire it
# into the git credential helper so the clone/push below can authenticate.
hf auth login --token "$HF_TOKEN" --add-to-git-credential

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

echo "Cloning Space $SPACE_ID ..."
git clone "https://huggingface.co/spaces/$SPACE_ID" "$WORK/space"

echo "Copying app files ..."
cp "$REPO_ROOT/app.py"          "$WORK/space/app.py"
cp "$REPO_ROOT/requirements.txt" "$WORK/space/requirements.txt"
cp "$REPO_ROOT/README.md"       "$WORK/space/README.md"   # carries the Spaces YAML header
rm -rf "$WORK/space/fantsu"
cp -r "$REPO_ROOT/fantsu" "$WORK/space/fantsu"
# Drop caches/build cruft that shouldn't ship to the Space.
find "$WORK/space/fantsu" -name '__pycache__' -type d -prune -exec rm -rf {} +
find "$WORK/space/fantsu" -name '*.pyc' -delete

cd "$WORK/space"
git add -A
if git diff --cached --quiet; then
  echo "No changes to deploy."
  exit 0
fi
git -c user.name="fantsu-deploy" -c user.email="deploy@fantsu.local" \
    commit -m "Deploy Fantsu Gradio app"
git push

echo "Done. Add the GROQ_API_KEY secret in the Space UI if you haven't:"
echo "  https://huggingface.co/spaces/$SPACE_ID/settings"
