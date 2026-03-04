[CmdletBinding()]
param(
  [Parameter(ValueFromRemainingArguments = $true)]
  [string[]]$CliArgs
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$ScriptName = Split-Path -Leaf $PSCommandPath
$ScriptDir = Split-Path -Parent $PSCommandPath

$TorConfig = Join-Path $ScriptDir 'torrc.silica'
$TorDataDir = if ($env:TOR_DATA_DIR) { $env:TOR_DATA_DIR } else { Join-Path $env:TEMP 'tor-data' }
$NoInstall = $false
$TorArgs = [System.Collections.Generic.List[string]]::new()

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
  .\docker\$ScriptName [wrapper-options] [tor-args...]
  .\docker\$ScriptName [wrapper-options] -- [tor-args...]

Wrapper options:
  --help               Show this help.
  --config <path>      Tor config file path (default: docker/torrc.silica).
  --data-dir <path>    Tor data dir (default: %TEMP%\tor-data).
  --no-install         Never install Tor automatically.

Any other args are forwarded to the Tor process.
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
  return $reply.Trim().ToLowerInvariant().StartsWith('y')
}

function Parse-Args {
  param([string[]]$InputArgs)

  $i = 0
  while ($i -lt $InputArgs.Count) {
    $token = $InputArgs[$i]
    switch ($token) {
      '--help' {
        Show-Help
        exit 0
      }
      '--config' {
        $i++
        if ($i -ge $InputArgs.Count) {
          throw 'Missing value for --config'
        }
        $script:TorConfig = $InputArgs[$i]
      }
      '--data-dir' {
        $i++
        if ($i -ge $InputArgs.Count) {
          throw 'Missing value for --data-dir'
        }
        $script:TorDataDir = $InputArgs[$i]
      }
      '--no-install' {
        $script:NoInstall = $true
      }
      '--' {
        $i++
        while ($i -lt $InputArgs.Count) {
          $script:TorArgs.Add($InputArgs[$i])
          $i++
        }
        break
      }
      default {
        $script:TorArgs.Add($token)
      }
    }
    $i++
  }
}

function Resolve-TorBinary {
  $fromPath = Get-Command tor -ErrorAction SilentlyContinue
  if ($fromPath) {
    return $fromPath.Source
  }

  $candidates = @(
    (Join-Path $env:ProgramFiles 'Tor Browser\Browser\TorBrowser\Tor\tor.exe'),
    (Join-Path ${env:ProgramFiles(x86)} 'Tor Browser\Browser\TorBrowser\Tor\tor.exe'),
    (Join-Path $env:LocalAppData 'Tor Browser\Browser\TorBrowser\Tor\tor.exe')
  )

  foreach ($candidate in $candidates) {
    if ($candidate -and (Test-Path -Path $candidate -PathType Leaf)) {
      return $candidate
    }
  }

  return $null
}

function Install-TorWindows {
  Write-InfoLine 'Installing Tor...'

  if (Get-Command winget -ErrorAction SilentlyContinue) {
    & winget install -e --id TorProject.TorBrowser --accept-source-agreements --accept-package-agreements
    return
  }
  if (Get-Command choco -ErrorAction SilentlyContinue) {
    & choco install -y tor-browser
    return
  }

  throw 'Neither winget nor choco is available. Install Tor manually and rerun.'
}

function Ensure-Tor {
  $torBin = Resolve-TorBinary
  if ($torBin) {
    return $torBin
  }

  if ($NoInstall) {
    throw 'Tor is not installed. Remove --no-install to allow guided install.'
  }

  if (Prompt-YesNo -Question 'Tor is not installed. Install it now?' -DefaultYes:$true) {
    Install-TorWindows
    $torBin = Resolve-TorBinary
    if ($torBin) {
      return $torBin
    }
    throw 'Tor install completed but binary is still unavailable. Restart shell and rerun.'
  }

  throw 'Tor is required.'
}

function Start-Tor {
  param([string]$TorBinary)

  New-Item -ItemType Directory -Path $TorDataDir -Force | Out-Null

  if (Test-Path -Path $TorConfig -PathType Leaf) {
    Write-InfoLine "Starting Tor with config: $TorConfig"
    & $TorBinary --DataDirectory $TorDataDir -f $TorConfig @TorArgs
    exit $LASTEXITCODE
  }

  Write-WarnLine "Config file not found at '$TorConfig'. Starting Tor with inline defaults."
  & $TorBinary `
    --DataDirectory $TorDataDir `
    --SocksPort 127.0.0.1:9050 `
    --ClientOnly 1 `
    --AvoidDiskWrites 1 `
    @TorArgs
  exit $LASTEXITCODE
}

try {
  Parse-Args -InputArgs $CliArgs
  $torBinary = Ensure-Tor
  Start-Tor -TorBinary $torBinary
} catch {
  Write-ErrorLine $_.Exception.Message
  exit 1
}
