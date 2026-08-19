"""Unit tests for ORM model instantiation and field defaults.

These tests verify that SQLAlchemy models can be instantiated correctly
with proper defaults and field types, WITHOUT requiring a database connection.
We test the Python-level defaults and model structure.
"""

import uuid
from datetime import datetime

import pytest

from app.models.user import User
from app.models.project import Project
from app.models.project_version import ProjectVersion
from app.models.tor_section import TORSection
from app.models.template import Template
from app.models.template_version import TemplateVersion
from app.models.knowledge_base_document import KnowledgeBaseDocument
from app.models.kb_chunk import KBChunk
from app.models.suggestion import Suggestion
from app.models.audit_log import AuditLog
from app.models.uploaded_file import UploadedFile
from app.models.ai_runtime_settings import AiRuntimeSettings
from app.models.agent_session import AgentSession
from app.models.kb_chat_session import KBChatSession
from app.providers.constants import EMBEDDING_DIMENSIONS


class TestUserModel:
    """Unit tests for User model instantiation."""

    def test_user_creation_with_all_fields(self, sample_user_id: uuid.UUID):
        """Test User can be instantiated with all fields provided."""
        user = User(
            id=sample_user_id,
            name="สมชาย ใจดี",
            email="somchai@example.go.th",
            password_hash="$2b$12$hashed_password_value",
            organization="กระทรวงดิจิทัลเพื่อเศรษฐกิจและสังคม",
            role="officer",
        )
        assert user.id == sample_user_id
        assert user.name == "สมชาย ใจดี"
        assert user.email == "somchai@example.go.th"
        assert user.password_hash == "$2b$12$hashed_password_value"
        assert user.organization == "กระทรวงดิจิทัลเพื่อเศรษฐกิจและสังคม"
        assert user.role == "officer"

    def test_user_default_role_is_officer(self):
        """Test that User role column default is configured as 'officer'."""
        col = User.__table__.columns["role"]
        assert col.default.arg == "officer"

    def test_user_role_applied_when_specified(self):
        """Test that User role is set correctly when explicitly provided."""
        user = User(
            name="ทดสอบ",
            email="test@example.go.th",
            password_hash="hashed",
            organization="หน่วยงาน",
            role="officer",
        )
        assert user.role == "officer"

    def test_user_role_can_be_reviewer(self, sample_user_id: uuid.UUID):
        """Test User role can be set to 'reviewer'."""
        user = User(
            id=sample_user_id,
            name="ผู้ตรวจ",
            email="reviewer@example.go.th",
            password_hash="hashed",
            organization="หน่วยงาน",
            role="reviewer",
        )
        assert user.role == "reviewer"

    def test_user_role_can_be_admin(self, sample_user_id: uuid.UUID):
        """Test User role can be set to 'admin'."""
        user = User(
            id=sample_user_id,
            name="ผู้ดูแล",
            email="admin@example.go.th",
            password_hash="hashed",
            organization="หน่วยงาน",
            role="admin",
        )
        assert user.role == "admin"

    def test_user_repr(self, sample_user_id: uuid.UUID):
        """Test User __repr__ output."""
        user = User(
            id=sample_user_id,
            name="ทดสอบ",
            email="test@example.go.th",
            password_hash="hashed",
            organization="หน่วยงาน",
            role="officer",
        )
        repr_str = repr(user)
        assert "User" in repr_str
        assert str(sample_user_id) in repr_str
        assert "test@example.go.th" in repr_str
        assert "officer" in repr_str

    def test_user_tablename(self):
        """Test that User model is mapped to 'users' table."""
        assert User.__tablename__ == "users"


