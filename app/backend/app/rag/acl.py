"""Visibility rules for knowledge-base documents and RAG chunks."""

from __future__ import annotations

from uuid import UUID


def document_is_visible(
    *,
    document_owner_id: UUID | str | None,
    viewer_id: UUID | str | None,
    search_scope: str = "both",
) -> bool:
    """Return whether a viewer may see a document under the given RAG scope.

    Global (owner_id is None) documents are shared. User documents are visible
    only to that same user — never to another officer.
    """
    owner = str(document_owner_id) if document_owner_id is not None else None
    viewer = str(viewer_id) if viewer_id is not None else None
    if search_scope == "global":
        return owner is None
    if search_scope == "mine":
        return owner is not None and viewer is not None and owner == viewer
    if owner is None:
        return True
    return viewer is not None and owner == viewer
