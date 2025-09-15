# Plex File Renamer - Windows Installation Script (PowerShell)

param(
    [string]$Version = ""
)

# Configuration
$RepoOwner = "trentmillar"
$RepoName = "plex-file-namer"
$InstallDir = "$env:LOCALAPPDATA\Programs\PlexFileRenamer"
$ConfigDir = "$env:APPDATA\PlexFileRenamer"

# Colors
function Write-ColorOutput($ForegroundColor) {
    $fc = $host.UI.RawUI.ForegroundColor
    $host.UI.RawUI.ForegroundColor = $ForegroundColor
    if ($args) {
        Write-Output $args
    }
    $host.UI.RawUI.ForegroundColor = $fc
}

Write-Host "🎬 Plex File Renamer - Windows Installation Script" -ForegroundColor Green
Write-Host "===================================================" -ForegroundColor Green
Write-Host ""

# Check if running as administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")
if (-not $isAdmin) {
    Write-Host "Note: Running without administrator privileges." -ForegroundColor Yellow
    Write-Host "Some features may require manual configuration." -ForegroundColor Yellow
    Write-Host ""
}

# Fetch available releases
Write-Host "Fetching available releases..." -ForegroundColor Blue

try {
    $releases = Invoke-RestMethod -Uri "https://api.github.com/repos/$RepoOwner/$RepoName/releases" -Method Get
    $releaseVersions = $releases | Select-Object -First 20 | ForEach-Object { $_.tag_name }
} catch {
    Write-Host "Could not fetch releases. Installing from main branch..." -ForegroundColor Yellow
    $Version = "main"
}

# Select version
if ($Version -eq "" -and $releaseVersions.Count -gt 0) {
    $latest = $releaseVersions[0]
    
    Write-Host "Available versions:" -ForegroundColor Green
    Write-Host "  [0] Latest ($latest) - Recommended" -ForegroundColor Cyan
    
    for ($i = 0; $i -lt $releaseVersions.Count; $i++) {
        Write-Host "  [$($i + 1)] $($releaseVersions[$i])"
    }
    
    $selection = Read-Host "`nSelect version [0-$($releaseVersions.Count)], or press Enter for latest"
    
    if ($selection -eq "" -or $selection -eq "0") {
        $Version = $latest
    } elseif ([int]$selection -le $releaseVersions.Count) {
        $Version = $releaseVersions[[int]$selection - 1]
    } else {
        $Version = $latest
    }
}

Write-Host "Installing version: $Version" -ForegroundColor Green

# Check Python installation
Write-Host "`nChecking Python installation..." -ForegroundColor Blue

$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    $pythonCmd = Get-Command python3 -ErrorAction SilentlyContinue
}

if ($pythonCmd) {
    $pythonVersion = & $pythonCmd.Source --version 2>&1
    Write-Host "✓ Python found: $pythonVersion" -ForegroundColor Green
} else {
    Write-Host "Python not found!" -ForegroundColor Red
    Write-Host "Please install Python from: https://www.python.org/downloads/" -ForegroundColor Yellow
    Write-Host "Make sure to check 'Add Python to PATH' during installation!" -ForegroundColor Yellow
    
    $install = Read-Host "Would you like to open the Python download page? (Y/N)"
    if ($install -eq "Y" -or $install -eq "y") {
        Start-Process "https://www.python.org/downloads/"
    }
    
    Write-Host "`nPlease run this script again after installing Python." -ForegroundColor Yellow
    exit 1
}

# Check ffmpeg installation
Write-Host "Checking ffmpeg installation..." -ForegroundColor Blue

$ffmpegCmd = Get-Command ffmpeg -ErrorAction SilentlyContinue
if ($ffmpegCmd) {
    Write-Host "✓ ffmpeg found" -ForegroundColor Green
} else {
    Write-Host "ffmpeg not found (optional but recommended)" -ForegroundColor Yellow
    Write-Host "To install ffmpeg:" -ForegroundColor Yellow
    Write-Host "  1. Download from: https://ffmpeg.org/download.html" -ForegroundColor Cyan
    Write-Host "  2. Or use: choco install ffmpeg (if you have Chocolatey)" -ForegroundColor Cyan
    Write-Host "  3. Or use: winget install ffmpeg (if you have Windows Package Manager)" -ForegroundColor Cyan
}

# Create directories
Write-Host "`nCreating installation directories..." -ForegroundColor Blue
New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
New-Item -ItemType Directory -Force -Path $ConfigDir | Out-Null

# Download and extract
Write-Host "Downloading Plex File Renamer $Version..." -ForegroundColor Blue

$tempDir = New-TemporaryFile | ForEach-Object { Remove-Item $_; New-Item -ItemType Directory -Path $_ }