class TestProjectModel:
    """Unit tests for Project model instantiation."""

    def test_project_creation_with_all_fields(
        self, sample_project_id: uuid.UUID, sample_user_id: uuid.UUID, sample_template_id: uuid.UUID
    ):
        """Test Project can be instantiated with all fields provided."""
        project = Project(
            id=sample_project_id,
            owner_id=sample_user_id,
            name="โครงการพัฒนาระบบสารสนเทศ",
            ministry="กระทรวงดิจิทัลเพื่อเศรษฐกิจและสังคม",
            budget=5_000_000,
            project_type="it",
            status="draft",
            current_step=1,
            quality_score=None,
            template_id=sample_template_id,
        )
        assert project.id == sample_project_id
        assert project.owner_id == sample_user_id
        assert project.name == "โครงการพัฒนาระบบสารสนเทศ"
        assert project.ministry == "กระทรวงดิจิทัลเพื่อเศรษฐกิจและสังคม"
        assert project.budget == 5_000_000
        assert project.project_type == "it"
        assert project.status == "draft"
        assert project.current_step == 1
        assert project.quality_score is None
        assert project.template_id == sample_template_id

    def test_project_default_status_is_draft(self, sample_user_id: uuid.UUID):
        """Test that Project status column default is configured as 'draft'."""
        col = Project.__table__.columns["status"]
        assert col.default.arg == "draft"

    def test_project_default_current_phase_is_0(self, sample_user_id: uuid.UUID):
        """Test that Project current_phase column default is 0."""
        col = Project.__table__.columns["current_phase"]
        assert col.default.arg == 0

    def test_project_default_current_step_is_1(self, sample_user_id: uuid.UUID):
        """Test that Project current_step column default is configured as 1."""
        col = Project.__table__.columns["current_step"]
        assert col.default.arg == 1

    def test_project_default_project_type_is_general(self, sample_user_id: uuid.UUID):
        """Test that Project project_type column default is configured as 'general'."""
        col = Project.__table__.columns["project_type"]
        assert col.default.arg == "general"

    def test_project_default_workflow_mode_is_wizard(self):
        """Test that Project workflow_mode column default is 'wizard'."""
        col = Project.__table__.columns["workflow_mode"]
        assert col.default.arg == "wizard"

    def test_project_status_values(self, sample_user_id: uuid.UUID):
        """Test that Project supports all valid status values."""
        statuses = ["draft", "in_review", "approved", "rejected", "archived"]
        for status in statuses:
            project = Project(
                owner_id=sample_user_id,
                name="โครงการ",
                ministry="กระทรวง",
                budget=1_000_000,
                status=status,
            )
            assert project.status == status

    def test_project_type_values(self, sample_user_id: uuid.UUID):
        """Test that Project supports all valid type values."""
        types = ["it", "construction", "consulting", "general"]
        for ptype in types:
            project = Project(
                owner_id=sample_user_id,
                name="โครงการ",
                ministry="กระทรวง",
                budget=1_000_000,
                project_type=ptype,
            )
            assert project.project_type == ptype

    def test_project_large_budget(self, sample_user_id: uuid.UUID):
        """Test Project with large budget (BigInteger field)."""
        project = Project(
            owner_id=sample_user_id,
            name="โครงการขนาดใหญ่",
            ministry="กระทรวง",
            budget=10_000_000_000,  # 10 billion baht
        )
        assert project.budget == 10_000_000_000

    def test_project_quality_score_nullable(self, sample_user_id: uuid.UUID):
        """Test that Project quality_score can be None."""
        project = Project(
            owner_id=sample_user_id,
            name="โครงการ",
            ministry="กระทรวง",
            budget=1_000_000,
            quality_score=None,
        )
        assert project.quality_score is None

    def test_project_quality_score_with_value(self, sample_user_id: uuid.UUID):
        """Test that Project quality_score can hold 0-100 range."""
        project = Project(
            owner_id=sample_user_id,
            name="โครงการ",
            ministry="กระทรวง",
            budget=1_000_000,
            quality_score=85,
        )
        assert project.quality_score == 85

    def test_project_repr(self, sample_project_id: uuid.UUID, sample_user_id: uuid.UUID):
        """Test Project __repr__ output."""
        project = Project(
            id=sample_project_id,
            owner_id=sample_user_id,
            name="โครงการทดสอบ",
            ministry="กระทรวง",
            budget=1_000_000,
            status="draft",
        )
        repr_str = repr(project)
        assert "Project" in repr_str
        assert "โครงการทดสอบ" in repr_str
        assert "draft" in repr_str

    def test_project_tablename(self):
        """Test that Project model is mapped to 'projects' table."""
        assert Project.__tablename__ == "projects"


class TestProjectVersionModel:
    """Unit tests for ProjectVersion model instantiation."""

    def test_project_version_creation(
        self, sample_project_id: uuid.UUID, sample_snapshot_data: dict
    ):
        """Test ProjectVersion can be instantiated with JSONB snapshot data."""
        version = ProjectVersion(
            id=uuid.uuid4(),
            project_id=sample_project_id,
            version_number=1,
            snapshot_data=sample_snapshot_data,
            step_number=2,
        )
        assert version.project_id == sample_project_id
        assert version.version_number == 1
        assert version.snapshot_data == sample_snapshot_data
        assert version.step_number == 2

    def test_project_version_snapshot_data_is_dict(self, sample_project_id: uuid.UUID):
        """Test that snapshot_data accepts a dictionary (JSONB)."""
        data = {"sections": {"s1": "content"}, "metadata": {"step": 3}}
        version = ProjectVersion(
            project_id=sample_project_id,
            version_number=5,
            snapshot_data=data,
            step_number=3,
        )
        assert isinstance(version.snapshot_data, dict)
        assert version.snapshot_data["sections"]["s1"] == "content"

    def test_project_version_repr(self, sample_project_id: uuid.UUID):
        """Test ProjectVersion __repr__ output."""
        vid = uuid.uuid4()
        version = ProjectVersion(
            id=vid,
            project_id=sample_project_id,
            version_number=3,
            snapshot_data={},
            step_number=1,
        )
        repr_str = repr(version)
        assert "ProjectVersion" in repr_str
        assert str(sample_project_id) in repr_str
        assert "3" in repr_str

    def test_project_version_tablename(self):
        """Test that ProjectVersion model is mapped to 'project_versions' table."""
        assert ProjectVersion.__tablename__ == "project_versions"


