from fastapi import APIRouter
from app.schemas.question import QuestionClassificationRequest, QuestionClassificationResponse
from app.services.question_classifier import QuestionClassificationService

router = APIRouter()


@router.post("/questions/classify", response_model=QuestionClassificationResponse)
async def classify_question_endpoint(
    req: QuestionClassificationRequest
) -> QuestionClassificationResponse:
    """
    Classify a natural-language research paper question into the PaperLens 14-type QuestionType taxonomy,
    calculate confidence score, and return mapped section retrieval priorities.
    """
    service = QuestionClassificationService()
    return service.classify_question(req.question_text)