if ($Version -eq "main") {
    $downloadUrl = "https://github.com/$RepoOwner/$RepoName/archive/main.zip"
} else {
    $downloadUrl = "https://github.com/$RepoOwner/$RepoName/releases/download/$Version/plex-file-renamer-$Version.zip"
}

$zipPath = Join-Path $tempDir "release.zip"

try {
    Invoke-WebRequest -Uri $downloadUrl -OutFile $zipPath
} catch {
    Write-Host "Failed to download release. Trying alternative URL..." -ForegroundColor Yellow
    $downloadUrl = "https://github.com/$RepoOwner/$RepoName/archive/$Version.zip"
    Invoke-WebRequest -Uri $downloadUrl -OutFile $zipPath
}

# Extract
Write-Host "Extracting files..." -ForegroundColor Blue
Expand-Archive -Path $zipPath -DestinationPath $tempDir -Force

# Find extracted folder
$extractedFolder = Get-ChildItem -Path $tempDir -Directory | Select-Object -First 1

# Install Python dependencies
Write-Host "Installing Python dependencies..." -ForegroundColor Blue
Push-Location $extractedFolder.FullName
& pip install --user -r requirements.txt
Pop-Location

# Copy files
Write-Host "Installing files..." -ForegroundColor Blue
Copy-Item -Path (Join-Path $extractedFolder.FullName "plex_file_renamer.py") -Destination $InstallDir -Force
Copy-Item -Path (Join-Path $extractedFolder.FullName "requirements.txt") -Destination $InstallDir -Force

if (Test-Path (Join-Path $extractedFolder.FullName "README.md")) {
    Copy-Item -Path (Join-Path $extractedFolder.FullName "README.md") -Destination $ConfigDir -Force
}

# Create batch file wrapper
$batchContent = @"
@echo off
python "$InstallDir\plex_file_renamer.py" %*
"@
$batchPath = Join-Path $InstallDir "plex-renamer.bat"
Set-Content -Path $batchPath -Value $batchContent

# Create PowerShell wrapper
$ps1Content = @"
#!/usr/bin/env pwsh
python "$InstallDir\plex_file_renamer.py" `$args
"@
$ps1Path = Join-Path $InstallDir "plex-renamer.ps1"
Set-Content -Path $ps1Path -Value $ps1Content

# Create sample config if it doesn't exist
$configPath = Join-Path $env:USERPROFILE ".plex-renamer.conf"
if (-not (Test-Path $configPath)) {
    $configContent = @"
[default]
# TMDb API key (get free key from https://www.themoviedb.org/settings/api)
# api_key = your_api_key_here

# Default media type: auto, movie, or tv
default_type = auto

# Only detect years in parentheses format (2004)
parentheses_only = false

# Skip confirmation prompts for batch operations
skip_confirmation = false
"@
    Set-Content -Path $configPath -Value $configContent
    Write-Host "✓ Created sample config at $configPath" -ForegroundColor Green
}

# Add to PATH
Write-Host "`nUpdating PATH..." -ForegroundColor Blue

$currentPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($currentPath -notlike "*$InstallDir*") {
    $newPath = "$currentPath;$InstallDir"
    
    if ($isAdmin) {
        [Environment]::SetEnvironmentVariable("Path", $newPath, "User")
        Write-Host "✓ Added to PATH (permanent)" -ForegroundColor Green
    } else {
        $env:Path = $newPath
        Write-Host "✓ Added to PATH (current session only)" -ForegroundColor Green
        Write-Host "To make permanent, run as administrator or add manually:" -ForegroundColor Yellow
        Write-Host "  $InstallDir" -ForegroundColor Cyan
    }
} else {
    Write-Host "✓ Already in PATH" -ForegroundColor Green
}

# Clean up
Remove-Item -Path $tempDir -Recurse -Force

# Done
Write-Host "`n✅ Installation complete!" -ForegroundColor Green
Write-Host ""
Write-Host "To get started:" -ForegroundColor Cyan
Write-Host "  1. Get a free TMDb API key: https://www.themoviedb.org/settings/api" -ForegroundColor White
Write-Host "  2. Edit $configPath and add your API key" -ForegroundColor White
Write-Host "  3. Run: plex-renamer --help" -ForegroundColor White
Write-Host ""
Write-Host "Usage examples:" -ForegroundColor Cyan
Write-Host "  plex-renamer 'C:\Videos\movie.mp4' --dry-run" -ForegroundColor White
Write-Host "  plex-renamer 'C:\Videos' --rename" -ForegroundColor White
Write-Host ""

if (-not $isAdmin) {
    Write-Host "Note: For permanent PATH update, run this script as Administrator" -ForegroundColor Yellow
}