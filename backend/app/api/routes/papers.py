import uuid
from typing import List, Optional
from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.enums import PaperStatus, PipelineStage
from app.models.paper import Paper
from app.models.user import User
from app.models.workspace import Workspace
from app.schemas.analysis import ClaimWithSource, PaperAnalysisResponse, StructuredPaperSummary
from app.schemas.answer import AskQuestionRequest, GroundedAnswerResponse
from app.schemas.contribution import ContributionEvidence, ContributionExtractionResponse, ExtractedContribution
from app.schemas.evaluation import EvaluationBenchmarkReport, EvaluationDataset
from app.schemas.evidence import EvidencePackage
from app.schemas.methodology import MethodologyEvidenceItem, MethodologyExtractionResponse
from app.schemas.paper import PaperResponse, PaperStatusResponse, PaperUploadResponse
from app.schemas.question import QuestionAnsweringRequest, QuestionAnsweringResponse
from app.schemas.retrieval import RetrievalRequest, RetrievedChunkCandidate
from app.services.answer_generation_service import AnswerGenerationService
from app.services.contribution_extraction_service import ContributionExtractionService
from app.services.evaluation_service import EvaluationService
from app.services.evidence_selection_service import EvidenceSelectionService
from app.services.indexing_service import index_paper
from app.services.methodology_extraction_service import MethodologyExtractionService
from app.services.paper_processing_service import process_paper
from app.services.pipeline_orchestrator import PaperPipelineOrchestrator
from app.services.retrieval_service import RetrievalService
from app.services.retrieval_strategy_service import StructureAwareRetrievalService
from app.services.summary_service import SummaryService
from app.utils.storage import delete_stored_file, save_upload_file

router = APIRouter()