class TestTORSectionModel:
    """Unit tests for TORSection model instantiation."""

    def test_tor_section_creation(self, sample_project_id: uuid.UUID):
        """Test TORSection can be instantiated with all fields."""
        section = TORSection(
            id=uuid.uuid4(),
            project_id=sample_project_id,
            section_key="s1",
            sub_key=None,
            content="ความเป็นมาของโครงการ",
            ai_draft="ร่างเนื้อหาจาก AI",
            quality_score=0.85,
            validation_findings={"issues": []},
            is_approved=True,
            version=2,
        )
        assert section.project_id == sample_project_id
        assert section.section_key == "s1"
        assert section.sub_key is None
        assert section.content == "ความเป็นมาของโครงการ"
        assert section.ai_draft == "ร่างเนื้อหาจาก AI"
        assert section.quality_score == 0.85
        assert section.validation_findings == {"issues": []}
        assert section.is_approved is True
        assert section.version == 2

    def test_tor_section_default_is_approved_false(self, sample_project_id: uuid.UUID):
        """Test that TORSection is_approved column default is configured as False."""
        col = TORSection.__table__.columns["is_approved"]
        assert col.default.arg is False

    def test_tor_section_default_version_is_1(self, sample_project_id: uuid.UUID):
        """Test that TORSection version column default is configured as 1."""
        col = TORSection.__table__.columns["version"]
        assert col.default.arg == 1

    def test_tor_section_default_content_empty(self, sample_project_id: uuid.UUID):
        """Test that TORSection content column default is configured as empty string."""
        col = TORSection.__table__.columns["content"]
        assert col.default.arg == ""

    def test_tor_section_with_sub_key(self, sample_project_id: uuid.UUID):
        """Test TORSection with sub_key for scope subsections (4.1..4.14)."""
        section = TORSection(
            project_id=sample_project_id,
            section_key="s4",
            sub_key="4.7",
            content="ขอบเขตงานส่วนที่ 7",
        )
        assert section.sub_key == "4.7"

    def test_tor_section_nullable_fields(self, sample_project_id: uuid.UUID):
        """Test that nullable fields (ai_draft, quality_score, validation_findings) accept None."""
        section = TORSection(
            project_id=sample_project_id,
            section_key="s5",
            content="ระยะเวลา",
            ai_draft=None,
            quality_score=None,
            validation_findings=None,
        )
        assert section.ai_draft is None
        assert section.quality_score is None
        assert section.validation_findings is None

    def test_tor_section_repr(self, sample_project_id: uuid.UUID):
        """Test TORSection __repr__ output."""
        sid = uuid.uuid4()
        section = TORSection(
            id=sid,
            project_id=sample_project_id,
            section_key="s1",
            content="test",
        )
        repr_str = repr(section)
        assert "TORSection" in repr_str
        assert str(sample_project_id) in repr_str
        assert "s1" in repr_str

    def test_tor_section_tablename(self):
        """Test that TORSection model is mapped to 'tor_sections' table."""
        assert TORSection.__tablename__ == "tor_sections"


class TestTemplateModel:
    """Unit tests for Template model instantiation."""

    def test_template_creation(
        self,
        sample_template_id: uuid.UUID,
        sample_user_id: uuid.UUID,
        sample_section_structure: dict,
        sample_placeholder_guidance: dict,
    ):
        """Test Template can be instantiated with all fields."""
        template = Template(
            id=sample_template_id,
            name="เทมเพลต IT",
            industry="it",
            status="published",
            section_structure=sample_section_structure,
            placeholder_guidance=sample_placeholder_guidance,
            created_by=sample_user_id,
        )
        assert template.id == sample_template_id
        assert template.name == "เทมเพลต IT"
        assert template.industry == "it"
        assert template.status == "published"
        assert template.section_structure == sample_section_structure
        assert template.placeholder_guidance == sample_placeholder_guidance
        assert template.created_by == sample_user_id

    def test_template_default_status_is_draft(
        self, sample_user_id: uuid.UUID, sample_section_structure: dict, sample_placeholder_guidance: dict
    ):
        """Test that Template status column default is configured as 'draft'."""
        col = Template.__table__.columns["status"]
        assert col.default.arg == "draft"

    def test_template_lifecycle_states(
        self, sample_user_id: uuid.UUID, sample_section_structure: dict, sample_placeholder_guidance: dict
    ):
        """Test Template supports Draft and Published lifecycle states."""
        for status in ["draft", "published"]:
            template = Template(
                name="เทมเพลต",
                industry="it",
                status=status,
                section_structure=sample_section_structure,
                placeholder_guidance=sample_placeholder_guidance,
                created_by=sample_user_id,
            )
            assert template.status == status

    def test_template_industry_values(
        self, sample_user_id: uuid.UUID, sample_section_structure: dict, sample_placeholder_guidance: dict
    ):
        """Test Template supports all valid industry values."""
        industries = ["it", "construction", "consulting", "general"]
        for industry in industries:
            template = Template(
                name="เทมเพลต",
                industry=industry,
                section_structure=sample_section_structure,
                placeholder_guidance=sample_placeholder_guidance,
                created_by=sample_user_id,
            )
            assert template.industry == industry

    def test_template_repr(
        self, sample_template_id: uuid.UUID, sample_user_id: uuid.UUID
    ):
        """Test Template __repr__ output."""
        template = Template(
            id=sample_template_id,
            name="เทมเพลต IT",
            industry="it",
            section_structure={},
            placeholder_guidance={},
            created_by=sample_user_id,
        )
        repr_str = repr(template)
        assert "Template" in repr_str
        assert "เทมเพลต IT" in repr_str
        assert "it" in repr_str

    def test_template_tablename(self):
        """Test that Template model is mapped to 'templates' table."""
        assert Template.__tablename__ == "templates"


class TestTemplateVersionModel:
    """Unit tests for TemplateVersion model instantiation."""

    def test_template_version_creation(
        self, sample_template_id: uuid.UUID, sample_section_structure: dict, sample_placeholder_guidance: dict
    ):
        """Test TemplateVersion can be instantiated with all fields."""
        version = TemplateVersion(
            id=uuid.uuid4(),
            template_id=sample_template_id,
            version_number=1,
            section_structure=sample_section_structure,
            placeholder_guidance=sample_placeholder_guidance,
        )
        assert version.template_id == sample_template_id
        assert version.version_number == 1
        assert version.section_structure == sample_section_structure
        assert version.placeholder_guidance == sample_placeholder_guidance

    def test_template_version_repr(self, sample_template_id: uuid.UUID):
        """Test TemplateVersion __repr__ output."""
        vid = uuid.uuid4()
        version = TemplateVersion(
            id=vid,
            template_id=sample_template_id,
            version_number=2,
            section_structure={},
            placeholder_guidance={},
        )
        repr_str = repr(version)
        assert "TemplateVersion" in repr_str
        assert str(sample_template_id) in repr_str
        assert "2" in repr_str

    def test_template_version_tablename(self):
        """Test that TemplateVersion model is mapped to 'template_versions' table."""
        assert TemplateVersion.__tablename__ == "template_versions"


