#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: bootstrap_dependencies.sh [--check-only]

Install or verify the local dependencies required for stable Mermaid SVG rendering
and PDF export for prototype-to-prd-pack.

Dependencies:
  - node (provides `npm`)
  - @mermaid-js/mermaid-cli (provides `mmdc`)
  - pandoc
  - weasyprint
EOF
}

find_local_browser() {
  local candidates=(
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"
    "/Applications/Chromium.app/Contents/MacOS/Chromium"
  )
  local candidate
  for candidate in "${candidates[@]}"; do
    if [ -x "$candidate" ]; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done
  for candidate in "$(command -v google-chrome 2>/dev/null || true)" "$(command -v chromium 2>/dev/null || true)" "$(command -v microsoft-edge 2>/dev/null || true)"; do
    if [ -n "$candidate" ] && [ -x "$candidate" ]; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done
  return 1
}

check_only=false
for arg in "$@"; do
  case "$arg" in
    --check-only)
      check_only=true
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "[ERROR] Unknown argument: $arg" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if ! command -v brew >/dev/null 2>&1; then
  echo "[ERROR] Homebrew is required but not installed." >&2
  echo "Install Homebrew from https://brew.sh and rerun this script." >&2
  exit 1
fi

packages=(
  "node"
  "pandoc"
  "weasyprint"
)

missing=()
for package in "${packages[@]}"; do
  if ! brew list --versions "$package" >/dev/null 2>&1; then
    missing+=("$package")
  fi
done

if [ ${#missing[@]} -eq 0 ]; then
  echo "[OK] All required packages are already installed."
elif [ "$check_only" = true ]; then
  echo "[INFO] Missing packages: ${missing[*]}"
  exit 1
else
  echo "[INFO] Installing missing packages: ${missing[*]}"
  HOMEBREW_NO_AUTO_UPDATE=1 brew install "${missing[@]}"
fi

if ! command -v npm >/dev/null 2>&1; then
  echo "[ERROR] npm is required but not available after installing node." >&2
  exit 1
fi

if ! command -v mmdc >/dev/null 2>&1; then
  if [ "$check_only" = true ]; then
    echo "[INFO] Missing npm package: @mermaid-js/mermaid-cli"
    exit 1
  fi
  browser_path="$(find_local_browser || true)"
  npm uninstall -g @mermaid-js/mermaid-cli >/dev/null 2>&1 || true
  if [ -n "$browser_path" ]; then
    echo "[INFO] Installing @mermaid-js/mermaid-cli via npm using local browser: $browser_path"
    PUPPETEER_SKIP_DOWNLOAD=1 PUPPETEER_EXECUTABLE_PATH="$browser_path" npm install -g @mermaid-js/mermaid-cli
  else
    echo "[INFO] Installing @mermaid-js/mermaid-cli via npm with bundled browser download"
    npm install -g @mermaid-js/mermaid-cli
  fi
fi

missing_commands=()
for command_name in mmdc pandoc weasyprint; do
  if ! command -v "$command_name" >/dev/null 2>&1; then
    missing_commands+=("$command_name")
  fi
done

if [ ${#missing_commands[@]} -ne 0 ]; then
  echo "[ERROR] Missing commands after bootstrap: ${missing_commands[*]}" >&2
  exit 1
fi

echo "[OK] Dependency bootstrap complete."
echo "[OK] mmdc: $(command -v mmdc)"
echo "[OK] pandoc: $(command -v pandoc)"
echo "[OK] weasyprint: $(command -v weasyprint)"
