$ErrorActionPreference = "Stop"
if (Get-Command unity -ErrorAction SilentlyContinue) {
  Write-Host "Unity CLI already on PATH: $(unity --version 2>$null)"
  exit 0
}
Write-Host "Installing Unity CLI (beta)..."
$env:UNITY_CLI_CHANNEL = "beta"
try {
  irm https://public-cdn.cloud.unity3d.com/hub/prod/cli/install.ps1 | iex
} catch {
  Write-Host "CDN script failed, trying winget..."
  winget install Unity.CLI --accept-package-agreements --accept-source-agreements
}
if (Get-Command unity -ErrorAction SilentlyContinue) {
  Write-Host "OK unity $(unity --version 2>$null)"
} else {
  Write-Host "WARN: reopen the terminal, then unity --version"
  Write-Host "Docs: https://docs.unity.com/en-us/unity-cli/use-unity-cli.md"
}
