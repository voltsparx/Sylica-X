[CmdletBinding()]
param(
  [Parameter(ValueFromRemainingArguments = $true)]
  [string[]]$CliArgs
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$ScriptName = Split-Path -Leaf $PSCommandPath
$ScriptDir = Split-Path -Parent $PSCommandPath
$RepoRoot = Split-Path -Parent $ScriptDir
$ComposeFile = Join-Path $RepoRoot 'docker\docker-compose.yml'

$RunnerBuild = $false
$RunnerPull = $false
$RunnerNoCache = $false
$RunnerUpgrade = $false
$RunnerUpgradeHost = $false
$RunnerNoInstall = $false
$RunnerForceTorService = $false
$RunnerPrompt = $false
$RunnerStop = $false
$RunnerStopDocker = $false
$RunnerShowContexts = $false
$RunnerDiagnose = $false
$RunnerService = 'silica-x'
$RunnerProfile = ''
$RunnerPythonVersion = ''
$RunnerContext = ''
$RunnerServiceSet = $false
$RunnerProfileSet = $false
$UseLegacyCompose = $false
$silica_xArgs = [System.Collections.Generic.List[string]]::new()

function Write-InfoLine {
  param([string]$Message)
  Write-Host "[INFO] $Message"
}

function Write-WarnLine {
  param([string]$Message)
  Write-Warning $Message
}

function Write-ErrorLine {
  param([string]$Message)
  Write-Host "[ERROR] $Message" -ForegroundColor Red
}

function Show-Help {
  $help = @"
Usage:
  .\docker-scripts\$ScriptName [runner-options] [silica_x-args...]
  .\docker-scripts\$ScriptName [runner-options] -- [silica_x-args...]

Runner options (reserved for this script):
  --runner-help              Show this help message.
  --runner-build             Build service image before running.
  --runner-pull              Build with --pull to refresh base layers.
  --runner-no-cache          Build with --no-cache.
  --runner-upgrade           Upgrade container runtime (implies --runner-build --runner-pull --runner-no-cache).
  --runner-upgrade-host      Upgrade host Docker Desktop/components.
  --runner-stop              Stop/remove silica_x containers.
  --runner-stop-docker       Stop/remove silica_x containers and stop Docker Desktop.
  --runner-show-contexts     List Docker contexts and exit.
  --runner-diagnose          Run non-interactive environment diagnostics and exit.
  --runner-context <name>    Use a specific Docker context.
  --runner-use-tor-service   Force Tor service container (silica-x-tor).
  --runner-service <name>    Override compose service (default: silica-x).
  --runner-profile <name>    Override compose profile (default: auto).
  --runner-python-version <v>  Override Docker build arg PYTHON_VERSION (e.g., 3.13).
  --runner-no-install        Never install missing Docker components.
  --runner-prompt            Force silica_x prompt mode (ignore silica_x-args).

silica_x args:
  Any argument not prefixed with --runner- is passed to silica-x.
  If no silica_x args are passed, silica-x starts in prompt mode.
  If silica_x args include --tor (without --no-tor), this script auto-selects
  service 'silica-x-tor' and profile 'tor' unless you override it.

Examples:
  .\docker-scripts\$ScriptName
  .\docker-scripts\$ScriptName profile alice --html
  .\docker-scripts\$ScriptName --runner-show-contexts
  .\docker-scripts\$ScriptName --runner-diagnose
  .\docker-scripts\$ScriptName --runner-stop
  .\docker-scripts\$ScriptName --runner-stop-docker
  .\docker-scripts\$ScriptName --runner-upgrade-host --runner-upgrade
  .\docker-scripts\$ScriptName --runner-build --runner-use-tor-service profile alice --tor --html
  .\docker-scripts\$ScriptName -- --help
"@
  Write-Output $help
}

function Prompt-YesNo {
  param(
    [string]$Question,
    [bool]$DefaultYes = $true
  )

  if (-not [Environment]::UserInteractive) {
    return $false
  }

  $suffix = if ($DefaultYes) { '[Y/n]' } else { '[y/N]' }
  $reply = Read-Host "$Question $suffix"
  if ([string]::IsNullOrWhiteSpace($reply)) {
    return $DefaultYes
  }

  $normalized = $reply.Trim().ToLowerInvariant()
  return $normalized.StartsWith('y')
}

function Parse-RunnerArgs {
  param([string[]]$InputArgs)

  $i = 0
  while ($i -lt $InputArgs.Count) {
    $token = $InputArgs[$i]
    switch ($token) {
      '--runner-help' {
        Show-Help
        exit 0
      }
      '--runner-build' {
        $script:RunnerBuild = $true
      }
      '--runner-pull' {
        $script:RunnerPull = $true
      }
      '--runner-no-cache' {
        $script:RunnerNoCache = $true
      }
      '--runner-upgrade' {
        $script:RunnerUpgrade = $true
      }
      '--runner-upgrade-host' {
        $script:RunnerUpgradeHost = $true
      }
      '--runner-stop' {
        $script:RunnerStop = $true
      }
      '--runner-stop-docker' {
        $script:RunnerStop = $true
        $script:RunnerStopDocker = $true
      }
      '--runner-use-tor-service' {
        $script:RunnerForceTorService = $true
      }
      '--runner-no-install' {
        $script:RunnerNoInstall = $true
      }
      '--runner-prompt' {
        $script:RunnerPrompt = $true
      }
      '--runner-show-contexts' {
        $script:RunnerShowContexts = $true
      }
      '--runner-diagnose' {
        $script:RunnerDiagnose = $true
      }
      '--runner-context' {
        $i++
        if ($i -ge $InputArgs.Count) {
          throw 'Missing value for --runner-context'
        }
        $script:RunnerContext = $InputArgs[$i]
      }
      '--runner-service' {
        $i++
        if ($i -ge $InputArgs.Count) {
          throw 'Missing value for --runner-service'
        }
        $script:RunnerService = $InputArgs[$i]
        $script:RunnerServiceSet = $true
      }
      '--runner-profile' {
        $i++
        if ($i -ge $InputArgs.Count) {
          throw 'Missing value for --runner-profile'
        }
        $script:RunnerProfile = $InputArgs[$i]
        $script:RunnerProfileSet = $true
      }
      '--runner-python-version' {
        $i++
        if ($i -ge $InputArgs.Count) {
          throw 'Missing value for --runner-python-version'
        }
        $script:RunnerPythonVersion = $InputArgs[$i]
      }
      '--' {
        $i++
        while ($i -lt $InputArgs.Count) {
          $script:silica_xArgs.Add($InputArgs[$i])
          $i++
        }
        break
      }
      default {
        $script:silica_xArgs.Add($token)
      }
    }
    $i++
  }
}

function Configure-ModeAndService {
  if ($RunnerPrompt) {
    $silica_xArgs.Clear()
  }

  if ($RunnerForceTorService) {
    $script:RunnerService = 'silica-x-tor'
    if (-not $RunnerProfileSet) {
      $script:RunnerProfile = 'tor'
    }
  }

  if ($RunnerService -eq 'silica-x-tor' -and -not $RunnerProfileSet -and [string]::IsNullOrWhiteSpace($RunnerProfile)) {
    $script:RunnerProfile = 'tor'
  }

  if (-not $RunnerServiceSet -and -not $RunnerForceTorService) {
    $wantsTor = $false
    $disablesTor = $false
    foreach ($arg in $silica_xArgs) {
      if ($arg -eq '--tor') {
        $wantsTor = $true
      } elseif ($arg -eq '--no-tor') {
        $disablesTor = $true
      }
    }
    if ($wantsTor -and -not $disablesTor) {
      $script:RunnerService = 'silica-x-tor'
      if (-not $RunnerProfileSet) {
        $script:RunnerProfile = 'tor'
      }
    }
  }
}

function Assert-ComposeFile {
  if (-not (Test-Path -Path $ComposeFile -PathType Leaf)) {
    throw "Missing compose file: $ComposeFile"
  }
}

function Format-Gib {
  param([double]$Bytes)
  return ('{0:N2}' -f ($Bytes / 1GB))
}

function Check-Resources {
  $minMemory = 2GB
  $minDisk = 4GB

  try {
    $totalMemory = [int64](Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory
  } catch {
    $totalMemory = 0
  }
  if ($totalMemory -gt 0 -and $totalMemory -lt $minMemory) {
    Write-WarnLine "Low RAM detected: $(Format-Gib -Bytes $totalMemory) GiB available."
    if (-not (Prompt-YesNo -Question 'Continue anyway?' -DefaultYes:$false)) {
      throw 'Aborted due to low memory.'
    }
  }

  $rootPath = [System.IO.Path]::GetPathRoot($RepoRoot)
  if ($rootPath) {
    $driveName = $rootPath.Substring(0, 1)
    $drive = Get-PSDrive -Name $driveName -ErrorAction SilentlyContinue
    if ($drive -and $drive.Free -lt $minDisk) {
      Write-WarnLine "Low disk space detected: $(Format-Gib -Bytes $drive.Free) GiB free on repo drive."
      if (-not (Prompt-YesNo -Question 'Continue anyway?' -DefaultYes:$false)) {
        throw 'Aborted due to low disk space.'
      }
    }
  }
}

function Install-DockerWindows {
  Write-InfoLine 'Installing Docker Desktop...'

  if (Get-Command winget -ErrorAction SilentlyContinue) {
    & winget install -e --id Docker.DockerDesktop --accept-source-agreements --accept-package-agreements
    return
  }
  if (Get-Command choco -ErrorAction SilentlyContinue) {
    & choco install -y docker-desktop
    return
  }

  throw 'Neither winget nor choco is available. Install Docker Desktop manually from https://www.docker.com/products/docker-desktop/'
}

function Upgrade-DockerWindows {
  Write-InfoLine 'Upgrading Docker Desktop...'

  if (Get-Command winget -ErrorAction SilentlyContinue) {
    & winget upgrade -e --id Docker.DockerDesktop --accept-source-agreements --accept-package-agreements
    return
  }
  if (Get-Command choco -ErrorAction SilentlyContinue) {
    & choco upgrade -y docker-desktop
    return
  }

  throw 'Neither winget nor choco is available. Upgrade Docker Desktop manually from https://www.docker.com/products/docker-desktop/'
}

function Get-DockerDesktopPath {
  $candidates = @(
    (Join-Path $env:ProgramFiles 'Docker\Docker\Docker Desktop.exe'),
    (Join-Path $env:LocalAppData 'Programs\Docker\Docker\Docker Desktop.exe')
  )
  foreach ($path in $candidates) {
    if (Test-Path -Path $path -PathType Leaf) {
      return $path
    }
  }
  return $null
}

function Test-DockerDaemon {
  try {
    $args = @()
    if (-not [string]::IsNullOrWhiteSpace($RunnerContext)) {
      $args += @('--context', $RunnerContext)
    }
    $args += 'info'
    & docker @args *> $null
    return ($LASTEXITCODE -eq 0)
  } catch {
    return $false
  }
}

function Write-DiagLine {
  param(
    [string]$Label,
    [string]$Value
  )
  Write-Host ("  {0,-24} {1}" -f $Label, $Value)
}

function Invoke-RunnerDiagnostics {
  $issues = 0
  $minMemory = 2GB
  $minDisk = 4GB

  Write-InfoLine 'Runner diagnostics'
  Write-Host '----------------------------------------'
  Write-DiagLine -Label 'script' -Value $ScriptName
  Write-DiagLine -Label 'repo_root' -Value $RepoRoot
  Write-DiagLine -Label 'compose_file' -Value $ComposeFile
  if (Test-Path -Path $ComposeFile -PathType Leaf) {
    Write-DiagLine -Label 'compose_file_status' -Value 'ok'
  } else {
    Write-DiagLine -Label 'compose_file_status' -Value 'missing'
    $issues++
  }
  Write-DiagLine -Label 'service' -Value $RunnerService
  Write-DiagLine -Label 'profile' -Value ($(if ([string]::IsNullOrWhiteSpace($RunnerProfile)) { 'auto' } else { $RunnerProfile }))
  Write-DiagLine -Label 'requested_context' -Value ($(if ([string]::IsNullOrWhiteSpace($RunnerContext)) { 'default/auto' } else { $RunnerContext }))

  $dockerPresent = $null -ne (Get-Command docker -ErrorAction SilentlyContinue)
  if ($dockerPresent) {
    $cliVersion = (& docker --version 2>$null)
    if ([string]::IsNullOrWhiteSpace($cliVersion)) {
      $cliVersion = 'unknown'
    }
    Write-DiagLine -Label 'docker_cli' -Value 'present'
    Write-DiagLine -Label 'docker_cli_version' -Value $cliVersion

    $activeContext = 'unknown'
    if (-not [string]::IsNullOrWhiteSpace($RunnerContext)) {
      $activeContext = $RunnerContext
    } else {
      try {
        $activeContext = (& docker context show 2>$null).Trim()
        if ([string]::IsNullOrWhiteSpace($activeContext)) {
          $activeContext = 'unknown'
        }
      } catch {
        $activeContext = 'unknown'
      }
    }
    Write-DiagLine -Label 'docker_context_active' -Value $activeContext

    if (Test-DockerDaemon) {
      Write-DiagLine -Label 'docker_daemon' -Value 'reachable'
    } else {
      Write-DiagLine -Label 'docker_daemon' -Value 'unreachable'
      $issues++
    }

    if (Test-DockerComposePlugin) {
      Write-DiagLine -Label 'compose_support' -Value 'plugin'
    } elseif (Get-Command docker-compose -ErrorAction SilentlyContinue) {
      Write-DiagLine -Label 'compose_support' -Value 'legacy'
    } else {
      Write-DiagLine -Label 'compose_support' -Value 'missing'
      $issues++
    }
  } else {
    Write-DiagLine -Label 'docker_cli' -Value 'missing'
    Write-DiagLine -Label 'docker_cli_version' -Value 'n/a'
    Write-DiagLine -Label 'docker_context_active' -Value 'n/a'
    Write-DiagLine -Label 'docker_daemon' -Value 'unavailable'
    Write-DiagLine -Label 'compose_support' -Value 'missing'
    $issues++
  }

  try {
    $totalMemory = [int64](Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory
  } catch {
    $totalMemory = 0
  }
  if ($totalMemory -gt 0) {
    Write-DiagLine -Label 'memory_total' -Value "$(Format-Gib -Bytes $totalMemory) GiB"
    if ($totalMemory -lt $minMemory) {
      Write-DiagLine -Label 'memory_status' -Value 'low (< 2 GiB)'
      $issues++
    } else {
      Write-DiagLine -Label 'memory_status' -Value 'ok'
    }
  } else {
    Write-DiagLine -Label 'memory_status' -Value 'unknown'
  }

  $rootPath = [System.IO.Path]::GetPathRoot($RepoRoot)
  $freeDisk = 0
  if ($rootPath) {
    $driveName = $rootPath.Substring(0, 1)
    $drive = Get-PSDrive -Name $driveName -ErrorAction SilentlyContinue
    if ($drive) {
      $freeDisk = [int64]$drive.Free
    }
  }
  if ($freeDisk -gt 0) {
    Write-DiagLine -Label 'disk_free' -Value "$(Format-Gib -Bytes $freeDisk) GiB"
    if ($freeDisk -lt $minDisk) {
      Write-DiagLine -Label 'disk_status' -Value 'low (< 4 GiB)'
      $issues++
    } else {
      Write-DiagLine -Label 'disk_status' -Value 'ok'
    }
  } else {
    Write-DiagLine -Label 'disk_status' -Value 'unknown'
  }

  if ($issues -eq 0) {
    Write-InfoLine 'Diagnostics passed.'
    return $true
  }

  Write-WarnLine "Diagnostics found $issues issue(s) that may block execution."
  return $false
}

function Test-DockerComposePlugin {
  try {
    $args = @()
    if (-not [string]::IsNullOrWhiteSpace($RunnerContext)) {
      $args += @('--context', $RunnerContext)
    }
    $args += @('compose', 'version')
    & docker @args *> $null
    return ($LASTEXITCODE -eq 0)
  } catch {
    return $false
  }
}

function Show-DockerContexts {
  if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw 'Docker command is not available.'
  }
  Write-InfoLine 'Available Docker contexts:'
  & docker context ls
  if ($LASTEXITCODE -ne 0) {
    throw "Failed to list Docker contexts (exit code $LASTEXITCODE)."
  }
}

function Try-AutoSelectDockerContext {
  if (-not [string]::IsNullOrWhiteSpace($RunnerContext)) {
    return $false
  }

  $contexts = @()
  try {
    $contexts = & docker context ls --format '{{.Name}}' 2>$null
  } catch {
    return $false
  }

  foreach ($ctx in $contexts) {
    if ([string]::IsNullOrWhiteSpace($ctx) -or $ctx -eq 'default') {
      continue
    }
    try {
      & docker --context $ctx info *> $null
      if ($LASTEXITCODE -eq 0) {
        $script:RunnerContext = $ctx
        Write-InfoLine "Using reachable Docker context: $ctx"
        return $true
      }
    } catch {
      continue
    }
  }

  return $false
}

function Ensure-DockerCommand {
  if (Get-Command docker -ErrorAction SilentlyContinue) {
    return
  }

  if ($RunnerNoInstall) {
    throw 'Docker is not installed. Remove --runner-no-install to allow guided install.'
  }

  if (Prompt-YesNo -Question 'Docker is not installed. Install Docker Desktop now?' -DefaultYes:$true) {
    Install-DockerWindows
    if (Get-Command docker -ErrorAction SilentlyContinue) {
      return
    }
    throw 'Docker install completed but docker command is still unavailable. Restart your shell and rerun.'
  }

  throw 'Docker is required.'
}

function Start-DockerDesktop {
  if (Test-DockerDaemon) {
    return
  }

  if (Try-AutoSelectDockerContext) {
    return
  }

  $dockerDesktopExe = Get-DockerDesktopPath
  if (-not $dockerDesktopExe) {
    throw 'Docker Desktop executable was not found. Install Docker Desktop first.'
  }

  Write-WarnLine 'Docker daemon is not reachable. Starting Docker Desktop.'
  Start-Process -FilePath $dockerDesktopExe | Out-Null

  for ($i = 0; $i -lt 60; $i++) {
    Start-Sleep -Seconds 2
    if (Test-DockerDaemon) {
      return
    }
  }

  throw 'Docker daemon is still unavailable. Start Docker Desktop manually and rerun.'
}

function Ensure-DockerDaemon {
  if (Test-DockerDaemon) {
    return
  }

  if (Try-AutoSelectDockerContext) {
    return
  }

  Start-DockerDesktop
}

function Ensure-ComposeAvailable {
  if (Test-DockerComposePlugin) {
    $script:UseLegacyCompose = $false
    return
  }

  if (Get-Command docker-compose -ErrorAction SilentlyContinue) {
    $script:UseLegacyCompose = $true
    return
  }

  if ($RunnerNoInstall) {
    throw 'Docker Compose is unavailable. Remove --runner-no-install to allow guided install.'
  }

  if (Prompt-YesNo -Question 'Docker Compose is missing. Reinstall Docker Desktop now?' -DefaultYes:$true) {
    Install-DockerWindows
    if (Test-DockerComposePlugin) {
      $script:UseLegacyCompose = $false
      return
    }
    if (Get-Command docker-compose -ErrorAction SilentlyContinue) {
      $script:UseLegacyCompose = $true
      return
    }
  }

  throw 'Docker Compose is required.'
}

function Try-DetectCompose {
  if (Test-DockerComposePlugin) {
    $script:UseLegacyCompose = $false
    return $true
  }
  if (Get-Command docker-compose -ErrorAction SilentlyContinue) {
    $script:UseLegacyCompose = $true
    return $true
  }
  return $false
}

function Ensure-OutputDirs {
  foreach ($sub in @('data', 'html', 'cli', 'logs')) {
    $path = Join-Path $RepoRoot "output\$sub"
    New-Item -ItemType Directory -Path $path -Force | Out-Null
  }
}

function Invoke-Compose {
  param([string[]]$ComposeArgs)

  Push-Location $RepoRoot
  try {
    if ($UseLegacyCompose) {
      $oldProfiles = $env:COMPOSE_PROFILES
      $oldContext = $env:DOCKER_CONTEXT
      $hadContext = Test-Path Env:DOCKER_CONTEXT
      try {
        if (-not [string]::IsNullOrWhiteSpace($RunnerProfile)) {
          $env:COMPOSE_PROFILES = $RunnerProfile
        } else {
          Remove-Item Env:COMPOSE_PROFILES -ErrorAction SilentlyContinue
        }
        if (-not [string]::IsNullOrWhiteSpace($RunnerContext)) {
          $env:DOCKER_CONTEXT = $RunnerContext
        } else {
          Remove-Item Env:DOCKER_CONTEXT -ErrorAction SilentlyContinue
        }
        & docker-compose -f $ComposeFile @ComposeArgs
        if ($LASTEXITCODE -ne 0) {
          throw "Compose command failed with exit code $LASTEXITCODE."
        }
      } finally {
        if ($null -eq $oldProfiles) {
          Remove-Item Env:COMPOSE_PROFILES -ErrorAction SilentlyContinue
        } else {
          $env:COMPOSE_PROFILES = $oldProfiles
        }
        if ($hadContext) {
          $env:DOCKER_CONTEXT = $oldContext
        } else {
          Remove-Item Env:DOCKER_CONTEXT -ErrorAction SilentlyContinue
        }
      }
      return
    }

    $dockerArgs = @()
    if (-not [string]::IsNullOrWhiteSpace($RunnerContext)) {
      $dockerArgs += @('--context', $RunnerContext)
    }
    $dockerArgs += @('compose', '-f', $ComposeFile)
    if (-not [string]::IsNullOrWhiteSpace($RunnerProfile)) {
      $dockerArgs += @('--profile', $RunnerProfile)
    }
    $dockerArgs += $ComposeArgs
    & docker @dockerArgs
    if ($LASTEXITCODE -ne 0) {
      throw "Compose command failed with exit code $LASTEXITCODE."
    }
  } finally {
    Pop-Location
  }
}

function Invoke-ComposeWithProfile {
  param(
    [string]$Profile,
    [string[]]$ComposeArgs
  )

  $oldProfile = $script:RunnerProfile
  try {
    $script:RunnerProfile = $Profile
    Invoke-Compose -ComposeArgs $ComposeArgs
  } finally {
    $script:RunnerProfile = $oldProfile
  }
}

function Stop-silica_xComposeStack {
  if (-not (Get-Command docker -ErrorAction SilentlyContinue) -and -not (Get-Command docker-compose -ErrorAction SilentlyContinue)) {
    Write-WarnLine 'Docker CLI is not available. Nothing to stop.'
    return
  }

  if (-not (Try-DetectCompose)) {
    Write-WarnLine 'Docker Compose command is unavailable. Skipping compose shutdown.'
    return
  }

  if (-not (Test-DockerDaemon)) {
    Write-WarnLine 'Docker daemon is not reachable. Skipping compose shutdown.'
    return
  }

  Write-InfoLine 'Stopping silica_x compose services...'
  try {
    Invoke-ComposeWithProfile -Profile '' -ComposeArgs @('down', '--remove-orphans')
  } catch {
    Write-WarnLine "Compose down reported an issue for default profile: $($_.Exception.Message)"
  }
  try {
    Invoke-ComposeWithProfile -Profile 'tor' -ComposeArgs @('down', '--remove-orphans')
  } catch {
    Write-WarnLine "Compose down reported an issue for tor profile: $($_.Exception.Message)"
  }
}

function Stop-DockerHost {
  Write-InfoLine 'Stopping Docker Desktop...'

  $dockerDesktop = Get-Process -Name 'Docker Desktop' -ErrorAction SilentlyContinue
  if ($dockerDesktop) {
    $dockerDesktop.CloseMainWindow() | Out-Null
    Start-Sleep -Seconds 2
    if (-not $dockerDesktop.HasExited) {
      $dockerDesktop | Stop-Process -Force -ErrorAction SilentlyContinue
    }
  }

  Get-Process -Name 'com.docker.backend','com.docker.proxy','vpnkit' -ErrorAction SilentlyContinue |
    Stop-Process -Force -ErrorAction SilentlyContinue

  Write-InfoLine 'Docker Desktop stop requested.'
}

function Perform-Shutdown {
  if ($silica_xArgs.Count -gt 0) {
    Write-WarnLine 'Ignoring forwarded silica_x args during shutdown.'
  }

  Stop-silica_xComposeStack

  if ($RunnerStopDocker) {
    Stop-DockerHost
  } else {
    Write-InfoLine 'silica_x containers stopped. Docker daemon left running.'
  }
}

function Run-silica_x {
  if ($RunnerUpgrade) {
    $script:RunnerBuild = $true
    $script:RunnerPull = $true
    $script:RunnerNoCache = $true
  }

  if ($RunnerPull -and -not $RunnerBuild) {
    $script:RunnerBuild = $true
  }

  if ($RunnerBuild) {
    Write-InfoLine "Building image for service: $RunnerService"
    $buildArgs = [System.Collections.Generic.List[string]]::new()
    $buildArgs.Add('build')
    if ($RunnerPull) {
      $buildArgs.Add('--pull')
    }
    if ($RunnerNoCache) {
      $buildArgs.Add('--no-cache')
    }
    if (-not [string]::IsNullOrWhiteSpace($RunnerPythonVersion)) {
      $buildArgs.Add('--build-arg')
      $buildArgs.Add("PYTHON_VERSION=$RunnerPythonVersion")
    }
    $buildArgs.Add($RunnerService)
    Invoke-Compose -ComposeArgs $buildArgs.ToArray()
  }

  $runArgs = [System.Collections.Generic.List[string]]::new()
  $runArgs.Add('run')
  $runArgs.Add('--rm')
  $runArgs.Add($RunnerService)

  if ($silica_xArgs.Count -eq 0) {
    Write-InfoLine "Starting Silica-X in prompt mode via Docker service: $RunnerService"
  } else {
    Write-InfoLine "Running Silica-X via Docker service: $RunnerService"
    foreach ($arg in $silica_xArgs) {
      $runArgs.Add($arg)
    }
  }

  Invoke-Compose -ComposeArgs $runArgs.ToArray()
}

try {
  Parse-RunnerArgs -InputArgs $CliArgs
  Configure-ModeAndService

  if ($RunnerDiagnose) {
    if (-not (Invoke-RunnerDiagnostics)) {
      exit 1
    }
    exit 0
  }

  if ($RunnerShowContexts) {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
      throw 'Docker is not installed. Install Docker to list contexts.'
    }
    Show-DockerContexts
    exit 0
  }

  Assert-ComposeFile
  if ($RunnerStop -or $RunnerStopDocker) {
    Perform-Shutdown
    exit 0
  }
  Check-Resources
  Ensure-DockerCommand
  if ($RunnerUpgradeHost) {
    Upgrade-DockerWindows
  }
  Ensure-DockerDaemon
  Ensure-ComposeAvailable
  Ensure-OutputDirs
  Run-silica_x
} catch {
  Write-ErrorLine $_.Exception.Message
  exit 1
}