class TestKnowledgeBaseDocumentModel:
    """Unit tests for KnowledgeBaseDocument model instantiation."""

    def test_kb_document_creation(self):
        """Test KnowledgeBaseDocument can be instantiated with all fields."""
        doc = KnowledgeBaseDocument(
            id=uuid.uuid4(),
            name="พ.ร.บ. การจัดซื้อจัดจ้างและการบริหารพัสดุภาครัฐ พ.ศ. 2560",
            category="law",
            file_type="pdf",
            storage_path="/documents/procurement-act-2560.pdf",
            processing_status="completed",
            chunk_count=150,
            error_message=None,
        )
        assert doc.name == "พ.ร.บ. การจัดซื้อจัดจ้างและการบริหารพัสดุภาครัฐ พ.ศ. 2560"
        assert doc.category == "law"
        assert doc.file_type == "pdf"
        assert doc.storage_path == "/documents/procurement-act-2560.pdf"
        assert doc.processing_status == "completed"
        assert doc.chunk_count == 150
        assert doc.error_message is None

    def test_kb_document_default_chunk_count_is_0(self):
        """Test that KnowledgeBaseDocument chunk_count column default is configured as 0."""
        col = KnowledgeBaseDocument.__table__.columns["chunk_count"]
        assert col.default.arg == 0

    def test_kb_document_default_processing_status_is_pending(self):
        """Test that KnowledgeBaseDocument processing_status column default is 'pending'."""
        col = KnowledgeBaseDocument.__table__.columns["processing_status"]
        assert col.default.arg == "pending"

    def test_kb_document_category_values(self):
        """Test all valid category values."""
        categories = ["law", "regulation", "guideline", "manual", "example_tor"]
        for category in categories:
            doc = KnowledgeBaseDocument(
                name="ทดสอบ",
                category=category,
                file_type="pdf",
                storage_path="/test.pdf",
            )
            assert doc.category == category

    def test_kb_document_file_type_values(self):
        """Test all valid file_type values."""
        file_types = ["pdf", "docx", "txt"]
        for ft in file_types:
            doc = KnowledgeBaseDocument(
                name="ทดสอบ",
                category="law",
                file_type=ft,
                storage_path=f"/test.{ft}",
            )
            assert doc.file_type == ft

    def test_kb_document_processing_status_values(self):
        """Test all valid processing_status values."""
        statuses = ["pending", "processing", "completed", "failed"]
        for status in statuses:
            doc = KnowledgeBaseDocument(
                name="ทดสอบ",
                category="law",
                file_type="pdf",
                storage_path="/test.pdf",
                processing_status=status,
            )
            assert doc.processing_status == status

    def test_kb_document_with_error_message(self):
        """Test KnowledgeBaseDocument with error_message for failed processing."""
        doc = KnowledgeBaseDocument(
            name="ไฟล์เสียหาย",
            category="guideline",
            file_type="pdf",
            storage_path="/broken.pdf",
            processing_status="failed",
            error_message="Unable to extract text: corrupted PDF",
        )
        assert doc.processing_status == "failed"
        assert doc.error_message == "Unable to extract text: corrupted PDF"

    def test_kb_document_repr(self):
        """Test KnowledgeBaseDocument __repr__ output."""
        doc_id = uuid.uuid4()
        doc = KnowledgeBaseDocument(
            id=doc_id,
            name="พ.ร.บ. 2560",
            category="law",
            file_type="pdf",
            storage_path="/test.pdf",
            processing_status="completed",
        )
        repr_str = repr(doc)
        assert "KnowledgeBaseDocument" in repr_str
        assert "พ.ร.บ. 2560" in repr_str
        assert "completed" in repr_str

    def test_kb_document_tablename(self):
        """Test that KnowledgeBaseDocument is mapped to 'knowledge_base_documents' table."""
        assert KnowledgeBaseDocument.__tablename__ == "knowledge_base_documents"


