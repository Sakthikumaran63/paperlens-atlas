import uuid
from typing import List, Optional
from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Request, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, get_db, get_workspace_scoped_paper
from app.core.limiter import limiter
from app.models.enums import PaperStatus, PipelineStage, RetrievalMode
from app.models.paper import Paper
from app.models.user import User
from app.models.workspace import Workspace
from app.models.question import Question
from app.models.answer import Answer
from app.models.answer_evidence import AnswerEvidence
from app.schemas.analysis import ClaimWithSource, PaperAnalysisResponse, StructuredPaperSummary
from app.schemas.answer import AskQuestionRequest, GroundedAnswerResponse
from app.schemas.contribution import ContributionEvidence, ContributionExtractionResponse, ExtractedContribution
from app.schemas.evaluation import EvaluationBenchmarkReport, EvaluationDataset
from app.schemas.evidence import EvidencePackage
from app.schemas.methodology import MethodologyEvidenceItem, MethodologyExtractionResponse
from app.schemas.paper import (
    PaperResponse,
    PaperStatusResponse,
    PaperUploadResponse,
    RecommendedPaper,
    PaperRecommendationsResponse
)
from app.services.semantic_scholar_service import SemanticScholarService
from app.schemas.question import QuestionAnsweringRequest, QuestionAnsweringResponse, SourceMetadataItem
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
    background_tasks: BackgroundTasks,
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
        file_path=stored_filename,
        file_size=file_size,
        status=PaperStatus.UPLOADED
    )
    db.add(new_paper)
    await db.commit()
    await db.refresh(new_paper)

    # 4. Launch background pipeline processing asynchronously
    orchestrator = PaperPipelineOrchestrator()
    background_tasks.add_task(orchestrator.run_pipeline, new_paper.id)

    return PaperUploadResponse(
        paper_id=new_paper.id,
        file_name=new_paper.file_name,
        status=new_paper.status
    )


@router.get("/papers/recommendations/search", response_model=PaperRecommendationsResponse)
@limiter.limit("20/minute")
async def search_paper_recommendations_endpoint(
    request: Request,
    title: str,
    limit: int = 5,
    current_user: User = Depends(get_current_user)
) -> PaperRecommendationsResponse:
    """
    Search for related reference papers given a paper title string via Semantic Scholar.
    """
    if not title or not title.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Title parameter cannot be empty.")

    service = SemanticScholarService()
    raw_recommendations = await service.fetch_related_papers_by_title(title.strip(), limit=limit)

    recommendations = [RecommendedPaper(**p) for p in raw_recommendations]
    return PaperRecommendationsResponse(
        seed_title=title.strip(),
        count=len(recommendations),
        recommendations=recommendations
    )


@router.get("/papers/{paper_id}/status", response_model=PaperStatusResponse)
async def get_paper_status_endpoint(
    paper: Paper = Depends(get_workspace_scoped_paper)
) -> PaperStatusResponse:
    """
    Retrieve real-time processing pipeline status, progress percentage, stage details, and error message.
    """
    return PaperStatusResponse(
        paper_id=paper.id,
        status=paper.status,
        stage=paper.stage,
        progress=paper.progress,
        stages_detail=paper.stage_details_json,
        processing_error=paper.processing_error
    )


@router.post("/papers/{paper_id}/retry")
async def retry_paper_pipeline_endpoint(
    background_tasks: BackgroundTasks,
    paper: Paper = Depends(get_workspace_scoped_paper)
) -> dict:
    """
    Retry processing pipeline for a paper.
    """
    orchestrator = PaperPipelineOrchestrator()
    background_tasks.add_task(orchestrator.run_pipeline, paper.id, True)

    return {
        "message": "Paper pipeline retry launched successfully.",
        "paper_id": str(paper.id),
        "status": PaperStatus.PROCESSING
    }


@router.post("/papers/{paper_id}/process", response_model=PaperResponse)
async def process_paper_endpoint(
    paper: Paper = Depends(get_workspace_scoped_paper),
    db: AsyncSession = Depends(get_db)
) -> PaperResponse:
    """
    Trigger text extraction and scientific section processing for an uploaded PDF paper.
    Updates status from UPLOADED -> PROCESSING -> READY (or FAILED).
    """
    processed_paper = await process_paper(paper.id, db)
    return PaperResponse.model_validate(processed_paper)


