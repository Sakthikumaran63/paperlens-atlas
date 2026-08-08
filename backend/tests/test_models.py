import uuid
import pytest
from app.models.enums import PaperStatus, QuestionType, SectionType
from app.models.user import User
from app.models.workspace import Workspace
from app.models.paper import Paper
from app.models.paper_page import PaperPage
from app.models.paper_section import PaperSection
from app.models.paper_chunk import PaperChunk
from app.models.paper_analysis import PaperAnalysis
from app.models.question import Question
from app.models.retrieved_evidence import RetrievedEvidence
from app.models.answer import Answer
from app.models.answer_evidence import AnswerEvidence


def test_paper_status_transitions():
    paper = Paper(
        title="Attention Is All You Need",
        file_name="attention.pdf",
        file_size=1048576,
        status=PaperStatus.UPLOADED
    )
    assert paper.status == PaperStatus.UPLOADED

    # Transition to PROCESSING
    paper.status = PaperStatus.PROCESSING
    assert paper.status == PaperStatus.PROCESSING

    # Transition to READY
    paper.status = PaperStatus.READY
    assert paper.status == PaperStatus.READY

    # Transition to FAILED with error
    paper.status = PaperStatus.FAILED
    paper.processing_error = "Extraction failed: corrupted PDF"
    assert paper.status == PaperStatus.FAILED
    assert paper.processing_error == "Extraction failed: corrupted PDF"


def test_section_types():
    valid_types = [
        SectionType.ABSTRACT,
        SectionType.INTRODUCTION,
        SectionType.RELATED_WORK,
        SectionType.METHODOLOGY,
        SectionType.DATASET,
        SectionType.EXPERIMENTS,
        SectionType.RESULTS,
        SectionType.DISCUSSION,
        SectionType.LIMITATIONS,
        SectionType.CONCLUSION,
        SectionType.REFERENCES,
        SectionType.OTHER,
    ]
    for st in valid_types:
        section = PaperSection(
            title="Test Section",
            normalized_title="test section",
            section_type=st,
            page_start=1,
            page_end=3,
            order_index=0,
            confidence=0.95
        )
        assert section.section_type == st
        assert section.confidence == 0.95


def test_models_relationships():
    # 1. User & Workspace
    user = User(email="test@paperlens.ai", name="Research User")
    workspace = Workspace(user=user, name="Transformers Research", description="NLP Papers")
    assert workspace.user == user
    assert workspace in user.workspaces

    # 2. Paper
    paper = Paper(
        workspace=workspace,
        title="Attention Is All You Need",
        authors=["Vaswani et al."],
        abstract="We propose the Transformer...",
        publication_year=2017,
        file_name="attention.pdf",
        file_size=524288,
        page_count=15,
        status=PaperStatus.READY
    )
    assert paper.workspace == workspace
    assert paper in workspace.papers

    # 3. PaperPage & PaperSection
    page = PaperPage(
        paper=paper,
        page_number=1,
        raw_text="Abstract text...",
        cleaned_text="Abstract text...",
        character_count=16,
        word_count=2
    )
    section = PaperSection(
        paper=paper,
        title="1. Introduction",
        normalized_title="introduction",
        section_type=SectionType.INTRODUCTION,
        page_start=1,
        page_end=2,
        order_index=1
    )
    assert page.paper == paper
    assert section.paper == paper
    assert page in paper.pages
    assert section in paper.sections

    # 4. PaperChunk
    chunk = PaperChunk(
        paper=paper,
        section=section,
        page_number=1,
        chunk_index=0,
        text="The Transformer is the first sequence model...",
        token_count=42,
        embedding=[0.1] * 1536,
        metadata_json={"source": "pdf_parser"}
    )
    assert chunk.paper == paper
    assert chunk.section == section
    assert chunk in paper.chunks
    assert chunk in section.chunks

    # 5. PaperAnalysis
    analysis = PaperAnalysis(
        paper=paper,
        summary="Introduces self-attention architecture.",
        methodology="Multi-head attention mechanism.",
        key_contributions=["Self-Attention", "Positional Encoding"]
    )
    assert paper.analysis == analysis
    assert analysis.paper == paper

    # 6. Question
    question = Question(
        workspace=workspace,
        paper=paper,
        question_text="What is multi-head attention?",
        question_type=QuestionType.METHODOLOGY,
        confidence=0.95
    )
    assert question.workspace == workspace
    assert question.paper == paper
    assert question in workspace.questions

    # 7. RetrievedEvidence
    retrieved_ev = RetrievedEvidence(
        question=question,
        chunk=chunk,
        similarity_score=0.92,
        rank=1
    )
    assert retrieved_ev.question == question
    assert retrieved_ev.chunk == chunk
    assert retrieved_ev in question.retrieved_evidences

    # 8. Answer & AnswerEvidence
    answer = Answer(
        question=question,
        answer_text="Multi-head attention allows the model to jointly attend to information...",
        is_abstained=False
    )
    answer_ev = AnswerEvidence(
        answer=answer,
        retrieved_evidence=retrieved_ev,
        relevance_explanation="Directly explains multi-head attention mechanism.",
        quote_text="Multi-head attention allows..."
    )
    assert answer.question == question
    assert question.answer == answer
    assert answer_ev.answer == answer
    assert answer_ev.retrieved_evidence == retrieved_ev
    assert answer_ev in answer.evidences
