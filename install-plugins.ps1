# Open the claude.ai Plugins page and print the clicks. Run this yourself.
# It cannot add the plugin. It does not copy skills, and it does not schedule anything.
param()
$ErrorActionPreference = 'Stop'
if ($args.Count -gt 0) { throw 'install-plugins.ps1 takes no arguments.' }
$url = 'https://claude.ai/customize/plugins'
$catalog = 'living-relation/handbuilt-cad'

function Get-HandbuiltClaudeAiLine {
  $id = 'handbuilt-cad@handbuilt-cad-plugins'
  $ok = 'The handbuilt-cad plugin is present on claude.ai.'
  $missing = 'WARN: The handbuilt-cad plugin is not added on claude.ai yet. Add catalog living-relation/handbuilt-cad and turn on handbuilt-cad.'
  $settings = Join-Path $env:USERPROFILE '.claude\settings.json'
  if (Test-Path -LiteralPath $settings) {
    try {
      $j = Get-Content -LiteralPath $settings -Raw -ErrorAction Stop | ConvertFrom-Json
      $ep = $j.enabledPlugins
      if ($null -ne $ep -and $ep.PSObject.Properties.Name -contains $id) {
        $val = $ep.PSObject.Properties[$id].Value
        if ($val -eq $true) { return $ok }
      }
    } catch {}
  }
  return $missing
}

Write-Host (Get-HandbuiltClaudeAiLine)
Write-Host ''
Write-Host 'handbuilt-cad on claude.ai'
Write-Host 'This script cannot add the plugin. Do these clicks yourself.'
Write-Host ''
Write-Host "Catalog to paste: $catalog"
Write-Host 'Catalog name: handbuilt-cad-plugins'
Write-Host ''
Write-Host '1. Sign in to the claude.ai account you use.'
Write-Host '2. Open Customize.'
Write-Host '3. Open Plugins.'
Write-Host '4. Choose Add.'
Write-Host '5. Choose Add marketplace.'
Write-Host "6. Paste $catalog."
Write-Host '7. Turn Sync automatically on. Where that switch sits on the page is unverified until someone clicks through Customize.'
Write-Host '8. Open handbuilt-cad and turn it on (Add).'
Write-Host '9. Chat, Cowork, and Claude Code signed in to this account all use that plugin.'
Write-Host ''
Write-Host 'Update: Turn Sync automatically on. Updates arrive automatically after merges to main. Check for updates in the catalog forces it sooner.'
Write-Host 'Remove: open handbuilt-cad, open its menu, choose Remove.'
Write-Host ''
Write-Host 'Cursor is separate. Leave Auto Refresh off.'
Write-Host 'Individual account: copy the plugin to ~/.cursor/plugins/local/handbuilt-cad (a real copy, not a shortcut to the clone). Include .cursor-plugin/plugin.json and skills/. Restart Cursor or run Developer: Reload Window. Open Customize and confirm the skills.'
Write-Host 'Update that copy: the Cursor local copy still updates by re-running this script (replace the copy, then reload).'
Write-Host 'Remove that copy: delete ~/.cursor/plugins/local/handbuilt-cad and reload.'
Write-Host 'Team or Enterprise account: Dashboard, Plugins & MCPs, Add Marketplace, Import from Repo. Paste https://github.com/living-relation/handbuilt-cad. Under Marketplace Settings, leave Enable Auto Refresh off. Then in Customize, install handbuilt-cad. Update: open the marketplace and choose Refresh.'
Write-Host ''
Write-Host "Opening $url"
try { Start-Process $url }
catch { Write-Host "Could not open a browser. Open this page yourself: $url" }
