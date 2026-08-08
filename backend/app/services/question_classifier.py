from abc import ABC, abstractmethod
import re
from typing import List, Tuple
from app.models.enums import QuestionType, SectionType
from app.schemas.question import QuestionClassificationResponse


class BaseQuestionClassifier(ABC):
    """
    Abstract interface for research question classifiers.
    Allows fine-tuned ML or LLM classifiers to replace rule-based baselines seamlessly.
    """

    @abstractmethod
    def classify(self, question_text: str) -> QuestionClassificationResponse:
        pass


class RuleBasedQuestionClassifier(BaseQuestionClassifier):
    """
    Deterministic rule and keyword baseline classifier for research paper questions.
    Categorizes natural language questions into the 14-type QuestionType taxonomy,
    assigns confidence scores, and maps to section retrieval priorities.
    """

    # Section retrieval priority mappings for each QuestionType
    RETRIEVAL_PRIORITIES = {
        QuestionType.PROBLEM: [SectionType.ABSTRACT, SectionType.INTRODUCTION],
        QuestionType.OBJECTIVE: [SectionType.ABSTRACT, SectionType.INTRODUCTION],
        QuestionType.CONTRIBUTION: [SectionType.ABSTRACT, SectionType.INTRODUCTION, SectionType.CONCLUSION],
        QuestionType.METHODOLOGY: [SectionType.METHODOLOGY, SectionType.EXPERIMENTS],
        QuestionType.MODEL: [SectionType.METHODOLOGY, SectionType.EXPERIMENTS],
        QuestionType.ALGORITHM: [SectionType.METHODOLOGY, SectionType.EXPERIMENTS],
        QuestionType.DATASET: [SectionType.DATASET, SectionType.EXPERIMENTS, SectionType.METHODOLOGY],
        QuestionType.EXPERIMENT: [SectionType.EXPERIMENTS, SectionType.RESULTS],
        QuestionType.RESULT: [SectionType.RESULTS, SectionType.EXPERIMENTS, SectionType.DISCUSSION],
        QuestionType.METRIC: [SectionType.RESULTS, SectionType.EXPERIMENTS, SectionType.METHODOLOGY],
        QuestionType.LIMITATION: [SectionType.LIMITATIONS, SectionType.DISCUSSION, SectionType.CONCLUSION],
        QuestionType.FUTURE_WORK: [SectionType.LIMITATIONS, SectionType.CONCLUSION],
        QuestionType.GENERAL: [SectionType.ABSTRACT, SectionType.INTRODUCTION, SectionType.RESULTS, SectionType.CONCLUSION],
        QuestionType.UNKNOWN: [SectionType.ABSTRACT, SectionType.INTRODUCTION, SectionType.RESULTS, SectionType.CONCLUSION],
    }

    # Intent keyword rules: (pattern, QuestionType, base_confidence)
    RULES: List[Tuple[re.Pattern, QuestionType, float]] = [
        # DATASET
        (re.compile(r'\b(what|which)\s+(dataset|data|corpus|benchmark|train(ing)?\s+set|eval(uation)?\s+set|split)\b', re.I), QuestionType.DATASET, 0.95),
        (re.compile(r'\b(dataset|corpus|benchmark|data\s+source|training\s+data|test\s+data|how\s+many\s+(samples|images|sentences))\b', re.I), QuestionType.DATASET, 0.92),

        # METRIC
        (re.compile(r'\b(evaluation\s+metric|loss\s+function|bleu|rouge|f1|accuracy|precision|recall|perplexity|how\s+is\s+(it|model)\s+evaluated)\b', re.I), QuestionType.METRIC, 0.95),

        # RESULT
        (re.compile(r'\b(what\s+are\s+the\s+results|result|outperform|achieve|state\s+of\s+the\s+art|sota|performance|experimental\s+result|score)\b', re.I), QuestionType.RESULT, 0.94),

        # EXPERIMENT
        (re.compile(r'\b(experiment|experimental\s+setup|ablation|baseline|hardware|gpu|training\s+setup|hyperparameter)\b', re.I), QuestionType.EXPERIMENT, 0.93),

        # LIMITATION
        (re.compile(r'\b(limitation|drawback|weakness|failure\s+case|shortcoming|bottleneck|where\s+does\s+it\s+fail|threats\s+to\s+validity)\b', re.I), QuestionType.LIMITATION, 0.95),

        # FUTURE_WORK
        (re.compile(r'\b(future\s+work|future\s+direction|next\s+step|future\s+research)\b', re.I), QuestionType.FUTURE_WORK, 0.95),

        # ALGORITHM
        (re.compile(r'\b(algorithm|pseudo\-?code|time\s+complexity|big\s+o|optimization\s+step|convergence)\b', re.I), QuestionType.ALGORITHM, 0.94),

        # MODEL
        (re.compile(r'\b(model\s+architecture|neural\s+network|transformer|encoder|decoder|backbone|parameter\s+count|layer)\b', re.I), QuestionType.MODEL, 0.93),

        # METHODOLOGY
        (re.compile(r'\b(how\s+does\s+(it|the\s+model|method|approach|system)\s+work|methodology|approach|mechanism|technique|pipeline)\b', re.I), QuestionType.METHODOLOGY, 0.94),

        # CONTRIBUTION
        (re.compile(r'\b(main\s+contribution|novelty|what\s+is\s+new|key\s+contribution|what\s+does\s+this\s+paper\s+(propose|introduce|contribute))\b', re.I), QuestionType.CONTRIBUTION, 0.95),

        # PROBLEM
        (re.compile(r'\b(what\s+problem|challenge|motivation|why\s+is\s+it\s+(difficult|hard)|addressing|issue)\b', re.I), QuestionType.PROBLEM, 0.93),

        # OBJECTIVE
        (re.compile(r'\b(goal|objective|aim|target|purpose|what\s+is\s+the\s+paper\s+trying\s+to\s+(do|achieve))\b', re.I), QuestionType.OBJECTIVE, 0.92),

        # GENERAL
        (re.compile(r'\b(summary|overview|what\s+is\s+this\s+paper\s+about|summarize)\b', re.I), QuestionType.GENERAL, 0.90),
    ]

    def classify(self, question_text: str) -> QuestionClassificationResponse:
        if not question_text or not question_text.strip():
            return QuestionClassificationResponse(
                question_type=QuestionType.UNKNOWN,
                confidence=0.50,
                retrieval_priorities=self.RETRIEVAL_PRIORITIES[QuestionType.UNKNOWN]
            )

        clean_q = question_text.strip()

        # Iterate rules
        for pattern, q_type, base_conf in self.RULES:
            if pattern.search(clean_q):
                return QuestionClassificationResponse(
                    question_type=q_type,
                    confidence=base_conf,
                    retrieval_priorities=self.RETRIEVAL_PRIORITIES[q_type]
                )

        # Fallback to GENERAL if question ends with ? or contains research terms, otherwise UNKNOWN
        if '?' in clean_q or len(clean_q.split()) > 3:
            return QuestionClassificationResponse(
                question_type=QuestionType.GENERAL,
                confidence=0.65,
                retrieval_priorities=self.RETRIEVAL_PRIORITIES[QuestionType.GENERAL]
            )

        return QuestionClassificationResponse(
            question_type=QuestionType.UNKNOWN,
            confidence=0.50,
            retrieval_priorities=self.RETRIEVAL_PRIORITIES[QuestionType.UNKNOWN]
        )


class QuestionClassificationService:
    """
    Facade service for question classification.
    Allows injecting alternative ML or LLM classifiers while keeping API signatures consistent.
    """

    def __init__(self, classifier: Optional[BaseQuestionClassifier] = None):
        self.classifier = classifier or RuleBasedQuestionClassifier()

    def classify_question(self, question_text: str) -> QuestionClassificationResponse:
        return self.classifier.classify(question_text)
