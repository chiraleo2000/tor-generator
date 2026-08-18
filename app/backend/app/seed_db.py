"""Seed demo users, published templates, and a sample project.

Usage (from app/backend/): python -m app.seed_db
"""

from __future__ import annotations

import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.domain.tor_sections import SCOPE_SUBSECTIONS, TOR_SECTION_LABELS
from app.models.project import Project
from app.models.template import Template
from app.models.user import User
from app.services.auth_service import AuthService

DEMO_PASSWORD = "Passw0rd!"

INDUSTRIES = [
    ("แม่แบบงานระบบสารสนเทศ", "it"),
    ("แม่แบบงานก่อสร้าง", "construction"),
    ("แม่แบบงานจ้างที่ปรึกษา", "consulting"),
    ("แม่แบบจัดซื้อจัดจ้างทั่วไป", "general"),
]


def _structure() -> dict:
    return {
        "sections": [
            {"key": key, "title": title} for key, title in TOR_SECTION_LABELS.items()
        ],
        "scope_subsections": [
            {"key": key, "title": title} for key, title in SCOPE_SUBSECTIONS.items()
        ],
    }


def _guidance(industry: str) -> dict:
    return {
        "s1": f"อธิบายความเป็นมาของงานประเภท {industry} ตามภารกิจหน่วยงาน",
        "s2": "ระบุวัตถุประสงค์แบบ SMART",
        "s4": "กรอกขอบเขตงาน 14 หัวข้อย่อยให้ครบ",
        "s6": "ระบุวงเงินและที่มาของงบประมาณ",
    }


async def seed() -> None:
    settings = get_settings()
    engine = create_async_engine(settings.database_url, pool_size=5)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as db:
        users = {
            "admin": ("ผู้ดูแลระบบ", "admin@example.go.th", "admin"),
            "officer": ("เจ้าหน้าที่พัสดุ", "officer@example.go.th", "officer"),
            "reviewer": ("ผู้ตรวจสอบ", "reviewer@example.go.th", "reviewer"),
        }
        created: dict[str, User] = {}
        for key, (name, email, role) in users.items():
            existing = (
                await db.execute(select(User).where(User.email == email))
            ).scalar_one_or_none()
            if existing:
                created[key] = existing
                print(f"user exists: {email}")
                continue
            user = User(
                name=name,
                email=email,
                password_hash=AuthService.hash_password(DEMO_PASSWORD),
                organization="หน่วยงานสาธิต",
                role=role,
            )
            db.add(user)
            await db.flush()
            created[key] = user
            print(f"created user: {email}")

        admin = created["admin"]
        for name, industry in INDUSTRIES:
            existing = (
                await db.execute(select(Template).where(Template.name == name))
            ).scalar_one_or_none()
            if existing:
                print(f"template exists: {name}")
                continue
            template = Template(
                name=name,
                industry=industry,
                status="published",
                section_structure=_structure(),
                placeholder_guidance=_guidance(industry),
                created_by=admin.id,
            )
            db.add(template)
            print(f"created template: {name}")

        await db.flush()
        officer = created["officer"]
        sample_name = "โครงการตัวอย่างพัฒนาระบบสารสนเทศ"
        existing_project = (
            await db.execute(select(Project).where(Project.name == sample_name))
        ).scalar_one_or_none()
        if not existing_project:
            it_template = (
                await db.execute(select(Template).where(Template.industry == "it"))
            ).scalar_one_or_none()
            db.add(
                Project(
                    owner_id=officer.id,
                    name=sample_name,
                    ministry="กระทรวงดิจิทัลเพื่อเศรษฐกิจและสังคม",
                    budget=5_000_000,
                    project_type="it",
                    status="draft",
                    current_step=1,
                    template_id=it_template.id if it_template else None,
                )
            )
            print("created sample project")
        await db.commit()
    await engine.dispose()
    print("seed_db complete")


if __name__ == "__main__":
    asyncio.run(seed())
