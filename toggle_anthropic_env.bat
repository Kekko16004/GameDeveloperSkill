<# :
@echo off
setlocal
chcp 65001 >nul
title Claude Auth ^& Proxy Switcher
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -Command "& ([ScriptBlock]::Create((Get-Content -LiteralPath '%~f0' -Raw)))"
exit /b %ERRORLEVEL%
#>
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$settingsPath = "$HOME\.claude\settings.json"
$backupPath = "$HOME\.claude\heyroute_env_backup.json"
$claudeJsonPath = "$HOME\.claude.json"

Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
public class Win32Env {
    [DllImport("user32.dll", SetLastError = true, CharSet = CharSet.Auto)]
    public static extern IntPtr SendMessageTimeout(
        IntPtr hWnd, uint Msg, UIntPtr wParam, string lParam,
        uint fuFlags, uint uTimeout, out UIntPtr lpdwResult);
}
"@ -ErrorAction SilentlyContinue

function Broadcast-EnvChange {
    try {
        $res = [UIntPtr]::Zero
        [Win32Env]::SendMessageTimeout([IntPtr]0xffff, 0x001A, [UIntPtr]::Zero, "Environment", 2, 1000, [ref]$res) | Out-Null
    } catch {}
}

function Get-ProxyStatus {
    $envBase = [Environment]::GetEnvironmentVariable("ANTHROPIC_BASE_URL", "User")
    $envToken = [Environment]::GetEnvironmentVariable("ANTHROPIC_AUTH_TOKEN", "User")
    
    $settingsBase = $null
    $settingsToken = $null
    if (Test-Path $settingsPath) {
        try {
            $settings = Get-Content $settingsPath -Raw -Encoding UTF8 | ConvertFrom-Json
            if ($settings.env) {
                $settingsBase = $settings.env.ANTHROPIC_BASE_URL
                $settingsToken = $settings.env.ANTHROPIC_AUTH_TOKEN
            }
        } catch {}
    }

    $isActive = ($null -ne $envBase -or $null -ne $envToken -or $null -ne $settingsBase -or $null -ne $settingsToken)
    return @{
        IsActive = $isActive
        EnvBase = $envBase
        EnvToken = $envToken
        SettingsBase = $settingsBase
        SettingsToken = $settingsToken
    }
}

function Save-BackupFromCurrent {
    $backupData = [ordered]@{}
    
    # Check HKCU
    $hkcu = Get-ItemProperty "HKCU:\Environment" -ErrorAction SilentlyContinue
    if ($hkcu) {
        foreach ($prop in $hkcu.PSObject.Properties) {
            if ($prop.Name -like "ANTHROPIC_*") {
                $backupData[$prop.Name] = [string]$prop.Value
            }
        }
    }
    
    # Check settings.json
    if (Test-Path $settingsPath) {
        try {
            $settings = Get-Content $settingsPath -Raw -Encoding UTF8 | ConvertFrom-Json
            if ($settings.env) {
                foreach ($prop in $settings.env.PSObject.Properties) {
                    if ($prop.Name -like "ANTHROPIC_*" -and -not $backupData.Contains($prop.Name)) {
                        $backupData[$prop.Name] = [string]$prop.Value
                    }
                }
            }
        } catch {}
    }

    if ($backupData.Count -gt 0) {
        $json = $backupData | ConvertTo-Json -Depth 5
        [System.IO.File]::WriteAllText($backupPath, $json, [System.Text.Encoding]::UTF8)
        return $backupData
    }
    return $null
}