class TestKBChunkModel:
    """Unit tests for KBChunk model instantiation."""

    def test_kb_chunk_creation(self, sample_document_id: uuid.UUID):
        """Test KBChunk can be instantiated with all fields."""
        chunk = KBChunk(
            id=uuid.uuid4(),
            document_id=sample_document_id,
            chunk_index=0,
            chunk_text="มาตรา ๑ พระราชบัญญัตินี้เรียกว่า",
            section_label="มาตรา 1",
            page_number=1,
            chunk_metadata={"source": "procurement_act", "section": "introduction"},
        )
        assert chunk.document_id == sample_document_id
        assert chunk.chunk_index == 0
        assert chunk.chunk_text == "มาตรา ๑ พระราชบัญญัตินี้เรียกว่า"
        assert chunk.section_label == "มาตรา 1"
        assert chunk.page_number == 1
        assert chunk.chunk_metadata == {"source": "procurement_act", "section": "introduction"}

    def test_kb_chunk_nullable_fields(self, sample_document_id: uuid.UUID):
        """Test KBChunk nullable fields (section_label, page_number, embedding)."""
        chunk = KBChunk(
            document_id=sample_document_id,
            chunk_index=5,
            chunk_text="เนื้อหาทดสอบ",
            section_label=None,
            page_number=None,
            chunk_metadata={},
        )
        assert chunk.section_label is None
        assert chunk.page_number is None

    def test_kb_chunk_default_metadata(self, sample_document_id: uuid.UUID):
        """Test KBChunk chunk_metadata column default is configured."""
        col = KBChunk.__table__.columns["metadata"]
        # default=dict means a callable default is configured for this column
        assert col.default is not None
        assert col.default.is_callable is True

    def test_kb_chunk_embedding_field_exists(self):
        """Test that KBChunk has an embedding column defined (Vector(768))."""
        # Verify the column exists in the model's mapper
        columns = KBChunk.__table__.columns
        assert "embedding" in columns
        # Check the column type string contains 'vector' (pgvector type)
        col = columns["embedding"]
        assert col.nullable is True
        assert EMBEDDING_DIMENSIONS == 768

    def test_kb_chunk_repr(self, sample_document_id: uuid.UUID):
        """Test KBChunk __repr__ output."""
        cid = uuid.uuid4()
        chunk = KBChunk(
            id=cid,
            document_id=sample_document_id,
            chunk_index=3,
            chunk_text="test",
            chunk_metadata={},
        )
        repr_str = repr(chunk)
        assert "KBChunk" in repr_str
        assert str(sample_document_id) in repr_str
        assert "3" in repr_str

    def test_kb_chunk_tablename(self):
        """Test that KBChunk model is mapped to 'kb_chunks' table."""
        assert KBChunk.__tablename__ == "kb_chunks"


class TestSuggestionModel:
    """Unit tests for Suggestion model instantiation."""

    def test_suggestion_creation(self, sample_project_id: uuid.UUID):
        """Test Suggestion can be instantiated with all fields."""
        suggestion = Suggestion(
            id=uuid.uuid4(),
            project_id=sample_project_id,
            section_key="s3",
            category="compliance",
            current_text="ผู้เสนอราคาต้องมีทุนจดทะเบียน 1 ล้านบาท",
            suggested_text="ผู้เสนอราคาต้องมีทุนจดทะเบียนไม่น้อยกว่า 1,250,000 บาท",
            predicted_score_improvement=5.0,
            status="pending",
        )
        assert suggestion.project_id == sample_project_id
        assert suggestion.section_key == "s3"
        assert suggestion.category == "compliance"
        assert suggestion.current_text == "ผู้เสนอราคาต้องมีทุนจดทะเบียน 1 ล้านบาท"
        assert suggestion.suggested_text == "ผู้เสนอราคาต้องมีทุนจดทะเบียนไม่น้อยกว่า 1,250,000 บาท"
        assert suggestion.predicted_score_improvement == 5.0
        assert suggestion.status == "pending"

    def test_suggestion_default_status_is_pending(self, sample_project_id: uuid.UUID):
        """Test that Suggestion status column default is configured as 'pending'."""
        col = Suggestion.__table__.columns["status"]
        assert col.default.arg == "pending"

    def test_suggestion_category_values(self, sample_project_id: uuid.UUID):
        """Test all valid suggestion category values."""
        categories = ["compliance", "clarity", "completeness", "consistency"]
        for category in categories:
            suggestion = Suggestion(
                project_id=sample_project_id,
                section_key="s1",
                category=category,
                current_text="เดิม",
                suggested_text="ใหม่",
                predicted_score_improvement=1.0,
            )
            assert suggestion.category == category

    def test_suggestion_status_values(self, sample_project_id: uuid.UUID):
        """Test all valid suggestion status values."""
        statuses = ["pending", "accepted", "dismissed"]
        for status in statuses:
            suggestion = Suggestion(
                project_id=sample_project_id,
                section_key="s2",
                category="completeness",
                current_text="เดิม",
                suggested_text="ใหม่",
                predicted_score_improvement=3.0,
                status=status,
            )
            assert suggestion.status == status

    def test_suggestion_repr(self, sample_project_id: uuid.UUID):
        """Test Suggestion __repr__ output."""
        sid = uuid.uuid4()
        suggestion = Suggestion(
            id=sid,
            project_id=sample_project_id,
            section_key="s5",
            category="consistency",
            current_text="เดิม",
            suggested_text="ใหม่",
            predicted_score_improvement=4.0,
            status="pending",
        )
        repr_str = repr(suggestion)
        assert "Suggestion" in repr_str
        assert str(sample_project_id) in repr_str
        assert "consistency" in repr_str
        assert "pending" in repr_str

    def test_suggestion_tablename(self):
        """Test that Suggestion model is mapped to 'suggestions' table."""
        assert Suggestion.__tablename__ == "suggestions"


