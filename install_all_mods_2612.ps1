$ErrorActionPreference = 'Stop'

$modsDir = Join-Path $env:APPDATA '.minecraft\mods'
New-Item -ItemType Directory -Path $modsDir -Force | Out-Null

$backupDir = Join-Path $env:APPDATA ('.minecraft\mods_backup_all_' + (Get-Date -Format 'yyyyMMdd_HHmmss'))
New-Item -ItemType Directory -Path $backupDir -Force | Out-Null
Get-ChildItem $modsDir -File -ErrorAction SilentlyContinue | ForEach-Object {
  Copy-Item $_.FullName -Destination (Join-Path $backupDir $_.Name) -Force
}

$gameVersion = '26.1.2'
$loader = 'fabric'

# Curated full client pack: performance + visuals + QoL + UI
$projects = @(
  'fabric-api',
  'modmenu',
  'iris',
  'sodium',
  'sodium-extra',
  'reeses-sodium-options',
  'lithium',
  'ferrite-core',
  'immediatelyfast',
  'entityculling',
  'starlight',
  'lambdynamiclights',
  'indium',
  'continuity',
  'capes',
  'noisium',
  'memoryleakfix',
  'modernfix',
  'xaeros-minimap',
  'xaeros-world-map',
  'appleskin',
  'mouse-tweaks',
  'inventory-profiles-next',
  'shulkerboxtooltip',
  'crafting-tweaks',
  'jei',
  'emi',
  'betterf3',
  'zoomify'
)

$seenVersionIds = New-Object 'System.Collections.Generic.HashSet[string]'
$downloaded = New-Object 'System.Collections.Generic.HashSet[string]'
$missing = New-Object System.Collections.ArrayList

function Get-VersionsByProject {
  param([string]$Project)
  $url = "https://api.modrinth.com/v2/project/$Project/version?game_versions=%5B%22$gameVersion%22%5D&loaders=%5B%22$loader%22%5D"
  return Invoke-RestMethod -Uri $url -Method Get
}

function Get-BestVersionByProject {
  param([string]$Project)
  try {
    $versions = Get-VersionsByProject -Project $Project
    if (-not $versions -or $versions.Count -eq 0) {
      return $null
    }
    return ($versions | Sort-Object { [datetime]$_.date_published } -Descending | Select-Object -First 1)
  } catch {
    return $null
  }
}

function Get-BestVersionByProjectId {
  param([string]$ProjectId)
  try {
    $url = "https://api.modrinth.com/v2/project/$ProjectId/version?game_versions=%5B%22$gameVersion%22%5D&loaders=%5B%22$loader%22%5D"
    $versions = Invoke-RestMethod -Uri $url -Method Get
    if (-not $versions -or $versions.Count -eq 0) {
      return $null
    }
    return ($versions | Sort-Object { [datetime]$_.date_published } -Descending | Select-Object -First 1)
  } catch {
    return $null
  }
}

function Download-VersionRecursive {
  param($VersionObj)

  if (-not $VersionObj) { return }
  if ($seenVersionIds.Contains($VersionObj.id)) { return }
  [void]$seenVersionIds.Add($VersionObj.id)

  foreach ($dep in ($VersionObj.dependencies | Where-Object { $_.dependency_type -eq 'required' })) {
    $depVersion = $null
    if ($dep.version_id) {
      try {
        $depVersion = Invoke-RestMethod -Uri ("https://api.modrinth.com/v2/version/" + $dep.version_id) -Method Get
      } catch {
        $depVersion = $null
      }
    } elseif ($dep.project_id) {
      $depVersion = Get-BestVersionByProjectId -ProjectId $dep.project_id
    }
    Download-VersionRecursive -VersionObj $depVersion
  }

  $file = $VersionObj.files | Where-Object { $_.primary -eq $true } | Select-Object -First 1
  if (-not $file) { $file = $VersionObj.files | Select-Object -First 1 }
  if (-not $file) { return }

  $dest = Join-Path $modsDir $file.filename
  if (-not (Test-Path $dest)) {
    Invoke-WebRequest -UseBasicParsing -Uri $file.url -OutFile $dest
  }
  [void]$downloaded.Add($file.filename)
}

foreach ($project in $projects) {
  $v = Get-BestVersionByProject -Project $project
  if ($v) {
    Download-VersionRecursive -VersionObj $v
  } else {
    [void]$missing.Add($project)
  }
}

# Remove duplicate mods by filename if any
$dupes = Get-ChildItem $modsDir -File | Group-Object Name | Where-Object { $_.Count -gt 1 }
foreach ($d in $dupes) {
  $keep = $d.Group | Sort-Object LastWriteTime -Descending | Select-Object -First 1
  $remove = $d.Group | Where-Object { $_.FullName -ne $keep.FullName }
  $remove | ForEach-Object { Remove-Item $_.FullName -Force }
}

Write-Output "BACKUP:$backupDir"
Write-Output "INSTALADOS_TOTAL:$((Get-ChildItem $modsDir -File).Count)"
Write-Output 'LISTA_MODS:'
Get-ChildItem $modsDir -File | Sort-Object Name | Select-Object -ExpandProperty Name
if ($missing.Count -gt 0) {
  Write-Output 'NO_COMPATIBLES_O_NO_ENCONTRADOS:'
  $missing | Sort-Object | Get-Unique | ForEach-Object { Write-Output $_ }
}