@router.post("/papers/upload", response_model=PaperUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_paper(
    file: UploadFile = File(...),
    workspace_id: Optional[uuid.UUID] = Form(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> PaperUploadResponse:
    """
    Upload a research paper (PDF only, max 20 MB).
    Validates MIME type, extension, size limit, and sanitizes filenames.
    """
    # 1. Resolve & verify workspace ownership
    if workspace_id:
        stmt = select(Workspace).where(Workspace.id == workspace_id, Workspace.user_id == current_user.id)
        result = await db.execute(stmt)
        target_workspace = result.scalar_one_or_none()
        if not target_workspace:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workspace not found or access denied."
            )
    else:
        stmt = select(Workspace).where(Workspace.user_id == current_user.id).order_by(Workspace.created_at)
        result = await db.execute(stmt)
        target_workspace = result.scalars().first()
        if not target_workspace:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No active workspace found. Please create a workspace first."
            )

    # 2. Save upload file securely with validations & path traversal protection
    stored_filename, original_filename, file_size = await save_upload_file(file)

    # 3. Create Paper database record
    new_paper = Paper(
        workspace_id=target_workspace.id,
        title=original_filename,
        file_name=original_filename,
        file_size=file_size,
        status=PaperStatus.UPLOADED
    )
    db.add(new_paper)
    await db.commit()
    await db.refresh(new_paper)

    return PaperUploadResponse(
        paper_id=new_paper.id,
        file_name=new_paper.file_name,
        status=new_paper.status
    )


@router.post("/papers/{paper_id}/process", response_model=PaperResponse)
async def process_paper_endpoint(
    paper_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> PaperResponse:
    """
    Trigger text extraction and scientific section processing for an uploaded PDF paper.
    Updates status from UPLOADED -> PROCESSING -> READY (or FAILED).
    """
    stmt = (
        select(Paper)
        .join(Workspace, Paper.workspace_id == Workspace.id)
        .where(Paper.id == paper_id, Workspace.user_id == current_user.id)
    )
    result = await db.execute(stmt)
    paper = result.scalar_one_or_none()

    if not paper:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paper not found or access denied."
        )

    processed_paper = await process_paper(paper.id, db)
    return PaperResponse.model_validate(processed_paper)


@router.post("/papers/{paper_id}/index", response_model=PaperResponse)
async def index_paper_endpoint(
    paper_id: uuid.UUID,
    force_reindex: bool = False,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> PaperResponse:
    """
    Generate and store vector embeddings for PaperChunk.text in PostgreSQL pgvector.
    Batches chunk vector generation and updates paper status: PROCESSING -> READY (or FAILED).
    Allows force_reindex query parameter.
    """
    stmt = (
        select(Paper)
        .join(Workspace, Paper.workspace_id == Workspace.id)
        .where(Paper.id == paper_id, Workspace.user_id == current_user.id)
    )
    result = await db.execute(stmt)
    paper = result.scalar_one_or_none()

    if not paper:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paper not found or access denied."
        )

    indexed_paper = await index_paper(paper.id, db, force_reindex=force_reindex)
    return PaperResponse.model_validate(indexed_paper)


@router.post("/papers/{paper_id}/retrieve", response_model=List[RetrievedChunkCandidate])
async def retrieve_paper_evidence_endpoint(
    paper_id: uuid.UUID,
    req: RetrievalRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> List[RetrievedChunkCandidate]:
    """
    Retrieve ranked evidence candidates for a query within a paper.
    Supports BASELINE_RAG (semantic only) and STRUCTURE_AWARE_RAG (combined weighted scoring) modes.
    Returns detailed scores: semantic_score, section_score, keyword_score, final_score, page, section, text.
    """
    # Verify paper & workspace ownership
    stmt = (
        select(Paper)
        .join(Workspace, Paper.workspace_id == Workspace.id)
        .where(Paper.id == paper_id, Workspace.user_id == current_user.id)
    )
    result = await db.execute(stmt)
    paper = result.scalar_one_or_none()

    if not paper:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paper not found or access denied."
        )

    retrieval_strategy_svc = StructureAwareRetrievalService()
    candidates = await retrieval_strategy_svc.retrieve_pipeline(
        query=req.query,
        paper_id=paper.id,
        top_k=req.top_k,
        mode=req.mode,
        section_type=req.section_type,
        workspace_id=paper.workspace_id,
        db=db
    )

    return candidates


@router.post("/papers/{paper_id}/evidence", response_model=EvidencePackage)
async def select_paper_evidence_endpoint(
    paper_id: uuid.UUID,
    req: RetrievalRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> EvidencePackage:
    """
    Retrieve ranked candidates and transform them into a compact, deduplicated, token-budgeted, auditable evidence package for the LLM.
    """
    # Verify paper & workspace ownership
    stmt = (
        select(Paper)
        .join(Workspace, Paper.workspace_id == Workspace.id)
        .where(Paper.id == paper_id, Workspace.user_id == current_user.id)
    )
    result = await db.execute(stmt)
    paper = result.scalar_one_or_none()

    if not paper:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paper not found or access denied."
        )

    retrieval_strategy_svc = StructureAwareRetrievalService()
    candidates = await retrieval_strategy_svc.retrieve_pipeline(
        query=req.query,
        paper_id=paper.id,
        top_k=req.top_k * 2,
        mode=req.mode,
        section_type=req.section_type,
        workspace_id=paper.workspace_id,
        db=db
    )

    evidence_selection_svc = EvidenceSelectionService()
    package = evidence_selection_svc.select_evidence(candidates)
    return package


@router.post("/papers/{paper_id}/ask", response_model=GroundedAnswerResponse)
async def ask_paper_question_endpoint(
    paper_id: uuid.UUID,
    req: AskQuestionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> GroundedAnswerResponse:
    """
    Ask a question about a research paper.
    Executes pipeline: Question Classification -> Structure-Aware Retrieval -> Evidence Selection -> Candidate Answer -> Evidence Verification -> Final Answer OR Abstention.
    Returns verified response with support_score, supported, searched_sections, evidence_count, and abstention_reason.
    """
    # Verify paper & workspace ownership
    stmt = (
        select(Paper)
        .join(Workspace, Paper.workspace_id == Workspace.id)
        .where(Paper.id == paper_id, Workspace.user_id == current_user.id)
    )
    result = await db.execute(stmt)
    paper = result.scalar_one_or_none()

    if not paper:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paper not found or access denied."
        )

    answer_gen_svc = AnswerGenerationService()
    try:
        response = await answer_gen_svc.generate_answer_for_paper(
            paper_id=paper.id,
            question_text=req.question_text,
            mode=req.mode,
            db=db
        )
        return response
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err)
        )


