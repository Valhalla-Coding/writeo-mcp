from . import deps, loginpage


def register(mcp):
    @mcp.tool()
    def writeo_login() -> dict:
        """Start a one-time sign-in. Returns a local link for the user to open in their own browser and
        enter their Writeo email and password there. Never ask the user to type a password into chat."""
        url = loginpage.start(deps.auth)
        return {"open_this_link": url, "note": "Link works on this computer only and closes after sign-in or 5 minutes."}

    @mcp.tool()
    def writeo_status() -> dict:
        """Who is signed in, and which novel is currently selected."""
        return {**deps.auth.status(), "selected_novel_id": deps.state.novel_id}
