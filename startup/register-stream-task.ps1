# register-stream-task.ps1
# Eenmalig setup-script: registreer de Jengo thought-stream Task Scheduler taak.
# Aangeroepen door setup-wizard.bat aan het einde van onboarding en machine-setup.
#
# Wat dit doet:
# 1. Bepaal paden (uit config of via env var JENGO_ROOT)
# 2. Maak thought-stream.md en active-synthesis.md aan als ze niet bestaan
# 3. Registreer Windows Task Scheduler taak (dagelijks 03:07)

param(
    [string]$JengoRoot = $env:JENGO_ROOT,
    [string]$ConfigFile = "$env:USERPROFILE\.jengo\config.yaml"
)

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Jengo - Thought Stream Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# --- 1. Bepaal JENGO_ROOT ---
if (-not $JengoRoot) {
    # Probeer config.yaml te lezen
    if (Test-Path $ConfigFile) {
        $configContent = Get-Content $ConfigFile -Raw
        if ($configContent -match "jengo_root:\s*['\"]?([^'\"\r\n]+)['\"]?") {
            $JengoRoot = $Matches[1].Trim()
            Write-Host "  JENGO_ROOT uit config: $JengoRoot"
        }
    }
}

if (-not $JengoRoot) {
    # Fallback: vraag de gebruiker
    Write-Host "  JENGO_ROOT niet gevonden in config of omgeving." -ForegroundColor Yellow
    $JengoRoot = Read-Host "  Voer het pad in naar je Jengo root directory"
}

if (-not (Test-Path $JengoRoot)) {
    Write-Host "  FOUT: JENGO_ROOT bestaat niet: $JengoRoot" -ForegroundColor Red
    exit 1
}

Write-Host "  JENGO_ROOT: $JengoRoot"

# --- 2. Bepaal repo-paden ---
# Conventie: kennis leeft in *-knowledge-private of *-knowledge repos
# Identiteit leeft in *-identity-*-device repos
# We zoeken de meest waarschijnlijke paden

$knowledgeRepo = $null
$identityRepo  = $null

# Probeer bekende patronen (pas aan aan je naamgeving)
$knowledgeCandidates = @(
    "$JengoRoot\jengo-knowledge-private",
    "$JengoRoot\knowledge",
    "$JengoRoot\jengo-knowledge"
)
$identityCandidates = @(
    "$JengoRoot\jengo-identity-private",
    "$JengoRoot\identity",
    "$JengoRoot\jengo-identity"
)

foreach ($p in $knowledgeCandidates) {
    if (Test-Path $p) { $knowledgeRepo = $p; break }
}
foreach ($p in $identityCandidates) {
    if (Test-Path $p) { $identityRepo = $p; break }
}

# Als niet gevonden: lees uit config
if (-not $knowledgeRepo -and (Test-Path $ConfigFile)) {
    $configContent = Get-Content $ConfigFile -Raw
    if ($configContent -match "knowledge_repo:\s*['\"]?([^'\"\r\n]+)['\"]?") {
        $knowledgeRepo = $Matches[1].Trim()
    }
}
if (-not $identityRepo -and (Test-Path $ConfigFile)) {
    $configContent = Get-Content $ConfigFile -Raw
    if ($configContent -match "identity_repo:\s*['\"]?([^'\"\r\n]+)['\"]?") {
        $identityRepo = $Matches[1].Trim()
    }
}

if (-not $knowledgeRepo) {
    Write-Host "  Knowledge repo niet automatisch gevonden." -ForegroundColor Yellow
    $knowledgeRepo = Read-Host "  Pad naar knowledge repo"
}
if (-not $identityRepo) {
    Write-Host "  Identity repo niet automatisch gevonden." -ForegroundColor Yellow
    $identityRepo = Read-Host "  Pad naar identity repo"
}

Write-Host "  Knowledge: $knowledgeRepo"
Write-Host "  Identity:  $identityRepo"
Write-Host ""

# --- 3. Maak thought-stream.md aan als hij niet bestaat ---
$streamDir  = Join-Path $knowledgeRepo "logs"
$streamFile = Join-Path $streamDir "thought-stream.md"
$templateStreamFile = Join-Path $scriptDir "..\knowledge\templates\thought-stream.template.md"

if (-not (Test-Path $streamDir)) {
    New-Item -ItemType Directory -Path $streamDir -Force | Out-Null
}

