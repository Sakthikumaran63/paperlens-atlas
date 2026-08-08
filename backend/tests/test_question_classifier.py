import pytest
from httpx import AsyncClient

from app.models.enums import QuestionType, SectionType
from app.schemas.question import QuestionClassificationResponse
from app.services.question_classifier import (
    BaseQuestionClassifier,
    QuestionClassificationService,
    RuleBasedQuestionClassifier,
)


def test_question_classifier_30_representative_questions():
    classifier = RuleBasedQuestionClassifier()

    # 30+ Representative Research Questions covering all 14 taxonomy types
    test_cases = [
        # 1. PROBLEM (2)
        ("What core problem does this paper address?", QuestionType.PROBLEM),
        ("Why is multi-modal alignment a challenging issue?", QuestionType.PROBLEM),

        # 2. OBJECTIVE (2)
        ("What is the primary objective of the proposed approach?", QuestionType.OBJECTIVE),
        ("What is the main goal of this research study?", QuestionType.OBJECTIVE),

        # 3. CONTRIBUTION (3)
        ("What are the main contributions of this paper?", QuestionType.CONTRIBUTION),
        ("What novelty does the paper introduce?", QuestionType.CONTRIBUTION),
        ("What key contribution is presented in the abstract?", QuestionType.CONTRIBUTION),

        # 4. METHODOLOGY (3)
        ("How does the self-attention mechanism work?", QuestionType.METHODOLOGY),
        ("What is the overall approach for feature extraction?", QuestionType.METHODOLOGY),
        ("What pipeline is used for data processing?", QuestionType.METHODOLOGY),

        # 5. MODEL (2)
        ("What neural network model architecture is used?", QuestionType.MODEL),
        ("How many layers are in the transformer encoder?", QuestionType.MODEL),

        # 6. ALGORITHM (2)
        ("What is the time complexity of the algorithm?", QuestionType.ALGORITHM),
        ("How is the optimization step computed in pseudo-code?", QuestionType.ALGORITHM),

        # 7. DATASET (3)
        ("What dataset was used for training?", QuestionType.DATASET),
        ("How many samples are in the ImageNet evaluation set?", QuestionType.DATASET),
        ("Which corpus was selected as the benchmark?", QuestionType.DATASET),

        # 8. EXPERIMENT (3)
        ("What experimental setup was used for evaluation?", QuestionType.EXPERIMENT),
        ("What hyperparameters were chosen for the baseline?", QuestionType.EXPERIMENT),
        ("What ablation study setup was conducted?", QuestionType.EXPERIMENT),

        # 9. RESULT (3)
        ("What are the main results of the experiments?", QuestionType.RESULT),
        ("Does the proposed model outperform state-of-the-art SOTA?", QuestionType.RESULT),
        ("What score did the model achieve on GLUE?", QuestionType.RESULT),

        # 10. METRIC (2)
        ("What evaluation metric is used to measure BLEU score?", QuestionType.METRIC),
        ("How is the F1 accuracy loss function computed?", QuestionType.METRIC),

        # 11. LIMITATION (3)
        ("What are the limitations of this method?", QuestionType.LIMITATION),
        ("Where does the model fail or exhibit drawbacks?", QuestionType.LIMITATION),
        ("What are the primary threats to validity?", QuestionType.LIMITATION),

        # 12. FUTURE_WORK (2)
        ("What future work do the authors propose?", QuestionType.FUTURE_WORK),
        ("What are the next steps for future research?", QuestionType.FUTURE_WORK),

        # 13. GENERAL (2)
        ("Can you give a brief summary of this paper?", QuestionType.GENERAL),
        ("What is an overview of the findings?", QuestionType.GENERAL),

        # 14. UNKNOWN (1)
        ("", QuestionType.UNKNOWN),
    ]

    assert len(test_cases) >= 30, f"Expected at least 30 test cases, got {len(test_cases)}"

    for q_text, expected_type in test_cases:
        res = classifier.classify(q_text)
        assert res.question_type == expected_type, f"Failed for '{q_text}': expected {expected_type}, got {res.question_type}"
        assert 0.0 <= res.confidence <= 1.0
        assert len(res.retrieval_priorities) > 0


def test_question_classifier_retrieval_priority_examples():
    classifier = RuleBasedQuestionClassifier()

    # User explicitly requested examples:
    # DATASET -> DATASET, EXPERIMENTS, METHODOLOGY
    res_dataset = classifier.classify("What dataset was used for training?")
    assert res_dataset.question_type == QuestionType.DATASET
    assert res_dataset.retrieval_priorities == [SectionType.DATASET, SectionType.EXPERIMENTS, SectionType.METHODOLOGY]

    # RESULT -> RESULTS, EXPERIMENTS, DISCUSSION
    res_result = classifier.classify("What are the results?")
    assert res_result.question_type == QuestionType.RESULT
    assert res_result.retrieval_priorities == [SectionType.RESULTS, SectionType.EXPERIMENTS, SectionType.DISCUSSION]

    # METHODOLOGY -> METHODOLOGY, EXPERIMENTS
    res_method = classifier.classify("How does the method work?")
    assert res_method.question_type == QuestionType.METHODOLOGY
    assert res_method.retrieval_priorities == [SectionType.METHODOLOGY, SectionType.EXPERIMENTS]

    # LIMITATION -> LIMITATIONS, DISCUSSION, CONCLUSION
    res_limitation = classifier.classify("What are the limitations?")
    assert res_limitation.question_type == QuestionType.LIMITATION
    assert res_limitation.retrieval_priorities == [SectionType.LIMITATIONS, SectionType.DISCUSSION, SectionType.CONCLUSION]


class CustomMockClassifier(BaseQuestionClassifier):
    """Custom Mock Classifier testing swappable interface abstraction."""
    def classify(self, question_text: str) -> QuestionClassificationResponse:
        return QuestionClassificationResponse(
            question_type=QuestionType.CONTRIBUTION,
            confidence=0.99,
            retrieval_priorities=[SectionType.ABSTRACT, SectionType.CONCLUSION]
        )


def test_classifier_swappable_abstraction():
    custom_classifier = CustomMockClassifier()
    service = QuestionClassificationService(classifier=custom_classifier)

    res = service.classify_question("Any random question")
    assert res.question_type == QuestionType.CONTRIBUTION
    assert res.confidence == 0.99
    assert res.retrieval_priorities == [SectionType.ABSTRACT, SectionType.CONCLUSION]


@pytest.mark.asyncio
async def test_question_classify_api_endpoint(client: AsyncClient):
    payload = {"question_text": "Which datasets were benchmarked in this paper?"}
    response = await client.post("/api/v1/questions/classify", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["question_type"] == "DATASET"
    assert data["confidence"] > 0.9
    assert "DATASET" in data["retrieval_priorities"]
