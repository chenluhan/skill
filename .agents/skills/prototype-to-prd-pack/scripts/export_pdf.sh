#!/usr/bin/env bash
set -euo pipefail

if [ $# -ne 1 ]; then
  echo "Usage: $0 <pack-dir>" >&2
  exit 1
fi

pack_dir=$1
export_dir="$pack_dir/export"
mkdir -p "$export_dir"

bundle="$export_dir/prd-pack.bundle.md"
pdf="$export_dir/prd-pack.pdf"

if [ -f "$pack_dir/00-change-summary.md" ]; then
  ordered_files=(
    "00-change-summary.md"
    "01-changed-pages.md"
    "02-changed-flows.md"
    "03-changed-rules.md"
    "04-open-questions-delta.md"
    "05-ai-delta-spec.md"
  )
else
  ordered_files=(
    "00-overview.md"
    "01-prd.md"
    "02-pages.md"
    "03-flows.md"
    "05-open-questions.md"
  )
fi

{
  for file in "${ordered_files[@]}"; do
    if [ -f "$pack_dir/$file" ]; then
      cat "$pack_dir/$file"
      printf '\n\n\\newpage\n\n'
    fi
  done
} >"$bundle"

if ! command -v pandoc >/dev/null 2>&1; then
  echo "[ERROR] 'pandoc' is not installed. Wrote bundle to $bundle" >&2
  exit 1
fi

engine=""
for candidate in wkhtmltopdf weasyprint prince xelatex pdflatex; do
  if command -v "$candidate" >/dev/null 2>&1; then
    engine=$candidate
    break
  fi
done

cd "$pack_dir"
if [ -n "$engine" ]; then
  pandoc "${ordered_files[@]}" --from gfm --resource-path "$pack_dir" --pdf-engine "$engine" -o "$pdf"
else
  if ! pandoc "${ordered_files[@]}" --from gfm --resource-path "$pack_dir" -o "$pdf"; then
    echo "[ERROR] PDF export failed. Wrote bundle to $bundle but no working PDF engine was found." >&2
    exit 1
  fi
fi

echo "[OK] Exported PDF to $pdf"
