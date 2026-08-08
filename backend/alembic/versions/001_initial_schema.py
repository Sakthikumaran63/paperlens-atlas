"""Initial PaperLens database schema migration

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-08-08 22:56:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Ensure vector extension is enabled
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    # 1. users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('email', sa.String(255), nullable=False, unique=True),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('name', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    # 2. workspaces table
    op.create_table(
        'workspaces',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index(op.f('ix_workspaces_user_id'), 'workspaces', ['user_id'], unique=False)

    # 3. papers table
    op.create_table(
        'papers',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('title', sa.String(512), nullable=False),
        sa.Column('authors', postgresql.JSONB(), nullable=True),
        sa.Column('abstract', sa.Text(), nullable=True),
        sa.Column('publication_year', sa.Integer(), nullable=True),
        sa.Column('file_name', sa.String(255), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=False),
        sa.Column('page_count', sa.Integer(), nullable=True),
        sa.Column(
            'status',
            sa.Enum('UPLOADED', 'PROCESSING', 'READY', 'FAILED', name='paper_status_enum'),
            nullable=False,
            server_default='UPLOADED'
        ),
        sa.Column(
            'stage',
            sa.Enum('UPLOADING', 'EXTRACTING', 'STRUCTURING', 'CHUNKING', 'EMBEDDING', 'ANALYZING', 'READY', 'FAILED', name='pipeline_stage_enum'),
            nullable=False,
            server_default='UPLOADING'
        ),
        sa.Column('progress', sa.Integer(), server_default='0', nullable=False),
        sa.Column('stage_details_json', postgresql.JSON(astext_type=sa.Text()), server_default='{}', nullable=True),
        sa.Column('processing_error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index(op.f('ix_papers_workspace_id'), 'papers', ['workspace_id'], unique=False)
    op.create_index(op.f('ix_papers_status'), 'papers', ['status'], unique=False)

    # 4. paper_pages table
    op.create_table(
        'paper_pages',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('paper_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('papers.id', ondelete='CASCADE'), nullable=False),
        sa.Column('page_number', sa.Integer(), nullable=False),
        sa.Column('raw_text', sa.Text(), nullable=False),
        sa.Column('cleaned_text', sa.Text(), nullable=False),
        sa.Column('character_count', sa.Integer(), nullable=False),
        sa.Column('word_count', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index(op.f('ix_paper_pages_paper_id'), 'paper_pages', ['paper_id'], unique=False)

    # 5. paper_sections table
    op.create_table(
        'paper_sections',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('paper_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('papers.id', ondelete='CASCADE'), nullable=False),
        sa.Column('title', sa.String(512), nullable=False),
        sa.Column('normalized_title', sa.String(512), nullable=False),
        sa.Column(
            'section_type',
            sa.Enum(
                'ABSTRACT', 'INTRODUCTION', 'RELATED_WORK', 'METHODOLOGY', 'DATASET',
                'EXPERIMENTS', 'RESULTS', 'DISCUSSION', 'LIMITATIONS', 'CONCLUSION',
                'REFERENCES', 'OTHER', name='section_type_enum'
            ),
            nullable=False,
            server_default='OTHER'
        ),
        sa.Column('page_start', sa.Integer(), nullable=False),
        sa.Column('page_end', sa.Integer(), nullable=False),
        sa.Column('order_index', sa.Integer(), nullable=False),
        sa.Column('confidence', sa.Float(), server_default='1.0', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index(op.f('ix_paper_sections_paper_id'), 'paper_sections', ['paper_id'], unique=False)
    op.create_index(op.f('ix_paper_sections_section_type'), 'paper_sections', ['section_type'], unique=False)

    # 6. paper_chunks table
    op.create_table(
        'paper_chunks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('paper_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('papers.id', ondelete='CASCADE'), nullable=False),
        sa.Column('page_number', sa.Integer(), nullable=False),
        sa.Column('section_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('paper_sections.id', ondelete='SET NULL'), nullable=True),
        sa.Column('chunk_index', sa.Integer(), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('token_count', sa.Integer(), nullable=False),
        sa.Column('embedding', Vector(1536), nullable=True),
        sa.Column('metadata', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index(op.f('ix_paper_chunks_paper_id'), 'paper_chunks', ['paper_id'], unique=False)
    op.create_index(op.f('ix_paper_chunks_section_id'), 'paper_chunks', ['section_id'], unique=False)

    # 7. paper_analyses table
    op.create_table(
        'paper_analyses',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('paper_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('papers.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('methodology', sa.Text(), nullable=True),
        sa.Column('key_contributions', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index(op.f('ix_paper_analyses_paper_id'), 'paper_analyses', ['paper_id'], unique=True)

    # 8. questions table
    op.create_table(
        'questions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('paper_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('papers.id', ondelete='SET NULL'), nullable=True),
        sa.Column('question_text', sa.Text(), nullable=False),
        sa.Column(
            'question_type',
            sa.Enum(
                'PROBLEM', 'OBJECTIVE', 'CONTRIBUTION', 'METHODOLOGY', 'MODEL',
                'ALGORITHM', 'DATASET', 'EXPERIMENT', 'RESULT', 'METRIC',
                'LIMITATION', 'FUTURE_WORK', 'GENERAL', 'UNKNOWN', name='question_type_enum'
            ),
            nullable=False,
            server_default='GENERAL'
        ),
        sa.Column('confidence', sa.Float(), server_default='1.0', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index(op.f('ix_questions_workspace_id'), 'questions', ['workspace_id'], unique=False)
    op.create_index(op.f('ix_questions_paper_id'), 'questions', ['paper_id'], unique=False)

    # 9. retrieved_evidences table
    op.create_table(
        'retrieved_evidences',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('question_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('questions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('chunk_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('paper_chunks.id', ondelete='CASCADE'), nullable=False),
        sa.Column('similarity_score', sa.Float(), nullable=False),
        sa.Column('rank', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index(op.f('ix_retrieved_evidences_question_id'), 'retrieved_evidences', ['question_id'], unique=False)
    op.create_index(op.f('ix_retrieved_evidences_chunk_id'), 'retrieved_evidences', ['chunk_id'], unique=False)

    # 10. answers table
    op.create_table(
        'answers',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('question_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('questions.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('answer_text', sa.Text(), nullable=False),
        sa.Column('is_abstained', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('abstention_reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index(op.f('ix_answers_question_id'), 'answers', ['question_id'], unique=True)

    # 11. answer_evidences table
    op.create_table(
        'answer_evidences',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('answer_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('answers.id', ondelete='CASCADE'), nullable=False),
        sa.Column('retrieved_evidence_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('retrieved_evidences.id', ondelete='CASCADE'), nullable=False),
        sa.Column('relevance_explanation', sa.Text(), nullable=True),
        sa.Column('quote_text', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index(op.f('ix_answer_evidences_answer_id'), 'answer_evidences', ['answer_id'], unique=False)
    op.create_index(op.f('ix_answer_evidences_retrieved_evidence_id'), 'answer_evidences', ['retrieved_evidence_id'], unique=False)


def downgrade() -> None:
    op.drop_table('answer_evidences')
    op.drop_table('answers')
    op.drop_table('retrieved_evidences')
    op.drop_table('questions')
    op.drop_table('paper_analyses')
    op.drop_table('paper_chunks')
    op.drop_table('paper_sections')
    op.drop_table('paper_pages')
    op.drop_table('papers')
    op.drop_table('workspaces')
    op.drop_table('users')

    op.execute("DROP TYPE IF EXISTS question_type_enum;")
    op.execute("DROP TYPE IF EXISTS section_type_enum;")
    op.execute("DROP TYPE IF EXISTS paper_status_enum;")
