param(
    [Parameter(Mandatory = $true)]
    [string]$Wheel,
    [Parameter(Mandatory = $true)]
    [string]$Constraints,
    [Parameter(Mandatory = $true)]
    [string]$Launcher,
    [Parameter(Mandatory = $true)]
    [string]$PackageName,
    [Parameter(Mandatory = $true)]
    [string]$Publisher,
    [Parameter(Mandatory = $true)]
    [string]$PublisherDisplayName,
    [Parameter(Mandatory = $true)]
    [string]$Version,
    [Parameter(Mandatory = $true)]
    [string]$Output
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

if ($env:OS -ne "Windows_NT") {
    throw "Le paquet Store doit etre construit sur Windows."
}
if ($PackageName -notmatch '^[A-Za-z0-9.-]{3,80}$') {
    throw "Le nom de paquet Store est invalide."
}
if ($Version -notmatch '^(\d+)\.(\d+)\.(\d+)(?:[-+].*)?$') {
    throw "La version doit utiliser le format MAJOR.MINOR.PATCH."
}
$MsixVersion = "$($Matches[1]).$($Matches[2]).$($Matches[3]).0"

$RepositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$WheelPath = (Resolve-Path $Wheel).Path
$ConstraintsPath = (Resolve-Path $Constraints).Path
$LauncherPath = (Resolve-Path $Launcher).Path
$ManifestTemplate = Join-Path $RepositoryRoot "agent\backend\windows\Package.appxmanifest.template"
$Logo = Join-Path $RepositoryRoot "agent\frontend\public\3decks-logo.png"
$OutputPath = [IO.Path]::GetFullPath($Output)
$OutputDirectory = Split-Path -Parent $OutputPath
New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null

$TemporaryBase = if ($env:RUNNER_TEMP) {
    [IO.Path]::GetFullPath($env:RUNNER_TEMP)
}
else {
    [IO.Path]::GetFullPath([IO.Path]::GetTempPath())
}
$BuildRoot = Join-Path $TemporaryBase ("3decks-msix-" + [guid]::NewGuid())
$Stage = Join-Path $BuildRoot "package"
$Runtime = Join-Path $Stage "runtime"
New-Item -ItemType Directory -Path $Runtime -Force | Out-Null

try {
    Write-Host "Preparing a private Python 3.12 runtime..."
    & uv python install 3.12
    if ($LASTEXITCODE -ne 0) { throw "uv could not install Python 3.12." }
    $Python = (& uv python find 3.12).Trim()
    if (!(Test-Path -LiteralPath $Python -PathType Leaf)) {
        throw "The managed Python runtime was not found."
    }
    $PythonRoot = Split-Path -Parent $Python
    Copy-Item -Path (Join-Path $PythonRoot "*") -Destination $Runtime -Recurse -Force

    $SitePackages = Join-Path $Runtime "Lib\site-packages"
    New-Item -ItemType Directory -Path $SitePackages -Force | Out-Null
    & uv pip install --target $SitePackages --constraints $ConstraintsPath $WheelPath
    if ($LASTEXITCODE -ne 0) { throw "The wheel could not be installed in the MSIX runtime." }

    Copy-Item -LiteralPath $LauncherPath -Destination (Join-Path $Stage "3Decks.exe")
    $Assets = Join-Path $Stage "Assets"
    New-Item -ItemType Directory -Path $Assets -Force | Out-Null

    Add-Type -AssemblyName System.Drawing
    $SourceImage = [Drawing.Image]::FromFile($Logo)
    try {
        foreach ($Asset in @(
            @{ Name = "StoreLogo.png"; Size = 50 },
            @{ Name = "Square44x44Logo.png"; Size = 44 },
            @{ Name = "Square150x150Logo.png"; Size = 150 }
        )) {
            $Size = [int]$Asset.Size
            $Bitmap = [Drawing.Bitmap]::new($Size, $Size)
            $Graphics = [Drawing.Graphics]::FromImage($Bitmap)
            try {
                $Graphics.Clear([Drawing.Color]::Transparent)
                $Scale = [Math]::Min($Size / $SourceImage.Width, $Size / $SourceImage.Height)
                $Width = [int]($SourceImage.Width * $Scale)
                $Height = [int]($SourceImage.Height * $Scale)
                $X = [int](($Size - $Width) / 2)
                $Y = [int](($Size - $Height) / 2)
                $Graphics.DrawImage($SourceImage, $X, $Y, $Width, $Height)
                $Bitmap.Save(
                    (Join-Path $Assets $Asset.Name),
                    [Drawing.Imaging.ImageFormat]::Png
                )
            }
            finally {
                $Graphics.Dispose()
                $Bitmap.Dispose()
            }
        }
    }
    finally {
        $SourceImage.Dispose()
    }

    $Manifest = Get-Content -LiteralPath $ManifestTemplate -Raw
    $Manifest = $Manifest.Replace("__PACKAGE_NAME__", [Security.SecurityElement]::Escape($PackageName))
    $Manifest = $Manifest.Replace("__PUBLISHER__", [Security.SecurityElement]::Escape($Publisher))
    $Manifest = $Manifest.Replace("__PUBLISHER_DISPLAY_NAME__", [Security.SecurityElement]::Escape($PublisherDisplayName))
    $Manifest = $Manifest.Replace("__VERSION__", $MsixVersion)
    $Manifest = $Manifest.Replace("__EXECUTABLE__", "3Decks.exe")
    if ($Manifest -match '__[A-Z0-9_]+__') {
        throw "The Store manifest still contains unresolved placeholders."
    }
    Set-Content -LiteralPath (Join-Path $Stage "AppxManifest.xml") -Value $Manifest -Encoding UTF8

    $MakeAppx = Get-ChildItem \
        "${env:ProgramFiles(x86)}\Windows Kits\10\bin\*\x64\makeappx.exe" |
        Sort-Object FullName -Descending |
        Select-Object -First 1
    if ($null -eq $MakeAppx) {
        throw "makeappx.exe is unavailable on this Windows runner."
    }
    Remove-Item -LiteralPath $OutputPath -Force -ErrorAction SilentlyContinue
    & $MakeAppx.FullName pack /d $Stage /p $OutputPath /o
    if ($LASTEXITCODE -ne 0) { throw "MakeAppx failed." }

    Write-Host "Unsigned Store submission package: $OutputPath"
    Write-Host "Submit this artifact to Partner Center; never offer it as a direct download."
}
finally {
    if ($BuildRoot.StartsWith($TemporaryBase, [StringComparison]::OrdinalIgnoreCase)) {
        Remove-Item -LiteralPath $BuildRoot -Recurse -Force -ErrorAction SilentlyContinue
    }
}
