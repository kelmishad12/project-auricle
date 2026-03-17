"""
Service to run DeepEval metrics asynchronously in the background.
"""
# pylint: disable=line-too-long
from deepeval.metrics import FaithfulnessMetric, HallucinationMetric
from deepeval.test_case import LLMTestCase
from deepeval.metrics.answer_relevancy.answer_relevancy import AnswerRelevancyMetric
from deepeval import evaluate

from src.db.session import SessionLocal
from src.db.models.base import EvalMetrics

class EvalService:
    """Background service to run DeepEval and store results in the DB."""

    @staticmethod
    def run_live_eval(cache_id: str, input_text: str, actual_output: str, retrieval_context: list[str]):
        """Run DeepEval metrics and save to DB."""
        print(f"🔍 Starting background DeepEval for cache_id: {cache_id}")

        # Setup initial DB record
        db = SessionLocal()
        try:
            # Create or update pending record
            eval_record = db.query(EvalMetrics).filter(EvalMetrics.cache_id == cache_id).first()
            if not eval_record:
                eval_record = EvalMetrics(cache_id=cache_id, status="running")
                db.add(eval_record)
            else:
                eval_record.status = "running"
            db.commit()

            # Setup metrics (we skip the custom wrapper here for simplicity if litellm covers it,
            # or we assume OPENAI_API_KEY is set or DeepEval can fallback).
            # In a real setup, we'd inject our custom Gemini wrapper here too.
            # For hackathon robust presentation, we will just use the default DeepEval setup
            # which will use OpenAI if key is present, otherwise we'd use our wrapper.
            # To ensure it runs, let's use the explicit Gemini Wrapper.

            # pylint: disable=import-outside-toplevel
            from scripts.run_golden_evals import GeminiDeepEvalWrapper
            custom_model = GeminiDeepEvalWrapper()

            faithfulness = FaithfulnessMetric(threshold=0.7, model=custom_model, include_reason=True)
            answer_relevancy = AnswerRelevancyMetric(threshold=0.7, model=custom_model, include_reason=True)
            hallucination = HallucinationMetric(threshold=0.7, model=custom_model, include_reason=True)

            test_case = LLMTestCase(
                input=input_text,
                actual_output=actual_output,
                retrieval_context=retrieval_context,
                context=retrieval_context
            )

            print("⏳ DeepEval evaluate() running...")
            # evaluate() returns a list of TestResult objects
            _results = evaluate([test_case], [faithfulness, answer_relevancy, hallucination], print_results=False)

            # Extract scores and reasoning from the metrics explicitly since evaluate() aggregates them
            eval_record.faithfulness_score = faithfulness.score
            eval_record.faithfulness_reasoning = faithfulness.reason

            eval_record.answer_relevance_score = answer_relevancy.score
            eval_record.answer_relevance_reasoning = answer_relevancy.reason

            eval_record.hallucination_score = hallucination.score
            eval_record.hallucination_reasoning = hallucination.reason

            eval_record.status = "completed"
            db.commit()
            print(f"✅ Background DeepEval completed for: {cache_id}")

        except Exception as e: # pylint: disable=broad-exception-caught
            print(f"⚠️ Background DeepEval failed: {e}")
            if eval_record:
                eval_record.status = "failed"
                eval_record.faithfulness_reasoning = f"Error: {e}"
                db.commit()
        finally:
            db.close()
