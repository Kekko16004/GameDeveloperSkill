$ErrorActionPreference = "Continue"
$env:PYTHONIOENCODING = "utf-8"
$uvx = Get-Command uvx -ErrorAction SilentlyContinue
if (-not $uvx) {
  $cand = Join-Path $env:USERPROFILE ".local\bin\uvx.exe"
  if (Test-Path -LiteralPath $cand) { $uvx = $cand }
}
if (-not $uvx) {
  Write-Host "FAIL uvx missing. powershell -c `"irm https://astral.sh/uv/install.ps1 | iex`""
  exit 1
}
$uvxPath = if ($uvx.Source) { $uvx.Source } else { [string]$uvx }
Write-Host "uvx mcp-for-blender install-addon"
& $uvxPath blender-mcp install-addon
Write-Host "Then: Blender -> Edit -> Preferences -> Add-ons -> enable MCP for Blender"
Write-Host "Then: 3D View N -> MCP for Blender -> Start MCP Server"