@router.post("/papers/{paper_id}/questions", response_model=QuestionAnsweringResponse)
async def ask_paper_questions_main_endpoint(
    paper_id: uuid.UUID,
    req: QuestionAnsweringRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> QuestionAnsweringResponse:
    """
    Main PaperLens question-answering endpoint.
    Executes complete 15-step grounded RAG pipeline:
    1. Authenticate user -> 2. Verify paper ownership -> 3. Validate paper is indexed -> 4. Classify question ->
    5. Route retrieval -> 6. Retrieve candidate chunks -> 7. Rank evidence -> 8. Build evidence package ->
    9. Generate grounded answer -> 10. Verify evidence support -> 11. Either answer or abstain ->
    12. Persist question -> 13. Persist retrieved evidence -> 14. Persist answer -> 15. Persist answer-evidence relationships.
    Returns database-bound evidence sources metadata.
    """
    # 1 & 2. Authenticate user & Verify paper ownership
    stmt = (
        select(Paper)
        .join(Workspace, Paper.workspace_id == Workspace.id)
        .where(Paper.id == paper_id, Workspace.user_id == current_user.id)
    )
    result = await db.execute(stmt)
    paper = result.scalar_one_or_none()

    if not paper:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paper not found or access denied."
        )

    # 3. Validate paper is indexed (PaperStatus.READY)
    if paper.status != PaperStatus.READY:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Paper is not ready for question answering (current status: {paper.status.value}). Please process and index the paper first."
        )

    # 4-15. Execute full 15-step pipeline
    answer_gen_svc = AnswerGenerationService()
    try:
        response = await answer_gen_svc.answer_question_pipeline(
            paper_id=paper.id,
            question_text=req.question,
            mode=req.mode or RetrievalMode.STRUCTURE_AWARE_RAG,
            db=db
        )
        return response
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err)
        )


@router.get("/papers/{paper_id}/analysis", response_model=PaperAnalysisResponse)
async def get_paper_analysis_endpoint(
    paper_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> PaperAnalysisResponse:
    """
    Retrieve structured research-paper analysis.
    Returns 10-field structured summary (Executive Summary, Problem Statement, Objective, Methodology,
    Key Contributions, Dataset, Experimental Setup, Key Results, Limitations, Conclusion) and claim source lineage.
    """
    # Verify paper & workspace ownership
    stmt = (
        select(Paper)
        .join(Workspace, Paper.workspace_id == Workspace.id)
        .where(Paper.id == paper_id, Workspace.user_id == current_user.id)
    )
    result = await db.execute(stmt)
    paper = result.scalar_one_or_none()

    if not paper:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paper not found or access denied."
        )

    summary_svc = SummaryService()
    analysis = await summary_svc.generate_structured_analysis(paper_id=paper.id, db=db)

    # Convert claims_json into ClaimWithSource objects
    claims_objs = []
    if analysis.claims_json and isinstance(analysis.claims_json, list):
        for cl in analysis.claims_json:
            claims_objs.append(
                ClaimWithSource(
                    claim_id=cl.get("claim_id", "claim_1"),
                    claim_text=cl.get("claim_text", ""),
                    section=cl.get("section", "Document Text"),
                    page=cl.get("page", 1)
                )
            )

    structured_summary = StructuredPaperSummary.model_validate(analysis.summary_json)

    return PaperAnalysisResponse(
        id=analysis.id,
        paper_id=analysis.paper_id,
        summary=structured_summary,
        claims=claims_objs,
        created_at=analysis.created_at
    )


@router.get("/papers/{paper_id}/methodology", response_model=MethodologyExtractionResponse)
async def get_paper_methodology_endpoint(
    paper_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> MethodologyExtractionResponse:
    """
    Retrieve structured methodology extraction for a research paper.
    Identifies research approach, model/architecture, algorithms, dataset, preprocessing, training procedure,
    experimental setup, evaluation metrics, and evidence source lineage (section & page).
    """
    # Verify paper & workspace ownership
    stmt = (
        select(Paper)
        .join(Workspace, Paper.workspace_id == Workspace.id)
        .where(Paper.id == paper_id, Workspace.user_id == current_user.id)
    )
    result = await db.execute(stmt)
    paper = result.scalar_one_or_none()

    if not paper:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paper not found or access denied."
        )

    methodology_svc = MethodologyExtractionService()
    extraction = await methodology_svc.extract_methodology(paper_id=paper.id, db=db)
    return extraction