@router.post("/papers/{paper_id}/index", response_model=PaperResponse)
async def index_paper_endpoint(
    force_reindex: bool = False,
    paper: Paper = Depends(get_workspace_scoped_paper),
    db: AsyncSession = Depends(get_db)
) -> PaperResponse:
    """
    Generate and store vector embeddings for PaperChunk.text in PostgreSQL pgvector.
    Batches chunk vector generation and updates paper status: PROCESSING -> READY (or FAILED).
    Allows force_reindex query parameter.
    """
    indexed_paper = await index_paper(paper.id, db, force_reindex=force_reindex)
    return PaperResponse.model_validate(indexed_paper)


@router.post("/papers/{paper_id}/retrieve", response_model=List[RetrievedChunkCandidate])
async def retrieve_paper_evidence_endpoint(
    req: RetrievalRequest,
    paper: Paper = Depends(get_workspace_scoped_paper),
    db: AsyncSession = Depends(get_db)
) -> List[RetrievedChunkCandidate]:
    """
    Retrieve ranked evidence candidates for a query within a paper.
    Supports BASELINE_RAG (semantic only) and STRUCTURE_AWARE_RAG (combined weighted scoring) modes.
    Returns detailed scores: semantic_score, section_score, keyword_score, final_score, page, section, text.
    """
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
    req: RetrievalRequest,
    paper: Paper = Depends(get_workspace_scoped_paper),
    db: AsyncSession = Depends(get_db)
) -> EvidencePackage:
    """
    Retrieve ranked candidates and transform them into a compact, deduplicated, token-budgeted, auditable evidence package for the LLM.
    """
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
    req: AskQuestionRequest,
    paper: Paper = Depends(get_workspace_scoped_paper),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> GroundedAnswerResponse:
    """
    Ask a question about a research paper.
    Executes pipeline: Question Classification -> Structure-Aware Retrieval -> Evidence Selection -> Candidate Answer -> Evidence Verification -> Final Answer OR Abstention.
    Returns verified response with support_score, supported, searched_sections, evidence_count, and abstention_reason.
    """
    answer_gen_svc = AnswerGenerationService()
    try:
        response = await answer_gen_svc.generate_answer_for_paper(
            paper_id=paper.id,
            question_text=req.question_text,
            mode=req.mode,
            db=db,
            user_id=current_user.id
        )
        return response
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err)
        )


@router.post("/papers/{paper_id}/questions", response_model=QuestionAnsweringResponse)
@limiter.limit("30/minute")
async def ask_paper_questions_main_endpoint(
    request: Request,
    req: QuestionAnsweringRequest,
    paper: Paper = Depends(get_workspace_scoped_paper),
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
            db=db,
            user_id=current_user.id
        )
        return response
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err)
        )



