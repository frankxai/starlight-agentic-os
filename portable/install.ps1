<#
.SYNOPSIS
  Starlight Agentic OS - Portable Pack Installer (Windows / PowerShell).

.DESCRIPTION
  Symlinks ONE portable pack's assets into every CLI's expected location so a
  single pack runs identically on Claude Code, Codex, Gemini, and Grok.

  Portable tripod (locked decisions):
    memory  -> AGENTS.md  (source of truth; aliased to CLAUDE.md, wired for Gemini)
    skills  -> skills\<name>\SKILL.md  (symlinked into each CLI skills dir)
    tools   -> mcp\servers.json  (rendered per-CLI into its native MCP config)

  Idempotent. Supports -DryRun, -Uninstall, -Force.

  WINDOWS SYMLINK CAVEAT
  ----------------------
  Creating symlinks on Windows requires EITHER:
    * Developer Mode enabled (Settings > Privacy & security > For developers), OR
    * Running this script from an elevated (Administrator) PowerShell.
  New-Item -ItemType SymbolicLink is used first; if it fails due to privilege,
  the script falls back to `cmd /c mklink` (dirs use /D, junctions /J as a last
  resort for directories, which work without elevation but only for local dirs).
  If all symlink strategies fail, run once as Admin or turn on Developer Mode.

.EXAMPLE
  .\install.ps1 -Pack .\packs\acos-meta -DryRun
  .\install.ps1 -Pack .\packs\acos-meta
  .\install.ps1 -Pack .\packs\acos-meta -Uninstall
#>
[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)][string]$Pack,
  [switch]$DryRun,
  [switch]$Uninstall,
  [switch]$Force
)

$ErrorActionPreference = 'Stop'

# ------------------------------- target roots --------------------------------
function Env-Or($name, $default) {
  $v = [Environment]::GetEnvironmentVariable($name)
  if ([string]::IsNullOrWhiteSpace($v)) { return $default } else { return $v }
}
$HomeDir          = $HOME
$ClaudeHome       = Env-Or 'CLAUDE_HOME'       (Join-Path $HomeDir '.claude')
$CodexHome        = Env-Or 'CODEX_HOME'        (Join-Path $HomeDir '.codex')
$CodexAgentsHome  = Env-Or 'CODEX_AGENTS_HOME' (Join-Path $HomeDir '.agents')
$GeminiHome       = Env-Or 'GEMINI_HOME'       (Join-Path $HomeDir '.gemini')
$GrokHome         = Env-Or 'GROK_HOME'         (Join-Path $HomeDir '.grok')

# ------------------------------- helpers -------------------------------------
function Log  ($m) { Write-Host "[*] $m" -ForegroundColor Cyan }
function Ok   ($m) { Write-Host "[+] $m" -ForegroundColor Green }
function Warn ($m) { Write-Host "[!] $m" -ForegroundColor Yellow }
function Err  ($m) { Write-Host "[x] $m" -ForegroundColor Red }

# ------------------------------- resolve pack --------------------------------
if (-not (Test-Path -LiteralPath $Pack -PathType Container)) {
  Err "Pack directory not found: $Pack"; exit 2
}
$PackRoot  = (Resolve-Path -LiteralPath $Pack).Path
$PackName  = Split-Path -Leaf $PackRoot
$AgentsSrc = Join-Path $PackRoot 'AGENTS.md'
$SkillsSrc = Join-Path $PackRoot 'skills'
$McpSrc    = Join-Path $PackRoot 'mcp\servers.json'
$Manifest  = Join-Path $PackRoot '.portable-install.manifest'

function Ensure-Dir($d) {
  if (-not (Test-Path -LiteralPath $d)) {
    Log "mkdir $d"
    if (-not $DryRun) { New-Item -ItemType Directory -Force -Path $d | Out-Null }
  }
}
function Record($p) {
  if (-not $DryRun) { Add-Content -LiteralPath $Manifest -Value $p }
}