@router.get("/papers/{paper_id}/contributions", response_model=ContributionExtractionResponse)
async def get_paper_contributions_endpoint(
    paper_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> ContributionExtractionResponse:
    """
    Retrieve key contributions for a research paper.
    Identifies explicit and evidence-supported inferred contributions, prioritizing Introduction, Abstract, Conclusion,
    and Methodology sections, and binds evidence source lineage (page, section, chunk_id).
    """
    # Verify paper & workspace ownership
    stmt = (
        select(Paper)
        .join(Workspace, Paper.workspace_id == Workspace.id)
        .where(Paper.id == paper_id, Workspace.user_id == current_user.id)
    )
    result = await db.execute(stmt)
    paper = result.scalar_one_or_none()

    if not paper:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paper not found or access denied."
        )

    contrib_svc = ContributionExtractionService()
    extraction = await contrib_svc.extract_contributions(paper_id=paper.id, db=db)
    return extraction


@router.post("/papers/{paper_id}/evaluate", response_model=EvaluationBenchmarkReport)
async def evaluate_paper_endpoint(
    paper_id: uuid.UUID,
    dataset: Optional[EvaluationDataset] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> EvaluationBenchmarkReport:
    """
    Run PaperLens evaluation benchmark for a paper.
    Compares BASELINE_RAG vs STRUCTURE_AWARE_RAG vs STRUCTURE_AWARE_RAG + EVIDENCE_VERIFICATION across
    Retrieval (Recall@K, Precision@K, MRR), Answer, Grounding, and Abstention metrics.
    """
    # Verify paper & workspace ownership
    stmt = (
        select(Paper)
        .join(Workspace, Paper.workspace_id == Workspace.id)
        .where(Paper.id == paper_id, Workspace.user_id == current_user.id)
    )
    result = await db.execute(stmt)
    paper = result.scalar_one_or_none()

    if not paper:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paper not found or access denied."
        )

    eval_svc = EvaluationService()
    target_dataset = dataset or eval_svc.generate_sample_evaluation_dataset(paper_id=paper.id)

    report = await eval_svc.run_benchmark(dataset=target_dataset, db=db, top_k=5)
    return report


@router.get("/papers", response_model=List[PaperResponse])
async def list_papers(
    workspace_id: Optional[uuid.UUID] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> List[PaperResponse]:
    """
    List papers in workspace(s) owned by the current user.
    """
    if workspace_id:
        ws_stmt = select(Workspace).where(Workspace.id == workspace_id, Workspace.user_id == current_user.id)
        ws_res = await db.execute(ws_stmt)
        if not ws_res.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workspace not found or access denied."
            )
        stmt = select(Paper).where(Paper.workspace_id == workspace_id).order_by(Paper.created_at.desc())
    else:
        stmt = (
            select(Paper)
            .join(Workspace, Paper.workspace_id == Workspace.id)
            .where(Workspace.user_id == current_user.id)
            .order_by(Paper.created_at.desc())
        )

    result = await db.execute(stmt)
    papers = result.scalars().all()
    return [PaperResponse.model_validate(p) for p in papers]


@router.get("/papers/{paper_id}", response_model=PaperResponse)
async def get_paper_detail(
    paper_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> PaperResponse:
    """
    Retrieve metadata for a specific paper.
    Requires workspace ownership.
    """
    stmt = (
        select(Paper)
        .join(Workspace, Paper.workspace_id == Workspace.id)
        .where(Paper.id == paper_id, Workspace.user_id == current_user.id)
    )
    result = await db.execute(stmt)
    paper = result.scalar_one_or_none()

    if not paper:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paper not found or access denied."
        )

    return PaperResponse.model_validate(paper)


@router.delete("/papers/{paper_id}", status_code=status.HTTP_200_OK)
async def delete_paper(
    paper_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Delete a paper database record and remove its stored file.
    Requires authentication and workspace ownership.
    """
    stmt = (
        select(Paper)
        .join(Workspace, Paper.workspace_id == Workspace.id)
        .where(Paper.id == paper_id, Workspace.user_id == current_user.id)
    )
    result = await db.execute(stmt)
    paper = result.scalar_one_or_none()

    if not paper:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paper not found or access denied."
        )

    await db.delete(paper)
    await db.commit()

    return {"detail": "Paper deleted successfully.", "paper_id": str(paper_id)}