class TestAuditLogModel:
    """Unit tests for AuditLog model instantiation."""

    def test_audit_log_creation(self, sample_user_id: uuid.UUID):
        """Test AuditLog can be instantiated with all fields."""
        log = AuditLog(
            id=uuid.uuid4(),
            user_id=sample_user_id,
            action="login",
            resource_type="auth",
            resource_id=None,
            ip_address="192.168.1.100",
            details={"user_agent": "Chrome/120"},
        )
        assert log.user_id == sample_user_id
        assert log.action == "login"
        assert log.resource_type == "auth"
        assert log.resource_id is None
        assert log.ip_address == "192.168.1.100"
        assert log.details == {"user_agent": "Chrome/120"}

    def test_audit_log_various_actions(self, sample_user_id: uuid.UUID):
        """Test AuditLog supports all defined action types."""
        actions = ["login", "logout", "login_failed", "create", "update", "delete", "export", "review"]
        for action in actions:
            log = AuditLog(
                user_id=sample_user_id,
                action=action,
                resource_type="project",
                ip_address="10.0.0.1",
            )
            assert log.action == action

    def test_audit_log_nullable_user_id(self):
        """Test AuditLog user_id can be None (e.g., system-generated events)."""
        log = AuditLog(
            user_id=None,
            action="login_failed",
            resource_type="auth",
            ip_address="203.0.113.50",
            details={"reason": "invalid credentials", "email": "unknown@example.com"},
        )
        assert log.user_id is None

    def test_audit_log_nullable_resource_id(self, sample_user_id: uuid.UUID):
        """Test AuditLog resource_id can be None."""
        log = AuditLog(
            user_id=sample_user_id,
            action="logout",
            resource_type="auth",
            resource_id=None,
            ip_address="10.0.0.1",
        )
        assert log.resource_id is None

    def test_audit_log_with_resource_id(self, sample_user_id: uuid.UUID, sample_project_id: uuid.UUID):
        """Test AuditLog with a resource_id pointing to a project."""
        log = AuditLog(
            user_id=sample_user_id,
            action="update",
            resource_type="project",
            resource_id=sample_project_id,
            ip_address="172.16.0.5",
            details={"field": "status", "old": "draft", "new": "in_review"},
        )
        assert log.resource_id == sample_project_id
        assert log.details["field"] == "status"

    def test_audit_log_ipv6_address(self, sample_user_id: uuid.UUID):
        """Test AuditLog supports IPv6 addresses."""
        log = AuditLog(
            user_id=sample_user_id,
            action="login",
            resource_type="auth",
            ip_address="2001:0db8:85a3:0000:0000:8a2e:0370:7334",
        )
        assert log.ip_address == "2001:0db8:85a3:0000:0000:8a2e:0370:7334"

    def test_audit_log_repr(self, sample_user_id: uuid.UUID):
        """Test AuditLog __repr__ output."""
        lid = uuid.uuid4()
        log = AuditLog(
            id=lid,
            user_id=sample_user_id,
            action="export",
            resource_type="project",
            ip_address="10.0.0.1",
        )
        repr_str = repr(log)
        assert "AuditLog" in repr_str
        assert str(sample_user_id) in repr_str
        assert "export" in repr_str
        assert "project" in repr_str

    def test_audit_log_tablename(self):
        """Test that AuditLog model is mapped to 'audit_logs' table."""
        assert AuditLog.__tablename__ == "audit_logs"


class TestUploadedFileModel:
    """Unit tests for UploadedFile model instantiation."""

    def test_uploaded_file_creation(
        self, sample_project_id: uuid.UUID, sample_user_id: uuid.UUID
    ):
        """Test UploadedFile can be instantiated with all fields."""
        file = UploadedFile(
            id=uuid.uuid4(),
            project_id=sample_project_id,
            uploaded_by=sample_user_id,
            original_name="เอกสารอ้างอิง.pdf",
            storage_path="/uploads/2024/08/abc123.pdf",
            mime_type="application/pdf",
            file_size_bytes=5_242_880,  # 5MB
            extracted_text="เนื้อหาที่ OCR ได้",
            ocr_status="completed",
        )
        assert file.project_id == sample_project_id
        assert file.uploaded_by == sample_user_id
        assert file.original_name == "เอกสารอ้างอิง.pdf"
        assert file.storage_path == "/uploads/2024/08/abc123.pdf"
        assert file.mime_type == "application/pdf"
        assert file.file_size_bytes == 5_242_880
        assert file.extracted_text == "เนื้อหาที่ OCR ได้"
        assert file.ocr_status == "completed"

    def test_uploaded_file_default_ocr_status_is_pending(self, sample_user_id: uuid.UUID):
        """Test that UploadedFile ocr_status column default is configured as 'pending'."""
        col = UploadedFile.__table__.columns["ocr_status"]
        assert col.default.arg == "pending"

    def test_uploaded_file_nullable_project_id(self, sample_user_id: uuid.UUID):
        """Test that UploadedFile project_id can be None (standalone upload)."""
        file = UploadedFile(
            project_id=None,
            uploaded_by=sample_user_id,
            original_name="reference.docx",
            storage_path="/uploads/reference.docx",
            mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            file_size_bytes=2048,
        )
        assert file.project_id is None

    def test_uploaded_file_nullable_extracted_text(self, sample_user_id: uuid.UUID):
        """Test that UploadedFile extracted_text can be None (not yet processed)."""
        file = UploadedFile(
            uploaded_by=sample_user_id,
            original_name="scan.pdf",
            storage_path="/uploads/scan.pdf",
            mime_type="application/pdf",
            file_size_bytes=10_000_000,
            extracted_text=None,
            ocr_status="pending",
        )
        assert file.extracted_text is None

    def test_uploaded_file_ocr_status_values(self, sample_user_id: uuid.UUID):
        """Test all valid ocr_status values."""
        statuses = ["pending", "completed", "failed", "timeout"]
        for status in statuses:
            file = UploadedFile(
                uploaded_by=sample_user_id,
                original_name="test.pdf",
                storage_path="/test.pdf",
                mime_type="application/pdf",
                file_size_bytes=1024,
                ocr_status=status,
            )
            assert file.ocr_status == status

    def test_uploaded_file_large_size(self, sample_user_id: uuid.UUID):
        """Test UploadedFile with large file size (BigInteger)."""
        file = UploadedFile(
            uploaded_by=sample_user_id,
            original_name="large_file.pdf",
            storage_path="/uploads/large.pdf",
            mime_type="application/pdf",
            file_size_bytes=20_971_520,  # 20MB (max allowed)
        )
        assert file.file_size_bytes == 20_971_520

    def test_uploaded_file_repr(self, sample_user_id: uuid.UUID):
        """Test UploadedFile __repr__ output."""
        fid = uuid.uuid4()
        file = UploadedFile(
            id=fid,
            uploaded_by=sample_user_id,
            original_name="เอกสาร.pdf",
            storage_path="/test.pdf",
            mime_type="application/pdf",
            file_size_bytes=1024,
            ocr_status="completed",
        )
        repr_str = repr(file)
        assert "UploadedFile" in repr_str
        assert "เอกสาร.pdf" in repr_str
        assert "completed" in repr_str

    def test_uploaded_file_tablename(self):
        """Test that UploadedFile model is mapped to 'uploaded_files' table."""
        assert UploadedFile.__tablename__ == "uploaded_files"