function Disable-Proxy {
    Write-Host "`n>>> [1/3] Salvataggio backup configurazione..." -ForegroundColor Cyan
    $saved = Save-BackupFromCurrent
    if ($saved) {
        Write-Host "    Backup salvato con $($saved.Count) variabili in: $backupPath" -ForegroundColor DarkGray
    }

    Write-Host ">>> [2/3] Rimozione variabili ANTHROPIC_* da Windows (HKCU)..." -ForegroundColor Cyan
    $hkcu = Get-ItemProperty "HKCU:\Environment" -ErrorAction SilentlyContinue
    if ($hkcu) {
        $toRemove = @($hkcu.PSObject.Properties | Where-Object { $_.Name -like "ANTHROPIC_*" } | Select-Object -ExpandProperty Name)
        foreach ($name in $toRemove) {
            Remove-ItemProperty -Path "HKCU:\Environment" -Name $name -ErrorAction SilentlyContinue
            [Environment]::SetEnvironmentVariable($name, $null, "Process")
            Write-Host "    - Rimosso da Windows: $name" -ForegroundColor DarkYellow
        }
        Broadcast-EnvChange
    }

    Write-Host ">>> [3/3] Rimozione variabili ANTHROPIC_* da settings.json..." -ForegroundColor Cyan
    if (Test-Path $settingsPath) {
        try {
            $settings = Get-Content $settingsPath -Raw -Encoding UTF8 | ConvertFrom-Json
            if ($settings.env) {
                $propsToRemove = @($settings.env.PSObject.Properties | Where-Object { $_.Name -like "ANTHROPIC_*" } | Select-Object -ExpandProperty Name)
                foreach ($p in $propsToRemove) {
                    $settings.env.PSObject.Properties.Remove($p)
                    Write-Host "    - Rimosso da settings.json: $p" -ForegroundColor DarkYellow
                }
                $updatedJson = $settings | ConvertTo-Json -Depth 10
                [System.IO.File]::WriteAllText($settingsPath, $updatedJson, [System.Text.Encoding]::UTF8)
            }
        } catch {
            Write-Host "    [!] Errore modifica settings.json: $_" -ForegroundColor Red
        }
    }

    if (Test-Path $claudeJsonPath) {
        try {
            $claudeJson = Get-Content $claudeJsonPath -Raw -Encoding UTF8 | ConvertFrom-Json
            if ($claudeJson.customApiKeyResponses) {
                $claudeJson.customApiKeyResponses = [PSCustomObject]@{ approved = @(); rejected = @() }
                $outCJson = $claudeJson | ConvertTo-Json -Depth 10
                [System.IO.File]::WriteAllText($claudeJsonPath, $outCJson, [System.Text.Encoding]::UTF8)
            }
        } catch {}
    }

    Write-Host "`n[FATTO] Proxy disattivato con successo!" -ForegroundColor Green
    Write-Host "Ora Claude Code usera l'autenticazione Pro ufficiale (/login)." -ForegroundColor White
    Write-Host "NOTA: Riavvia i terminali o VS Code per ricaricare le variabili d'ambiente.`n" -ForegroundColor Yellow
}

function Enable-Proxy {
    Write-Host "`n>>> [1/3] Caricamento backup configurazione..." -ForegroundColor Cyan
    $backupData = $null
    if (Test-Path $backupPath) {
        try {
            $raw = Get-Content $backupPath -Raw -Encoding UTF8
            $backupData = $raw | ConvertFrom-Json
        } catch {}
    }

    if (-not $backupData) {
        Write-Host "    Nessun backup trovato. Uso impostazioni predefinite Heyroute." -ForegroundColor DarkYellow
        $backupData = [PSCustomObject]@{
            ANTHROPIC_AUTH_TOKEN = "sk-mQTQ3VSQ6tPysHk9CqzdoWDNjTfjFAbaOcuA6RFRwu6lCtCs"
            ANTHROPIC_BASE_URL = "https://heyroute.ai"
            ANTHROPIC_DEFAULT_HAIKU_MODEL = "claude-haiku-4-5-20251001"
            ANTHROPIC_DEFAULT_HAIKU_MODEL_NAME = "claude-haiku-4-5-20251001"
            ANTHROPIC_DEFAULT_OPUS_MODEL = "claude-opus-5-5"
            ANTHROPIC_DEFAULT_OPUS_MODEL_NAME = "claude-opus-5-5"
            ANTHROPIC_DEFAULT_SONNET_MODEL = "claude-sonnet-5-5"
            ANTHROPIC_DEFAULT_SONNET_MODEL_NAME = "claude-sonnet-5-5"
            ANTHROPIC_MODEL = "claude-opus-5-5"
            ANTHROPIC_REASONING_MODEL = "claude-opus-5-5"
        }
    }

    Write-Host ">>> [2/3] Ripristino variabili ANTHROPIC_* in Windows (HKCU)..." -ForegroundColor Cyan
    foreach ($prop in $backupData.PSObject.Properties) {
        Set-ItemProperty -Path "HKCU:\Environment" -Name $prop.Name -Value ([string]$prop.Value) -Type String
        [Environment]::SetEnvironmentVariable($prop.Name, [string]$prop.Value, "Process")
        Write-Host "    + Impostato in Windows: $($prop.Name)" -ForegroundColor DarkGreen
    }
    Broadcast-EnvChange

    Write-Host ">>> [3/3] Ripristino variabili ANTHROPIC_* in settings.json..." -ForegroundColor Cyan
    if (Test-Path $settingsPath) {
        try {
            $settings = Get-Content $settingsPath -Raw -Encoding UTF8 | ConvertFrom-Json
            if (-not $settings.env) {
                $settings | Add-Member -NotePropertyName "env" -NotePropertyValue ([PSCustomObject]@{}) -Force
            }
            foreach ($prop in $backupData.PSObject.Properties) {
                $settings.env | Add-Member -NotePropertyName $prop.Name -NotePropertyValue ([string]$prop.Value) -Force
                Write-Host "    + Impostato in settings.json: $($prop.Name)" -ForegroundColor DarkGreen
            }
            $updatedJson = $settings | ConvertTo-Json -Depth 10
            [System.IO.File]::WriteAllText($settingsPath, $updatedJson, [System.Text.Encoding]::UTF8)
        } catch {
            Write-Host "    [!] Errore modifica settings.json: $_" -ForegroundColor Red
        }
    }

    Write-Host "`n[FATTO] Proxy Heyroute attivato con successo!" -ForegroundColor Green
    Write-Host "Ora Claude Code inoltrera le richieste a https://heyroute.ai." -ForegroundColor White
    Write-Host "NOTA: Riavvia i terminali o VS Code per ricaricare le variabili d'ambiente.`n" -ForegroundColor Yellow
}

