#!/usr/bin/env bash
set -euo pipefail

if [ $# -ne 1 ]; then
  echo "Usage: $0 <pack-dir>" >&2
  exit 1
fi

pack_dir=$1
diagrams_dir="$pack_dir/diagrams"
rendered_dir="$diagrams_dir/rendered"

if [ ! -d "$diagrams_dir" ]; then
  echo "[ERROR] Missing diagrams directory: $diagrams_dir" >&2
  exit 1
fi

mkdir -p "$rendered_dir"

config_file=$(mktemp "${TMPDIR:-/tmp}/mermaid-render.XXXXXX.json")
trap 'rm -f "$config_file"' EXIT
cat >"$config_file" <<'EOF'
{
  "flowchart": {
    "htmlLabels": false
  }
}
EOF

if [ -z "${PUPPETEER_EXECUTABLE_PATH:-}" ]; then
  candidates=(
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"
    "/Applications/Chromium.app/Contents/MacOS/Chromium"
  )
  for binary in "${candidates[@]}"; do
    if [ -x "$binary" ]; then
      export PUPPETEER_EXECUTABLE_PATH="$binary"
      echo "[INFO] Using local browser for Mermaid rendering: $binary"
      break
    fi
  done
fi

renderer=()
if command -v mmdc >/dev/null 2>&1; then
  renderer=(mmdc)
  echo "[INFO] Using installed mmdc renderer."
elif command -v npx >/dev/null 2>&1; then
  renderer=(npx -y @mermaid-js/mermaid-cli)
  echo "[INFO] Using npx fallback for Mermaid CLI. First run may take several minutes while dependencies install."
else
  echo "[ERROR] Mermaid renderer not found. Install 'mmdc' or provide 'npx' access." >&2
  exit 1
fi

shopt -s nullglob
files=("$diagrams_dir"/*.mmd)
if [ ${#files[@]} -eq 0 ]; then
  echo "[OK] No Mermaid source files found in $diagrams_dir"
  exit 0
fi

count=0
echo "[INFO] Rendering ${#files[@]} Mermaid file(s) from $diagrams_dir"
for src in "${files[@]}"; do
  base=$(basename "$src" .mmd)
  out="$rendered_dir/$base.png"
  "${renderer[@]}" -i "$src" -o "$out" -b transparent -c "$config_file" -s 2
  count=$((count + 1))
done

echo "[OK] Rendered $count Mermaid diagram(s) into $rendered_dir"