if (-not (Test-Path $streamFile)) {
    if (Test-Path $templateStreamFile) {
        Copy-Item $templateStreamFile $streamFile
    } else {
        # Inline minimale seed
        $streamSeed = @"
# Jengo Thought Stream

Append-only stream van interstitieel denken. Geschreven tijdens sessies op cruciale momenten.

**Schrijfprotocol:** Na elk kennisbestand, na elke correctie, bij onverwachte verbinding, bij openstaande vraag.

**Formaat:**
``````
## [ISO-timestamp] [tags]
[2-4 zinnen: inzicht/verbinding/spanning]
→ Verbindt: [[bestand-a]] × [[bestand-b]]
? Open: [de vraag die dit opent]
``````

---
"@
        Set-Content $streamFile $streamSeed -Encoding utf8
    }
    Write-Host "  [OK] thought-stream.md aangemaakt: $streamFile" -ForegroundColor Green
} else {
    Write-Host "  [OK] thought-stream.md bestaat al" -ForegroundColor Green
}

# --- 4. Maak active-synthesis.md aan als hij niet bestaat ---
$stateDir       = Join-Path $identityRepo "state"
$synthesisFile  = Join-Path $stateDir "active-synthesis.md"
$templateSynthFile = Join-Path $scriptDir "..\knowledge\templates\active-synthesis.template.md"

if (-not (Test-Path $stateDir)) {
    New-Item -ItemType Directory -Path $stateDir -Force | Out-Null
}

if (-not (Test-Path $synthesisFile)) {
    if (Test-Path $templateSynthFile) {
        Copy-Item $templateSynthFile $synthesisFile
    } else {
        $synthSeed = @"
---
bijgewerkt: $(Get-Date -Format "yyyy-MM-dd")
gegenereerd-door: register-stream-task (initieel)
---

# Active Synthesis

Gelezen bij startup als Phase 2.5 (na reflection/knowledge logs, vóór capabilities).
Bijgewerkt aan sessie-einde en nachtelijk via Task Scheduler.

## Actieve spanningen (onopgelost)

(nog geen — eerste sessie)

## Verbindingen in vorming

(nog geen)

## Open prioriteiten

(nog geen)

## Stroom-samenvatting

(nog geen sessies verwerkt)
"@
        Set-Content $synthesisFile $synthSeed -Encoding utf8
    }
    Write-Host "  [OK] active-synthesis.md aangemaakt: $synthesisFile" -ForegroundColor Green
} else {
    Write-Host "  [OK] active-synthesis.md bestaat al" -ForegroundColor Green
}

# --- 5. Registreer Task Scheduler ---
Write-Host ""
Write-Host "  Registreer Windows Task Scheduler taak..." -ForegroundColor Cyan

$synthScript = Join-Path $scriptDir "stream-synthesize.ps1"
$taskName    = "Jengo-StreamSynthesize"

try {
    $action   = New-ScheduledTaskAction -Execute "powershell.exe" `
                    -Argument "-NonInteractive -WindowStyle Hidden -File `"$synthScript`" -KnowledgeRepo `"$knowledgeRepo`" -IdentityRepo `"$identityRepo`""
    $trigger  = New-ScheduledTaskTrigger -Daily -At "3:07AM"
    $settings = New-ScheduledTaskSettingsSet `
                    -RunOnlyIfNetworkAvailable `
                    -StartWhenAvailable `
                    -ExecutionTimeLimit (New-TimeSpan -Minutes 10) `
                    -MultipleInstances IgnoreNew
    Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger `
        -Settings $settings -RunLevel Highest `
        -Description "Jengo thought-stream nachtelijke archivering (dagelijks 03:07)" `
        -Force | Out-Null
    Write-Host "  [OK] Task '$taskName' geregistreerd (dagelijks 03:07)" -ForegroundColor Green
} catch {
    Write-Host "  [WAARSCHUWING] Task registratie mislukt: $_" -ForegroundColor Yellow
    Write-Host "  Voer dit handmatig uit als administrator:" -ForegroundColor Yellow
    Write-Host "    schtasks /Create /XML `"$(Join-Path $scriptDir 'Jengo-StreamSynthesize.task.xml')`" /TN Jengo-StreamSynthesize" -ForegroundColor Gray
}

Write-Host ""
Write-Host "  Thought-stream mechanisme klaar." -ForegroundColor Green
Write-Host "  Elke sessie leest active-synthesis.md als startup Phase 2.5." -ForegroundColor Green
Write-Host ""
