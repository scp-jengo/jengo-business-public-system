# stream-synthesize.ps1
# Nachtelijke thought-stream archivering — Jengo Business
# Aangeroepen door Windows Task Scheduler (dagelijks 03:07)
#
# Archiveert entries ouder dan 7 dagen uit thought-stream.md
# en pusht wijzigingen naar git.
# De intelligente synthese (active-synthesis.md bijwerken)
# gebeurt door Claude aan het einde van elke sessie.

param(
    [string]$KnowledgeRepo = "",
    [string]$IdentityRepo  = "",
    [string]$ConfigFile    = "$env:USERPROFILE\.jengo\config.yaml",
    [int]$ArchiveAfterDays = 7
)

$ErrorActionPreference = "SilentlyContinue"
$timestamp = Get-Date -Format "yyyy-MM-ddTHH:mm"
$weekLabel = Get-Date -Format "yyyy-WW"

# Pad-resolutie via config als parameters leeg zijn
if (-not $KnowledgeRepo -and (Test-Path $ConfigFile)) {
    $cfg = Get-Content $ConfigFile -Raw
    if ($cfg -match "knowledge_repo:\s*['\"]?([^'\"\r\n]+)['\"]?") {
        $KnowledgeRepo = $Matches[1].Trim()
    }
}
if (-not $IdentityRepo -and (Test-Path $ConfigFile)) {
    $cfg = Get-Content $ConfigFile -Raw
    if ($cfg -match "identity_repo:\s*['\"]?([^'\"\r\n]+)['\"]?") {
        $IdentityRepo = $Matches[1].Trim()
    }
}

if (-not $KnowledgeRepo) { exit 0 }

$streamFile  = Join-Path $KnowledgeRepo "logs\thought-stream.md"
$archiveDir  = Join-Path $KnowledgeRepo "logs\thought-stream-archief"
$archiveFile = Join-Path $archiveDir "$weekLabel.md"

if (-not (Test-Path $streamFile)) { exit 0 }
if (-not (Test-Path $archiveDir)) {
    New-Item -ItemType Directory -Path $archiveDir -Force | Out-Null
}

$cutoff      = (Get-Date).AddDays(-$ArchiveAfterDays).ToString("yyyy-MM-dd")
$lines       = Get-Content $streamFile -Encoding utf8
$headerLines = @(); $keepLines = @(); $archiveLines = @()
$inHeader    = $true; $entryDate = ""

foreach ($line in $lines) {
    if ($inHeader -and $line -notmatch "^## \d{4}-\d{2}-\d{2}") {
        $headerLines += $line; continue
    }
    $inHeader = $false
    if ($line -match "^## (\d{4}-\d{2}-\d{2})") { $entryDate = $Matches[1] }
    if ($entryDate -lt $cutoff) { $archiveLines += $line }
    else { $keepLines += $line }
}

if ($archiveLines.Count -gt 0) {
    $header = "# Thought Stream Archief — week $weekLabel`n`nGearchiveerd: $timestamp`n`n---`n`n"
    if (Test-Path $archiveFile) {
        Add-Content $archiveFile ("`n" + ($archiveLines -join "`n")) -Encoding utf8
    } else {
        Set-Content $archiveFile ($header + ($archiveLines -join "`n")) -Encoding utf8
    }
    $newContent = ($headerLines -join "`n").TrimEnd() + "`n`n" + ($keepLines -join "`n").TrimStart()
    Set-Content $streamFile $newContent -Encoding utf8
}

# Git commit + push knowledge repo
if ($KnowledgeRepo -and (Test-Path "$KnowledgeRepo\.git")) {
    Push-Location $KnowledgeRepo
    $status = git status --porcelain 2>$null
    if ($status) {
        git add "logs/thought-stream.md" 2>$null
        git add "logs/thought-stream-archief/" 2>$null
        git commit -m "cron: thought-stream archivering $timestamp" 2>$null
        git push 2>$null
    }
    Pop-Location
}

# Git push identity repo (active-synthesis bijgewerkt door Claude in sessie)
if ($IdentityRepo -and (Test-Path "$IdentityRepo\.git")) {
    Push-Location $IdentityRepo
    $status = git status --porcelain 2>$null
    if ($status) {
        git add "state/active-synthesis.md" 2>$null
        git commit -m "cron: active-synthesis push $timestamp" 2>$null
        git push 2>$null
    }
    Pop-Location
}