# Robust symlink creator with graceful fallback for non-elevated Windows.
function New-Link {
  param([string]$Target, [string]$LinkPath)

  # Idempotency: already a link to the right place?
  if (Test-Path -LiteralPath $LinkPath) {
    $item = Get-Item -LiteralPath $LinkPath -Force
    if ($item.LinkType) {
      if ($item.Target -contains $Target -or $item.Target -eq $Target) {
        Write-Verbose "up-to-date: $LinkPath"
        return
      }
      Log "relink $LinkPath"
      if (-not $DryRun) { Remove-Item -LiteralPath $LinkPath -Force -Recurse }
    }
    elseif ($Force) {
      Warn "backing up $LinkPath -> $LinkPath.bak"
      if (-not $DryRun) { Move-Item -LiteralPath $LinkPath -Destination "$LinkPath.bak" -Force }
    }
    else {
      Err "Refusing to overwrite non-symlink: $LinkPath (use -Force)"; return
    }
  }
  else {
    Log "link $LinkPath -> $Target"
  }

  Ensure-Dir (Split-Path -Parent $LinkPath)
  if ($DryRun) { Write-Host "    dry-run: symlink $LinkPath -> $Target" -ForegroundColor DarkGray; return }

  $isDir = Test-Path -LiteralPath $Target -PathType Container
  $made  = $false
  try {
    New-Item -ItemType SymbolicLink -Path $LinkPath -Target $Target -Force | Out-Null
    $made = $true
  } catch {
    Warn "New-Item symlink failed (privilege?). Falling back to mklink..."
    $flag = if ($isDir) { '/D' } else { '' }
    cmd /c "mklink $flag `"$LinkPath`" `"$Target`"" | Out-Null
    if ($LASTEXITCODE -eq 0) { $made = $true }
    elseif ($isDir) {
      Warn "mklink /D failed; trying directory junction (/J, no elevation needed)..."
      cmd /c "mklink /J `"$LinkPath`" `"$Target`"" | Out-Null
      if ($LASTEXITCODE -eq 0) { $made = $true }
    }
  }
  if ($made) { Record $LinkPath }
  else { Err "Could not create link $LinkPath. Enable Developer Mode or run as Administrator." }
}

# ------------------------------- uninstall -----------------------------------
function Invoke-Uninstall {
  Log "Uninstalling pack '$PackName' (installer-created links only)"
  if (-not (Test-Path -LiteralPath $Manifest)) {
    Warn "No manifest at $Manifest - nothing to remove."
  } else {
    $lines = Get-Content -LiteralPath $Manifest | Where-Object { $_ -ne '' }
    [array]::Reverse($lines)
    foreach ($p in $lines) {
      $it = Get-Item -LiteralPath $p -Force -ErrorAction SilentlyContinue
      if ($it -and $it.LinkType) {
        Log "unlink $p"
        if (-not $DryRun) { Remove-Item -LiteralPath $p -Force -Recurse }
      } elseif ($it) {
        Warn "skip (not a link): $p"
      }
    }
    if (-not $DryRun) { Remove-Item -LiteralPath $Manifest -Force }
  }
  # Strip the marked Codex block.
  $codex = Join-Path $CodexHome 'config.toml'
  if ((Test-Path -LiteralPath $codex) -and (-not $DryRun)) {
    $txt = Get-Content -LiteralPath $codex -Raw
    $clean = [regex]::Replace($txt,
      '(?s)# >>> starlight-portable mcp_servers >>>.*?# <<< starlight-portable mcp_servers <<<\r?\n?', '')
    Set-Content -LiteralPath $codex -Value $clean
  }
  Ok "Uninstall complete for '$PackName'."
}

