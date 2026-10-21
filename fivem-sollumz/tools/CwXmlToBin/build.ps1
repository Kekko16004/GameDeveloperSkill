# Compila CwXmlToBin (richiede .NET SDK 8+: winget install Microsoft.DotNet.SDK.8)
# Uscita: tools\CwXmlToBin\bin\CwXmlToBin.exe
$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$cw = Join-Path $here "..\CodeWalker"
if (-not (Test-Path (Join-Path $cw "CodeWalker.Core\CodeWalker.Core.csproj"))) {
    git clone --depth 1 https://github.com/dexyfex/CodeWalker.git $cw
}
dotnet publish (Join-Path $here "CwXmlToBin.csproj") -c Release -o (Join-Path $here "bin")
Write-Host "OK -> $(Join-Path $here 'bin\CwXmlToBin.exe')"