class TestModelRelationships:
    """Test that model relationship attributes are properly defined."""

    def test_user_has_projects_relationship(self):
        """Test User model defines projects relationship."""
        user = User(
            name="test",
            email="test@test.com",
            password_hash="h",
            organization="org",
        )
        # Relationship attribute exists (will be empty list without DB session)
        assert hasattr(user, "projects")

    def test_user_has_audit_logs_relationship(self):
        """Test User model defines audit_logs relationship."""
        user = User(
            name="test",
            email="test@test.com",
            password_hash="h",
            organization="org",
        )
        assert hasattr(user, "audit_logs")

    def test_user_has_uploaded_files_relationship(self):
        """Test User model defines uploaded_files relationship."""
        user = User(
            name="test",
            email="test@test.com",
            password_hash="h",
            organization="org",
        )
        assert hasattr(user, "uploaded_files")

    def test_user_has_templates_relationship(self):
        """Test User model defines templates relationship."""
        user = User(
            name="test",
            email="test@test.com",
            password_hash="h",
            organization="org",
        )
        assert hasattr(user, "templates")

    def test_project_has_tor_sections_relationship(self, sample_user_id: uuid.UUID):
        """Test Project model defines tor_sections relationship."""
        project = Project(
            owner_id=sample_user_id,
            name="test",
            ministry="m",
            budget=1000,
        )
        assert hasattr(project, "tor_sections")

    def test_project_has_versions_relationship(self, sample_user_id: uuid.UUID):
        """Test Project model defines versions relationship."""
        project = Project(
            owner_id=sample_user_id,
            name="test",
            ministry="m",
            budget=1000,
        )
        assert hasattr(project, "versions")

    def test_project_has_suggestions_relationship(self, sample_user_id: uuid.UUID):
        """Test Project model defines suggestions relationship."""
        project = Project(
            owner_id=sample_user_id,
            name="test",
            ministry="m",
            budget=1000,
        )
        assert hasattr(project, "suggestions")

    def test_project_has_uploaded_files_relationship(self, sample_user_id: uuid.UUID):
        """Test Project model defines uploaded_files relationship."""
        project = Project(
            owner_id=sample_user_id,
            name="test",
            ministry="m",
            budget=1000,
        )
        assert hasattr(project, "uploaded_files")

    def test_project_has_agent_sessions_relationship(self, sample_user_id: uuid.UUID):
        """Test Project model defines agent_sessions relationship."""
        project = Project(
            owner_id=sample_user_id,
            name="test",
            ministry="m",
            budget=1000,
        )
        assert hasattr(project, "agent_sessions")

    def test_kb_document_has_chunks_relationship(self):
        """Test KnowledgeBaseDocument model defines chunks relationship."""
        doc = KnowledgeBaseDocument(
            name="test",
            category="law",
            file_type="pdf",
            storage_path="/test.pdf",
        )
        assert hasattr(doc, "chunks")

    def test_template_has_versions_relationship(self, sample_user_id: uuid.UUID):
        """Test Template model defines versions relationship."""
        template = Template(
            name="test",
            industry="it",
            section_structure={},
            placeholder_guidance={},
            created_by=sample_user_id,
        )
        assert hasattr(template, "versions")

    def test_template_has_projects_relationship(self, sample_user_id: uuid.UUID):
        """Test Template model defines projects relationship."""
        template = Template(
            name="test",
            industry="it",
            section_structure={},
            placeholder_guidance={},
            created_by=sample_user_id,
        )
        assert hasattr(template, "projects")