while ($true) {
    Clear-Host
    $status = Get-ProxyStatus
    
    Write-Host "============================================================" -ForegroundColor DarkCyan
    Write-Host "         CLAUDE AUTH & PROXY ENVIRONMENT SWITCHER           " -ForegroundColor Cyan
    Write-Host "============================================================" -ForegroundColor DarkCyan
    Write-Host ""
    
    if ($status.IsActive) {
        Write-Host "  STATO ATTUALE: " -NoNewline
        Write-Host "[ ATTIVO - PROXY HEYROUTE ]" -ForegroundColor Yellow
        Write-Host ""
        $url = if ($status.EnvBase) { $status.EnvBase } elseif ($status.SettingsBase) { $status.SettingsBase } else { "N/A" }
        $tok = if ($status.EnvToken) { $status.EnvToken } elseif ($status.SettingsToken) { $status.SettingsToken } else { "N/A" }
        if ($tok.Length -gt 15) { $tok = $tok.Substring(0, 12) + "..." }
        Write-Host "  - Base URL : $url" -ForegroundColor Gray
        Write-Host "  - Token    : $tok" -ForegroundColor Gray
        Write-Host "  - Windows  : " -NoNewline
        if ($status.EnvBase) { Write-Host "Presente" -ForegroundColor Green } else { Write-Host "Non presente" -ForegroundColor DarkGray }
        Write-Host "  - Settings : " -NoNewline
        if ($status.SettingsBase) { Write-Host "Presente" -ForegroundColor Green } else { Write-Host "Non presente" -ForegroundColor DarkGray }
        Write-Host ""
        Write-Host "------------------------------------------------------------" -ForegroundColor DarkCyan
        Write-Host "  [1] DISATTIVA PROXY -> Passa a Claude Login Ufficiale" -ForegroundColor White
        Write-Host "  [2] Esci" -ForegroundColor Gray
        Write-Host "------------------------------------------------------------" -ForegroundColor DarkCyan
    } else {
        Write-Host "  STATO ATTUALE: " -NoNewline
        Write-Host "[ DISATTIVATO - CLAUDE LOGIN UFFICIALE (OAuth) ]" -ForegroundColor Green
        Write-Host ""
        Write-Host "  - Nessuna variabile proxy ANTHROPIC_* attiva." -ForegroundColor Gray
        Write-Host "  - Claude Code usera l'account Pro autenticato con /login." -ForegroundColor Gray
        $hasBackup = Test-Path $backupPath
        Write-Host "  - Backup proxy disponibile : " -NoNewline
        if ($hasBackup) { Write-Host "SI (Pronto al ripristino)" -ForegroundColor Green } else { Write-Host "NO (Usata config default)" -ForegroundColor DarkGray }
        Write-Host ""
        Write-Host "------------------------------------------------------------" -ForegroundColor DarkCyan
        Write-Host "  [1] ATTIVA PROXY -> Passa a Heyroute (Modelli custom)" -ForegroundColor White
        Write-Host "  [2] Esci" -ForegroundColor Gray
        Write-Host "------------------------------------------------------------" -ForegroundColor DarkCyan
    }

    $rawInput = Read-Host "Scegli un'opzione (1 o 2)"
    if ($null -eq $rawInput) {
        break
    }
    $choice = $rawInput.Trim()

    if ($choice -eq "1") {
        if ($status.IsActive) {
            Disable-Proxy
        } else {
            Enable-Proxy
        }
        $null = Read-Host "Premi INVIO per tornare al menu..."
    } elseif ($choice -eq "2") {
        Write-Host "`nUscita in corso..." -ForegroundColor Gray
        break
    } else {
        Write-Host "`nOpzione non valida ('$choice'). Inserisci 1 o 2." -ForegroundColor Red
        Start-Sleep -Seconds 1
    }
}
