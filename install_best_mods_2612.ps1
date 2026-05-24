$ErrorActionPreference = 'Stop'

$modsDir = Join-Path $env:APPDATA '.minecraft\mods'
New-Item -ItemType Directory -Path $modsDir -Force | Out-Null

$backupDir = Join-Path $env:APPDATA ('.minecraft\mods_backup_' + (Get-Date -Format 'yyyyMMdd_HHmmss'))
New-Item -ItemType Directory -Path $backupDir -Force | Out-Null
Get-ChildItem $modsDir -File -ErrorAction SilentlyContinue | ForEach-Object {
  Copy-Item $_.FullName -Destination (Join-Path $backupDir $_.Name) -Force
}

$gameVersion = '26.1.2'
$loader = 'fabric'
$projects = @(
  'iris',
  'sodium',
  'lithium',
  'ferrite-core',
  'immediatelyfast',
  'entityculling',
  'modmenu',
  'sodium-extra',
  'reeses-sodium-options'
)

$seenVersionIds = New-Object 'System.Collections.Generic.HashSet[string]'
$downloadedNames = New-Object 'System.Collections.Generic.HashSet[string]'

function Get-BestVersionByProject {
  param([string]$Project)
  $url = "https://api.modrinth.com/v2/project/$Project/version?game_versions=%5B%22$gameVersion%22%5D&loaders=%5B%22$loader%22%5D"
  $versions = Invoke-RestMethod -Uri $url -Method Get
  if (-not $versions -or $versions.Count -eq 0) {
    return $null
  }
  return ($versions | Sort-Object { [datetime]$_.date_published } -Descending | Select-Object -First 1)
}

function Get-BestVersionByProjectId {
  param([string]$ProjectId)
  $url = "https://api.modrinth.com/v2/project/$ProjectId/version?game_versions=%5B%22$gameVersion%22%5D&loaders=%5B%22$loader%22%5D"
  $versions = Invoke-RestMethod -Uri $url -Method Get
  if (-not $versions -or $versions.Count -eq 0) {
    return $null
  }
  return ($versions | Sort-Object { [datetime]$_.date_published } -Descending | Select-Object -First 1)
}

function Download-VersionRecursive {
  param($VersionObj)

  if (-not $VersionObj) { return }
  if ($seenVersionIds.Contains($VersionObj.id)) { return }
  [void]$seenVersionIds.Add($VersionObj.id)

  foreach ($dep in ($VersionObj.dependencies | Where-Object { $_.dependency_type -eq 'required' })) {
    $depVersion = $null
    if ($dep.version_id) {
      $depVersion = Invoke-RestMethod -Uri ("https://api.modrinth.com/v2/version/" + $dep.version_id) -Method Get
    } elseif ($dep.project_id) {
      $depVersion = Get-BestVersionByProjectId -ProjectId $dep.project_id
    }
    Download-VersionRecursive -VersionObj $depVersion
  }

  $file = $VersionObj.files | Where-Object { $_.primary -eq $true } | Select-Object -First 1
  if (-not $file) {
    $file = $VersionObj.files | Select-Object -First 1
  }
  if (-not $file) { return }

  $dest = Join-Path $modsDir $file.filename
  if (-not (Test-Path $dest)) {
    Invoke-WebRequest -UseBasicParsing -Uri $file.url -OutFile $dest
  }
  [void]$downloadedNames.Add($file.filename)
}

foreach ($project in $projects) {
  $version = Get-BestVersionByProject -Project $project
  if ($version) {
    Download-VersionRecursive -VersionObj $version
  } else {
    Write-Output "SIN_VERSION_COMPATIBLE:$project"
  }
}

Write-Output "BACKUP:$backupDir"
Write-Output "MODS_FINALES:"
Get-ChildItem $modsDir -File | Sort-Object Name | Select-Object -ExpandProperty Name
