"""Entry point: `writeo-mcp` (stdio MCP server)."""
from mcp.server.fastmcp import FastMCP

from . import tools_boards, tools_chapters, tools_characters, tools_notes, tools_novels, tools_profiles, tools_relations, tools_session

mcp = FastMCP("writeo")
for module in (tools_session, tools_novels, tools_chapters, tools_characters, tools_notes, tools_boards, tools_relations, tools_profiles):
    module.register(mcp)


def main():
    mcp.run()


if __name__ == "__main__":
    main()
