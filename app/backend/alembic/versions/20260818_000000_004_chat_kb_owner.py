"""Chat rooms, prompt templates, and per-user knowledge-base ownership.

Revision ID: 004_chat_kb_owner
Revises: 003_project_phase_analysis
Create Date: 2026-08-18 00:00:00.000000
"""

from alembic import op

revision = "004_chat_kb_owner"
down_revision = "003_project_phase_analysis"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS chat_rooms (
            id UUID PRIMARY KEY,
            user_id UUID NOT NULL REFERENCES users(id),
            kind VARCHAR(32) NOT NULL,
            project_id UUID REFERENCES projects(id),
            title VARCHAR(255) NOT NULL DEFAULT 'ห้องใหม่',
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_chat_rooms_user_kind "
        "ON chat_rooms (user_id, kind, updated_at)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_chat_rooms_project ON chat_rooms (project_id)"
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS chat_messages (
            id UUID PRIMARY KEY,
            room_id UUID NOT NULL REFERENCES chat_rooms(id) ON DELETE CASCADE,
            role VARCHAR(20) NOT NULL,
            content TEXT NOT NULL DEFAULT '',
            citations JSONB NOT NULL DEFAULT '[]'::jsonb,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_chat_messages_room "
        "ON chat_messages (room_id, created_at)"
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS chat_prompt_templates (
            id UUID PRIMARY KEY,
            kind VARCHAR(32) NOT NULL,
            title VARCHAR(255) NOT NULL,
            body TEXT NOT NULL,
            sort_order INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    op.execute(
        "ALTER TABLE knowledge_base_documents "
        "ADD COLUMN IF NOT EXISTS owner_id UUID REFERENCES users(id)"
    )
    op.execute(
        "ALTER TABLE knowledge_base_documents "
        "ADD COLUMN IF NOT EXISTS mongo_gridfs_id VARCHAR(64)"
    )
    op.execute(
        "ALTER TABLE knowledge_base_documents "
        "ADD COLUMN IF NOT EXISTS scope VARCHAR(20) NOT NULL DEFAULT 'baseline'"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_kb_documents_owner "
        "ON knowledge_base_documents (owner_id)"
    )
    op.execute(
        """
        INSERT INTO chat_prompt_templates (id, kind, title, body, sort_order)
        VALUES
        (
            'a1e1e1e1-0001-4000-8000-000000000001'::uuid, 'kb',
            'คุณสมบัติผู้เสนอราคา',
            'ถามจาก พ.ร.บ. การจัดซื้อจัดจ้างฯ พ.ศ. 2560 และกฎกระทรวงว่าผู้เสนอราคาต้องมีคุณสมบัติอะไรบ้าง อ้างมาตรา/ข้อให้ชัด',
            1
        ),
        (
            'a1e1e1e1-0001-4000-8000-000000000002'::uuid, 'kb',
            'งวดงานและการจ่ายเงิน',
            'ดึงหลักเกณฑ์งวดจ่ายจากระเบียบกระทรวงการคลังและคู่มือแนวปฏิบัติ แล้วสรุปเป็นข้อที่อ้างแหล่งได้',
            2
        ),
        (
            'a1e1e1e1-0001-4000-8000-000000000003'::uuid, 'kb',
            'อัตราค่าปรับ',
            'อัตราค่าปรับงานจ้างตามระเบียบการจัดซื้อจัดจ้างภาครัฐคืออะไร อ้างข้อและเอกสารต้นฉบับ',
            3
        ),
        (
            'a1e1e1e1-0001-4000-8000-000000000004'::uuid, 'kb',
            'ราคากลาง',
            'อธิบายหลักการราคากลางที่เกี่ยวข้องกับการจัดทำ TOR พร้อมอ้างหนังสือกรมบัญชีกลางหรือระเบียบ',
            4
        ),
        (
            'a1e1e1e1-0002-4000-8000-000000000001'::uuid, 'draft_intake',
            'แกะเอกสารทั้งหมด',
            'แกะเอกสารที่อัปโหลดทั้งหมด แล้วสรุปว่าแต่ละไฟล์เกี่ยวกับหมวด TOR ใด',
            1
        ),
        (
            'a1e1e1e1-0002-4000-8000-000000000002'::uuid, 'draft_intake',
            'จัดเข้า 13 หมวด',
            'จัดเนื้อหาเข้าช่อง s1–s13 และ s4.1–s4.14 แล้วแสดงตารางความครบถ้วน',
            2
        ),
        (
            'a1e1e1e1-0002-4000-8000-000000000003'::uuid, 'draft_intake',
            'หมวดไหนยังขาด',
            'หมวดไหนยังขาดข้อมูลข้อเท็จจริงของโครงการนี้ ถามกลับทีละช่อง',
            3
        ),
        (
            'a1e1e1e1-0002-4000-8000-000000000004'::uuid, 'draft_intake',
            'ดึงมาตรฐานงวดจ่าย',
            'ดึงมาตรฐานงวดจ่ายจากระเบียบมาใส่เป็น Reference ของหมวด s8 โดยอ้างแหล่ง ไม่สวมเป็นข้อเท็จจริงโครงการ',
            4
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS chat_prompt_templates")
    op.execute("DROP TABLE IF EXISTS chat_messages")
    op.execute("DROP TABLE IF EXISTS chat_rooms")
    op.execute("ALTER TABLE knowledge_base_documents DROP COLUMN IF EXISTS owner_id")
    op.execute(
        "ALTER TABLE knowledge_base_documents DROP COLUMN IF EXISTS mongo_gridfs_id"
    )
    op.execute("ALTER TABLE knowledge_base_documents DROP COLUMN IF EXISTS scope")
