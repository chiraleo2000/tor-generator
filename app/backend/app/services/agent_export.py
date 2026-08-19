"""Persist agent drafts to TOR sections and trigger the existing export pipeline."""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import select

from app import infra as runtime
from app.domain.tor_sections import TOR_SECTION_ORDER
from app.models.project import Project
from app.models.project_version import ProjectVersion
from app.models.tor_section import TORSection
from app.orchestrator.agent_state import AgentWorkflowState
from app.services.intake_service import apply_slot_map_to_sections

logger = logging.getLogger("tor_app.agent_export")


async def persist_and_export(state: AgentWorkflowState) -> dict[str, str | None]:
    if runtime.session_factory is None:
        return {"docx": None, "pdf": None}
    project_id = UUID(str(state["project_id"]))
    drafts = state.get("section_drafts") or {}
    async with runtime.session_factory() as db:
        project = (
            await db.execute(select(Project).where(Project.id == project_id))
        ).scalar_one_or_none()
        if project is None:
            raise ValueError("ไม่พบโครงการ")
        await apply_slot_map_to_sections(db, project_id, state.get("slot_map") or {})
        for key in TOR_SECTION_ORDER:
            text = str(drafts.get(key) or "").strip()
            if not text:
                continue
            row = (
                await db.execute(
                    select(TORSection).where(
                        TORSection.project_id == project_id,
                        TORSection.section_key == key,
                        TORSection.sub_key.is_(None),
                    )
                )
            ).scalar_one_or_none()
            if row is None:
                db.add(
                    TORSection(
                        project_id=project_id,
                        section_key=key,
                        content=text,
                        ai_draft=text,
                        quality_score=(state.get("draft_quality_scores") or {}).get(key),
                    )
                )
            else:
                row.content = text
                row.ai_draft = text
        versions = (
            await db.execute(
                select(ProjectVersion).where(ProjectVersion.project_id == project_id)
            )
        ).scalars().all()
        next_number = max((row.version_number for row in versions), default=0) + 1
        db.add(
            ProjectVersion(
                project_id=project_id,
                version_number=next_number,
                snapshot_data={"section_drafts": drafts, "slot_map": state.get("slot_map")},
                step_number=0,
            )
        )
        await db.commit()
        await db.refresh(project)
        urls = await _trigger_export(db, project)
    return urls


async def _trigger_export(db, project: Project) -> dict[str, str | None]:
    from app.services.export_service import ExportService

    if runtime.minio_client is None:
        logger.warning("MinIO unavailable; export URLs omitted")
        return {"docx": None, "pdf": None}
    job = await ExportService.trigger_export(
        db, runtime.minio_client, project, session_factory=runtime.session_factory
    )
    docx_url = None
    pdf_url = None
    for info in job.files or []:
        fmt = getattr(info, "format", None) or getattr(info, "filename", "")
        url = getattr(info, "download_url", None)
        if "pdf" in str(fmt):
            pdf_url = url
        else:
            docx_url = url
    return {"docx": docx_url, "pdf": pdf_url}