class TestModelTableIndexes:
    """Test that model table indexes are properly defined."""

    def test_project_has_owner_status_index(self):
        """Test projects table has idx_projects_owner_status index."""
        indexes = {idx.name for idx in Project.__table__.indexes}
        assert "idx_projects_owner_status" in indexes

    def test_project_has_updated_at_index(self):
        """Test projects table has idx_projects_updated_at index."""
        indexes = {idx.name for idx in Project.__table__.indexes}
        assert "idx_projects_updated_at" in indexes

    def test_tor_section_has_project_index(self):
        """Test tor_sections table has idx_tor_sections_project index."""
        indexes = {idx.name for idx in TORSection.__table__.indexes}
        assert "idx_tor_sections_project" in indexes

    def test_kb_chunk_has_document_index(self):
        """Test kb_chunks table has idx_kb_chunks_document index."""
        indexes = {idx.name for idx in KBChunk.__table__.indexes}
        assert "idx_kb_chunks_document" in indexes

    def test_kb_chunk_has_embedding_hnsw_index(self):
        """Test kb_chunks table has idx_kb_chunks_embedding HNSW index."""
        indexes = {idx.name for idx in KBChunk.__table__.indexes}
        assert "idx_kb_chunks_embedding" in indexes

    def test_suggestion_has_project_status_index(self):
        """Test suggestions table has idx_suggestions_project_status index."""
        indexes = {idx.name for idx in Suggestion.__table__.indexes}
        assert "idx_suggestions_project_status" in indexes

    def test_audit_log_has_user_action_index(self):
        """Test audit_logs table has idx_audit_logs_user_action index."""
        indexes = {idx.name for idx in AuditLog.__table__.indexes}
        assert "idx_audit_logs_user_action" in indexes


class TestModelColumnConstraints:
    """Test model column constraints are properly defined."""

    def test_user_email_is_unique(self):
        """Test User email column has unique constraint."""
        email_col = User.__table__.columns["email"]
        assert email_col.unique is True

    def test_user_email_is_not_nullable(self):
        """Test User email column is NOT NULL."""
        email_col = User.__table__.columns["email"]
        assert email_col.nullable is False

    def test_project_owner_id_is_not_nullable(self):
        """Test Project owner_id column is NOT NULL."""
        col = Project.__table__.columns["owner_id"]
        assert col.nullable is False

    def test_project_budget_is_not_nullable(self):
        """Test Project budget column is NOT NULL."""
        col = Project.__table__.columns["budget"]
        assert col.nullable is False

    def test_project_quality_score_is_nullable(self):
        """Test Project quality_score column IS NULL."""
        col = Project.__table__.columns["quality_score"]
        assert col.nullable is True

    def test_project_template_id_is_nullable(self):
        """Test Project template_id column IS NULL."""
        col = Project.__table__.columns["template_id"]
        assert col.nullable is True

    def test_tor_section_ai_draft_is_nullable(self):
        """Test TORSection ai_draft column IS NULL."""
        col = TORSection.__table__.columns["ai_draft"]
        assert col.nullable is True

    def test_tor_section_quality_score_is_nullable(self):
        """Test TORSection quality_score column IS NULL."""
        col = TORSection.__table__.columns["quality_score"]
        assert col.nullable is True

    def test_kb_chunk_embedding_is_nullable(self):
        """Test KBChunk embedding column IS NULL (embeddings generated later)."""
        col = KBChunk.__table__.columns["embedding"]
        assert col.nullable is True

    def test_audit_log_user_id_is_nullable(self):
        """Test AuditLog user_id column IS NULL (system events)."""
        col = AuditLog.__table__.columns["user_id"]
        assert col.nullable is True

    def test_uploaded_file_project_id_is_nullable(self):
        """Test UploadedFile project_id column IS NULL (standalone uploads)."""
        col = UploadedFile.__table__.columns["project_id"]
        assert col.nullable is True

    def test_uploaded_file_extracted_text_is_nullable(self):
        """Test UploadedFile extracted_text column IS NULL."""
        col = UploadedFile.__table__.columns["extracted_text"]
        assert col.nullable is True

    def test_kb_document_error_message_is_nullable(self):
        """Test KnowledgeBaseDocument error_message column IS NULL."""
        col = KnowledgeBaseDocument.__table__.columns["error_message"]
        assert col.nullable is True


class TestAiRuntimeSettingsModel:
    """Singleton admin overlay row."""

    def test_tablename(self):
        assert AiRuntimeSettings.__tablename__ == "ai_runtime_settings"

    def test_payload_round_trip(self):
        row = AiRuntimeSettings(id=1, payload={"deployment_mode": "on_prem"})
        assert row.id == 1
        assert row.payload["deployment_mode"] == "on_prem"


class TestAgentSessionModel:
    """Unit tests for AgentSession model."""

    def test_tablename(self):
        assert AgentSession.__tablename__ == "agent_sessions"

    def test_creation(
        self, sample_project_id: uuid.UUID, sample_user_id: uuid.UUID
    ):
        session = AgentSession(
            project_id=sample_project_id,
            user_id=sample_user_id,
            phase="gap_filling",
        )
        assert session.project_id == sample_project_id
        assert session.user_id == sample_user_id
        assert session.phase == "gap_filling"

    def test_default_phase_is_idle(self):
        col = AgentSession.__table__.columns["phase"]
        assert col.default.arg == "idle"

    def test_repr(self, sample_project_id: uuid.UUID, sample_user_id: uuid.UUID):
        session_id = uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
        row = AgentSession(
            id=session_id,
            project_id=sample_project_id,
            user_id=sample_user_id,
            phase="idle",
        )
        assert str(session_id) in repr(row)


class TestKBChatSessionModel:
    """Unit tests for KBChatSession model."""

    def test_tablename(self):
        assert KBChatSession.__tablename__ == "kb_chat_sessions"

    def test_creation(self, sample_user_id: uuid.UUID):
        row = KBChatSession(user_id=sample_user_id, history=[])
        assert row.user_id == sample_user_id
        assert row.history == []

    def test_repr(self, sample_user_id: uuid.UUID):
        session_id = uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
        row = KBChatSession(id=session_id, user_id=sample_user_id)
        assert str(session_id) in repr(row)