@router.post("/papers/{paper_id}/reanalyze", status_code=status.HTTP_200_OK)
async def reanalyze_paper_endpoint(
    paper: Paper = Depends(get_workspace_scoped_paper),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Force re-analysis of a paper by clearing the cached PaperAnalysis record.
    The next GET /analysis, /methodology, /contributions request will re-run LLM extraction.
    Use this after configuring a Gemini or OpenAI API key to get real LLM-powered results.
    """
    from app.models.paper_analysis import PaperAnalysis
    from sqlalchemy import delete

    await db.execute(delete(PaperAnalysis).where(PaperAnalysis.paper_id == paper.id))
    await db.commit()
    return {"status": "cleared", "paper_id": str(paper.id), "message": "Analysis cache cleared. Re-fetch /analysis to trigger fresh LLM extraction."}


@router.get("/papers/{paper_id}/analysis", response_model=PaperAnalysisResponse)
async def get_paper_analysis_endpoint(
    paper: Paper = Depends(get_workspace_scoped_paper),
    db: AsyncSession = Depends(get_db)
) -> PaperAnalysisResponse:
    """
    Retrieve structured research-paper analysis.
    Returns 10-field structured summary (Executive Summary, Problem Statement, Objective, Methodology,
    Key Contributions, Dataset, Experimental Setup, Key Results, Limitations, Conclusion) and claim source lineage.
    """
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
    paper: Paper = Depends(get_workspace_scoped_paper),
    db: AsyncSession = Depends(get_db)
) -> MethodologyExtractionResponse:
    """
    Retrieve structured methodology extraction for a research paper.
    Identifies research approach, model/architecture, algorithms, dataset, preprocessing, training procedure,
    experimental setup, evaluation metrics, and evidence source lineage (section & page).
    """
    methodology_svc = MethodologyExtractionService()
    extraction = await methodology_svc.extract_methodology(paper_id=paper.id, db=db)
    return extraction


@router.get("/papers/{paper_id}/contributions", response_model=ContributionExtractionResponse)
async def get_paper_contributions_endpoint(
    paper: Paper = Depends(get_workspace_scoped_paper),
    db: AsyncSession = Depends(get_db)
) -> ContributionExtractionResponse:
    """
    Retrieve key contributions for a research paper.
    Identifies explicit and evidence-supported inferred contributions, prioritizing Introduction, Abstract, Conclusion,
    and Methodology sections, and binds evidence source lineage (page, section, chunk_id).
    """
    contrib_svc = ContributionExtractionService()
    extraction = await contrib_svc.extract_contributions(paper_id=paper.id, db=db)
    return extraction


@router.post("/papers/{paper_id}/evaluate", response_model=EvaluationBenchmarkReport)
async def evaluate_paper_endpoint(
    dataset: Optional[EvaluationDataset] = None,
    paper: Paper = Depends(get_workspace_scoped_paper),
    db: AsyncSession = Depends(get_db)
) -> EvaluationBenchmarkReport:
    """
    Run PaperLens evaluation benchmark for a paper.
    Compares BASELINE_RAG vs STRUCTURE_AWARE_RAG vs STRUCTURE_AWARE_RAG + EVIDENCE_VERIFICATION across
    Retrieval (Recall@K, Precision@K, MRR), Answer, Grounding, and Abstention metrics.
    """
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
    paper: Paper = Depends(get_workspace_scoped_paper)
) -> PaperResponse:
    """
    Retrieve metadata for a specific paper.
    Requires workspace ownership.
    """
    return PaperResponse.model_validate(paper)


@router.delete("/papers/{paper_id}", status_code=status.HTTP_200_OK)
async def delete_paper(
    paper: Paper = Depends(get_workspace_scoped_paper),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Delete a paper database record and remove its stored file.
    Requires authentication and workspace ownership.
    """
    pid = paper.id
    await db.delete(paper)
    await db.commit()

    return {"detail": "Paper deleted successfully.", "paper_id": str(pid)}


@router.get("/papers/{paper_id}/chat-history", response_model=List[QuestionAnsweringResponse])
async def get_paper_chat_history_endpoint(
    paper: Paper = Depends(get_workspace_scoped_paper),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> List[QuestionAnsweringResponse]:
    """
    Retrieve past Q&A history for a given paper and user.
    """
    stmt = (
        select(Question)
        .where(
            Question.paper_id == paper.id,
            Question.user_id == current_user.id
        )
        .options(
            selectinload(Question.answer)
            .selectinload(Answer.evidences)
            .selectinload(AnswerEvidence.chunk)
        )
        .order_by(Question.created_at.asc())
    )
    result = await db.execute(stmt)
    questions = result.scalars().all()

    chat_history = []
    for q in questions:
        source_items = []
        if q.answer and q.answer.evidences:
            for ev in q.answer.evidences:
                page_no = ev.page_number if ev.page_number is not None else (ev.chunk.page_number if ev.chunk else 1)
                sec_title = ev.section_title if ev.section_title else (ev.chunk.metadata_json.get("section_title") if (ev.chunk and ev.chunk.metadata_json) else "Document Text")
                text_content = ev.quote_text if ev.quote_text else (ev.chunk.text if ev.chunk else "")
                
                source_items.append(
                    SourceMetadataItem(
                        page=page_no,
                        section=sec_title,
                        chunk_id=ev.chunk_id,
                        text=text_content
                    )
                )

        chat_history.append(
            QuestionAnsweringResponse(
                question_id=q.id,
                question=q.question_text,
                question_type=q.intent,
                answer=q.answer.answer_text if q.answer else "No answer generated.",
                abstained=q.answer.is_abstained if q.answer else True,
                support_score=q.answer.support_score if (q.answer and q.answer.support_score is not None) else 0.0,
                sources=source_items
            )
        )

    return chat_history


@router.get("/papers/{paper_id}/recommendations", response_model=PaperRecommendationsResponse)
@limiter.limit("30/minute")
async def get_paper_recommendations_endpoint(
    request: Request,
    limit: int = 5,
    paper: Paper = Depends(get_workspace_scoped_paper),
    current_user: User = Depends(get_current_user)
) -> PaperRecommendationsResponse:
    """
    Fetch recommended related academic papers for an existing paper in the workspace via Semantic Scholar.
    """
    service = SemanticScholarService()
    seed_title = paper.title or paper.file_name
    raw_recommendations = await service.fetch_related_papers_by_title(seed_title, limit=limit)

    recommendations = [RecommendedPaper(**p) for p in raw_recommendations]
    return PaperRecommendationsResponse(
        seed_paper_id=paper.id,
        seed_title=seed_title,
        count=len(recommendations),
        recommendations=recommendations
    )


