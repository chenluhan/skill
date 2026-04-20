param(
    [switch]$CheckOnly
)

$ErrorActionPreference = "Stop"

function Test-Command($Name) {
    return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

function Install-WingetPackage($Id) {
    Write-Host "[INFO] Installing winget package: $Id"
    winget install --exact --id $Id --source winget --accept-package-agreements --accept-source-agreements
}

function Find-LocalBrowser() {
    $candidates = @(
        "$Env:ProgramFiles\Google\Chrome\Application\chrome.exe",
        "$Env:ProgramFiles(x86)\Google\Chrome\Application\chrome.exe",
        "$Env:LocalAppData\Google\Chrome\Application\chrome.exe",
        "$Env:ProgramFiles\Microsoft\Edge\Application\msedge.exe",
        "$Env:ProgramFiles(x86)\Microsoft\Edge\Application\msedge.exe",
        "$Env:LocalAppData\Microsoft\Edge\Application\msedge.exe"
    )
    foreach ($candidate in $candidates) {
        if ($candidate -and (Test-Path $candidate)) {
            return $candidate
        }
    }
    return $null
}

if (-not (Test-Command "winget")) {
    Write-Error "winget is required on Windows. Install App Installer from Microsoft Store and rerun this script."
}

$missingWinget = @()
if (-not (Test-Command "node")) { $missingWinget += "OpenJS.NodeJS.LTS" }
if (-not (Test-Command "pandoc")) { $missingWinget += "JohnMacFarlane.Pandoc" }

if ($missingWinget.Count -gt 0) {
    if ($CheckOnly) {
        Write-Host "[INFO] Missing winget packages: $($missingWinget -join ' ')"
        exit 1
    }
    foreach ($packageId in $missingWinget) {
        Install-WingetPackage $packageId
    }
}

if (-not (Test-Command "npm")) {
    Write-Error "npm is required but is not available after installing Node.js."
}

if (-not (Test-Command "mmdc")) {
    if ($CheckOnly) {
        Write-Host "[INFO] Missing npm package: @mermaid-js/mermaid-cli"
        exit 1
    }
    $browserPath = Find-LocalBrowser
    npm uninstall -g @mermaid-js/mermaid-cli | Out-Null
    if ($browserPath) {
        Write-Host "[INFO] Installing @mermaid-js/mermaid-cli via npm using local browser: $browserPath"
        $Env:PUPPETEER_SKIP_DOWNLOAD = "1"
        $Env:PUPPETEER_EXECUTABLE_PATH = $browserPath
    } else {
        Write-Host "[INFO] Installing @mermaid-js/mermaid-cli via npm with bundled browser download"
    }
    npm install -g @mermaid-js/mermaid-cli
}

$pdfEngineReady = (Test-Command "pdflatex") -or (Test-Command "wkhtmltopdf") -or (Test-Command "weasyprint")
if (-not $pdfEngineReady) {
    if ($CheckOnly) {
        Write-Host "[INFO] Missing Windows PDF engine. See references/dependency-setup.md for MiKTeX or official WeasyPrint/WSL paths."
        exit 1
    }
    Write-Warning "Pandoc is installed, but no supported PDF engine was found."
    Write-Warning "Recommended next step on Windows: install MiKTeX for pdflatex, or follow the official WeasyPrint/WSL path in references/dependency-setup.md."
}

$missingCommands = @()
foreach ($commandName in @("pandoc", "mmdc")) {
    if (-not (Test-Command $commandName)) {
        $missingCommands += $commandName
    }
}

if ($missingCommands.Count -gt 0) {
    Write-Error "Missing commands after bootstrap: $($missingCommands -join ' ')"
}

Write-Host "[OK] Dependency bootstrap complete for Windows."
Write-Host "[OK] pandoc: $((Get-Command pandoc).Source)"
Write-Host "[OK] mmdc: $((Get-Command mmdc).Source)"
if ($pdfEngineReady) {
    if (Test-Command "pdflatex") {
        Write-Host "[OK] PDF engine: $((Get-Command pdflatex).Source)"
    } elseif (Test-Command "wkhtmltopdf") {
        Write-Host "[OK] PDF engine: $((Get-Command wkhtmltopdf).Source)"
    } else {
        Write-Host "[OK] PDF engine: $((Get-Command weasyprint).Source)"
    }
} else {
    Write-Host "[INFO] PDF engine still needs setup. See references/dependency-setup.md."
}
