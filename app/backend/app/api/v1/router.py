"""Main API v1 router.

Aggregates all endpoint sub-routers under the /api/v1 prefix.
Sub-routers are stubs that will be implemented in later tasks.
"""
from fastapi import APIRouter

from app.api.constants import PROJECTS_PREFIX
from app.api.v1.endpoints import (
    admin_ai_settings,
    admin_users,
    agent,
    ai_queue,
    auth,
    chat,
    draft_chat,
    drafting,
    export,
    files,
    health,
    intake,
    kb_chat,
    knowledge_base,
    projects,
    review,
    standalone_review,
    templates,
    wizard,
)

# ---------------------------------------------------------------------------
# Stub routers for endpoints to be implemented in later tasks
# ---------------------------------------------------------------------------
auth_router = APIRouter(prefix="/auth", tags=["auth"])
auth_router.include_router(auth.router)
wizard_router = APIRouter(prefix=PROJECTS_PREFIX, tags=["wizard"])
wizard_router.include_router(wizard.router)
drafting_router = APIRouter(prefix=PROJECTS_PREFIX, tags=["drafting"])
drafting_router.include_router(drafting.router)
drafting_router.include_router(intake.router)
drafting_router.include_router(draft_chat.router)
review_router = APIRouter(prefix=PROJECTS_PREFIX, tags=["review"])
review_router.include_router(review.router)
export_router = APIRouter(prefix=PROJECTS_PREFIX, tags=["export"])
export_router.include_router(export.router)
files_router = APIRouter(prefix="/files", tags=["files"])
files_router.include_router(files.router)
# ---------------------------------------------------------------------------
# Main v1 router — includes all sub-routers
# ---------------------------------------------------------------------------
api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router)
api_router.include_router(auth_router)
api_router.include_router(projects.router, prefix=PROJECTS_PREFIX, tags=["projects"])
api_router.include_router(wizard_router)
api_router.include_router(drafting_router)
api_router.include_router(review_router)
api_router.include_router(templates.router, prefix="/templates", tags=["templates"])
api_router.include_router(knowledge_base.router, prefix="/knowledge-base", tags=["knowledge-base"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(ai_queue.router, prefix="/ai", tags=["ai-queue"])
api_router.include_router(agent.router, prefix="/agent", tags=["agent"])
api_router.include_router(kb_chat.router, prefix="/kb-chat", tags=["kb-chat"])
api_router.include_router(export_router)
api_router.include_router(files_router)
api_router.include_router(admin_users.router, prefix="/admin/users", tags=["admin-users"])
api_router.include_router(
    admin_ai_settings.router, prefix="/admin/ai-settings", tags=["admin-ai-settings"]
)
api_router.include_router(standalone_review.router, prefix="/review", tags=["standalone-review"])


