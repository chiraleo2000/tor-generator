"""App-level FastAPI configuration used by the Next.js rewrite proxy."""

from app.main import app


def test_redirect_slashes_disabled_so_post_projects_keeps_the_body():
    """Next.js rewrites POST /api/v1/projects; a 307 to /projects/ drops the body."""
    assert app.router.redirect_slashes is False