# ------------------------------- MCP render ----------------------------------
function Render-Mcp {
  if (-not (Test-Path -LiteralPath $McpSrc)) { Warn "No mcp\servers.json - skipping MCP wiring."; return }
  Ensure-Dir $ClaudeHome; Ensure-Dir $GeminiHome; Ensure-Dir $CodexHome
  if ($DryRun) { Log "dry-run: would render MCP for Claude/.mcp.json, Gemini/settings.json, Codex/config.toml"; return }

  $raw = Get-Content -LiteralPath $McpSrc -Raw | ConvertFrom-Json
  $servers = if ($raw.PSObject.Properties.Name -contains 'mcpServers') { $raw.mcpServers } else { $raw }

  # ${PACK_ROOT} interpolation (string values / arrays).
  function Interp($o) {
    if ($o -is [string]) { return $o.Replace('${PACK_ROOT}', $PackRoot) }
    if ($o -is [System.Collections.IEnumerable] -and -not ($o -is [string])) {
      return @($o | ForEach-Object { Interp $_ })
    }
    if ($o -is [psobject]) {
      $h = [ordered]@{}
      foreach ($p in $o.PSObject.Properties) { $h[$p.Name] = Interp $p.Value }
      return [pscustomobject]$h
    }
    return $o
  }
  $servers = Interp $servers

  # ---- Claude Code + Gemini: mcpServers JSON merge --------------------------
  function Merge-JsonMcp($path, $key) {
    $doc = @{}
    if (Test-Path -LiteralPath $path) {
      try { $doc = Get-Content -LiteralPath $path -Raw | ConvertFrom-Json -AsHashtable } catch { $doc = @{} }
    }
    if (-not $doc.ContainsKey($key)) { $doc[$key] = @{} }
    foreach ($p in $servers.PSObject.Properties) { $doc[$key][$p.Name] = $p.Value }
    ($doc | ConvertTo-Json -Depth 20) | Set-Content -LiteralPath $path
    Record $path
  }
  Merge-JsonMcp (Join-Path $ClaudeHome '.mcp.json')     'mcpServers'
  Merge-JsonMcp (Join-Path $GeminiHome 'settings.json') 'mcpServers'

  # ---- Codex config.toml : [mcp_servers.<name>] ----------------------------
  function ConvertTo-TomlValue($v) {
    if ($v -is [bool])   { return $(if ($v) { 'true' } else { 'false' }) }
    if ($v -is [int] -or $v -is [double] -or $v -is [long]) { return "$v" }
    if ($v -is [System.Collections.IEnumerable] -and -not ($v -is [string])) {
      return '[' + (($v | ForEach-Object { ConvertTo-TomlValue $_ }) -join ', ') + ']'
    }
    $s = "$v" -replace '\\', '\\\\' -replace '"', '\"'
    return '"' + $s + '"'
  }
  $sb = [System.Text.StringBuilder]::new()
  [void]$sb.AppendLine('# >>> starlight-portable mcp_servers >>>')
  [void]$sb.AppendLine('# Managed by Starlight portable installer')
  foreach ($p in $servers.PSObject.Properties) {
    [void]$sb.AppendLine("[mcp_servers.$($p.Name)]")
    foreach ($f in $p.Value.PSObject.Properties) {
      if ($f.Value -is [psobject] -and -not ($f.Value -is [string]) -and $f.Value.PSObject.Properties) {
        $inner = ($f.Value.PSObject.Properties | ForEach-Object { "$($_.Name) = $(ConvertTo-TomlValue $_.Value)" }) -join ', '
        [void]$sb.AppendLine("$($f.Name) = { $inner }")
      } else {
        [void]$sb.AppendLine("$($f.Name) = $(ConvertTo-TomlValue $f.Value)")
      }
    }
    [void]$sb.AppendLine('')
  }
  [void]$sb.AppendLine('# <<< starlight-portable mcp_servers <<<')
  $block = $sb.ToString()

  $codexPath = Join-Path $CodexHome 'config.toml'
  $prev = ''
  if (Test-Path -LiteralPath $codexPath) { $prev = Get-Content -LiteralPath $codexPath -Raw }
  if ($prev -match '# >>> starlight-portable mcp_servers >>>') {
    $new = [regex]::Replace($prev,
      '(?s)# >>> starlight-portable mcp_servers >>>.*?# <<< starlight-portable mcp_servers <<<\r?\n?', $block)
  } else {
    $new = ($(if ($prev.Trim()) { $prev.TrimEnd() + "`n`n" } else { '' })) + $block
  }
  Set-Content -LiteralPath $codexPath -Value $new
  Ok "MCP rendered -> Claude(.mcp.json), Gemini(settings.json), Codex(config.toml)"
}

# ------------------------------- Gemini memory -------------------------------
function Wire-GeminiMemory {
  New-Link -Target $AgentsSrc -LinkPath (Join-Path $GeminiHome 'AGENTS.md')
  $gset = Join-Path $GeminiHome 'settings.json'
  if ($DryRun) { Log "dry-run: would set context.fileName=AGENTS.md in $gset"; return }
  Ensure-Dir $GeminiHome
  $doc = @{}
  if (Test-Path -LiteralPath $gset) {
    try { $doc = Get-Content -LiteralPath $gset -Raw | ConvertFrom-Json -AsHashtable } catch { $doc = @{} }
  }
  if (-not $doc.ContainsKey('context')) { $doc['context'] = @{} }
  $doc['context']['fileName'] = 'AGENTS.md'
  ($doc | ConvertTo-Json -Depth 20) | Set-Content -LiteralPath $gset
  Ok "Gemini context.fileName -> AGENTS.md"
}

# ------------------------------- main ----------------------------------------
Log "Pack: $PackName"
Log "Root: $PackRoot"
if ($DryRun) { Warn 'DRY-RUN: no filesystem changes will be made.' }

if (-not (Test-Path -LiteralPath $AgentsSrc)) { Err "Missing AGENTS.md at $AgentsSrc"; exit 1 }
if (-not (Test-Path -LiteralPath $SkillsSrc)) { Err "Missing skills\ at $SkillsSrc"; exit 1 }

if ($Uninstall) { Invoke-Uninstall; exit 0 }

Log '--- Skills ---'
New-Link -Target $SkillsSrc -LinkPath (Join-Path $ClaudeHome "skills\$PackName")
New-Link -Target $SkillsSrc -LinkPath (Join-Path $CodexAgentsHome "skills\$PackName")
New-Link -Target $SkillsSrc -LinkPath (Join-Path $GeminiHome "skills\$PackName")

Log '--- Memory (AGENTS.md) ---'
New-Link -Target $AgentsSrc -LinkPath (Join-Path $CodexHome 'AGENTS.md')
New-Link -Target $AgentsSrc -LinkPath (Join-Path $GrokHome  'AGENTS.md')
New-Link -Target $AgentsSrc -LinkPath (Join-Path $ClaudeHome 'CLAUDE.md')
Wire-GeminiMemory

Log '--- MCP tools ---'
Render-Mcp

Ok "Installed pack '$PackName' across Claude Code, Codex, Gemini, Grok."
if (-not $DryRun) { Log "Manifest: $Manifest" }
Log "Verify with: bash .\verify-portability.sh `"$PackRoot`""
