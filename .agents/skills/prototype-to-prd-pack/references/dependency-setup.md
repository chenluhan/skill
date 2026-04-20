# Dependency Setup

Use this guide whenever dependency diagnosis says Mermaid or PDF export is limited or blocked.

## macOS

Recommended direct path:

```bash
bash scripts/bootstrap_dependencies.sh
```

This script will:

- install `node`, `pandoc`, and `weasyprint` with Homebrew
- install `@mermaid-js/mermaid-cli` with npm
- reuse local Chrome / Edge when available to avoid a long Puppeteer browser download
- verify `mmdc`, `pandoc`, and `weasyprint`

If the user only wants a quick verification first:

```bash
bash scripts/bootstrap_dependencies.sh --check-only
```

## Windows

Recommended direct path:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\bootstrap_dependencies.ps1
```

This script will:

- install Node.js LTS with `winget` when needed
- install Pandoc with `winget` when needed
- install `@mermaid-js/mermaid-cli` with npm
- reuse local Chrome / Edge when available to avoid a long Puppeteer browser download
- check whether a supported PDF engine is already available

Important:

- The Windows script can fully bootstrap Mermaid and Pandoc.
- PDF export may still require one more user-visible step, because Windows PDF engines are not all equally scriptable.

## Windows PDF Engine Options

### Option A: MiKTeX

Recommended when the team wants a Pandoc-native Windows PDF path.

What to verify after installation:

```powershell
pdflatex --version
```

Reference:

- Pandoc Windows install docs: [pandoc.org/installing.html](https://pandoc.org/installing.html)

### Option B: WeasyPrint Native or WSL

Recommended when the team already uses WeasyPrint elsewhere or prefers a browser/CSS-oriented PDF path.

What to verify after installation:

```powershell
weasyprint --version
```

References:

- WeasyPrint install docs: [doc.courtbouillon.org/weasyprint/stable/first_steps.html](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html)

## Mermaid CLI Reference

Official package:

- npm: [@mermaid-js/mermaid-cli](https://www.npmjs.com/package/@mermaid-js/mermaid-cli)

What to verify:

```bash
mmdc --version
```

If Mermaid CLI install is slow, prefer the local-browser path first instead of waiting for a bundled Chromium download.

## Diagnosis Output Rule

If dependencies are blocked or limited, the agent should always report:

- current platform
- direct bootstrap command for that platform
- whether the bootstrap can finish everything automatically
- if not, which official reference the user should follow next
