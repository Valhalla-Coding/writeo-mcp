# Windows: irm https://raw.githubusercontent.com/Valhalla-Coding/writeo-mcp/main/install.ps1 | iex
# Wrapped in a function so a piped run leaves no variables behind and errors do not close the window.
function Install-WriteoMcp {
    $ErrorActionPreference = "Stop"
    if (-not $env:WRITEO_MCP_SOURCE) {
        $env:WRITEO_MCP_SOURCE = "https://github.com/Valhalla-Coding/writeo-mcp/archive/refs/heads/main.zip"
    }
    function Find-Uvx {
        $cmd = Get-Command uvx -ErrorAction SilentlyContinue
        if ($cmd) { return $cmd.Source }
        foreach ($d in @($env:UV_INSTALL_DIR, $env:XDG_BIN_HOME, "$HOME\.local\bin", "$HOME\.cargo\bin")) {
            if ($d -and (Test-Path "$d\uvx.exe")) { return "$d\uvx.exe" }
        }
        return $null
    }
    $uvx = Find-Uvx
    if (-not $uvx) {
        Write-Host "Installing uv (the Python tool runner this needs)..."
        Invoke-RestMethod https://astral.sh/uv/install.ps1 | Invoke-Expression
        $uvx = Find-Uvx
        if (-not $uvx) { Write-Host "uv installed, but uvx was not found. Open a new terminal and run this again."; return }
    }
    & $uvx --from $env:WRITEO_MCP_SOURCE writeo-mcp-setup @args
}
Install-WriteoMcp @args
