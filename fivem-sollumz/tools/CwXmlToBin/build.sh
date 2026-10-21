#!/usr/bin/env bash
# Compila CwXmlToBin su Linux/macOS (richiede .NET SDK 8+). Uscita: tools/CwXmlToBin/bin/CwXmlToBin
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
CW="$HERE/../CodeWalker"
[ -f "$CW/CodeWalker.Core/CodeWalker.Core.csproj" ] || git clone --depth 1 https://github.com/dexyfex/CodeWalker.git "$CW"
dotnet publish "$HERE/CwXmlToBin.csproj" -c Release -o "$HERE/bin"
echo "OK -> $HERE/bin/CwXmlToBin"
