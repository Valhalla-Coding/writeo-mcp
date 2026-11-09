#!/usr/bin/env sh
# macOS / Linux: curl -LsSf https://raw.githubusercontent.com/Valhalla-Coding/writeo-mcp/HEAD/install.sh | sh
# Extra options go after "-s --", e.g.  ... | sh -s -- --dry-run
set -eu
export WRITEO_MCP_SOURCE="${WRITEO_MCP_SOURCE:-https://github.com/Valhalla-Coding/writeo-mcp/archive/HEAD.zip}"

find_uvx() {
  command -v uvx && return 0
  for d in "${UV_INSTALL_DIR:-}" "${XDG_BIN_HOME:-}" "$HOME/.local/bin" "$HOME/.cargo/bin"; do
    [ -n "$d" ] && [ -x "$d/uvx" ] && { echo "$d/uvx"; return 0; }
  done
  return 1
}

UVX=$(find_uvx || true)
if [ -z "$UVX" ]; then
  echo "Installing uv (the Python tool runner this needs)..."
  if command -v curl >/dev/null 2>&1; then curl -LsSf https://astral.sh/uv/install.sh | sh
  else wget -qO- https://astral.sh/uv/install.sh | sh; fi
  UVX=$(find_uvx) || { echo "uv installed, but uvx was not found. Open a new terminal and run this again."; exit 1; }
fi

# When piped from curl, stdin is the script itself; read answers from the terminal instead.
if [ ! -t 0 ] && (: </dev/tty) 2>/dev/null; then exec </dev/tty; fi
exec "$UVX" --from "$WRITEO_MCP_SOURCE" writeo-mcp-setup "$@"
