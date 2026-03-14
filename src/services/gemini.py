"""
Gemini integration for textual generation and reasoning.
"""
# pylint: disable=import-error,no-name-in-module,broad-exception-caught
from typing import Protocol, Any
import os
import json
import vertexai
from vertexai.generative_models import GenerativeModel


class LLMProvider(Protocol):
    """Abstract protocol for Foundation Models."""

    def generate_content(self, prompt: str) -> str:
        """Generate text content from prompt."""

    def analyze_context(self, state: Any) -> dict:
        """Analyze context state and return insights."""


class GeminiService(LLMProvider):
    """
    Concrete implementation of Gemini 1.5 Flash.
    Leverages LangGraph orchestration for structural reasoning.
    """

    def __init__(self, credentials_path: str = None):
        self.credentials_path = credentials_path or os.environ.get(
            "GEMINI_VERTEX_AI_CREDENTIALS")
        self.is_mocked = False

        if self.credentials_path:
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = self.credentials_path
            try:
                with open(self.credentials_path, 'r', encoding='utf-8') as f:
                    creds_data = json.load(f)
                    project_id = creds_data.get('project_id')
                vertexai.init(project=project_id, location="us-central1")
                self.model = GenerativeModel("gemini-2.0-flash-001")
            except Exception as e:
                print(f"WARNING: Failed to initialize Vertex AI: {e}")
                self.model = None
                self.is_mocked = True
        else:
            print("WARNING: GEMINI_VERTEX_AI_CREDENTIALS not found. "
                  "GeminiService API calls will fail.")
            self.model = None
            self.is_mocked = True

    def generate_content(self, prompt: str) -> str:
        """Generate text using Gemini."""
        if self.is_mocked:
            return "Gemini 1.5 Flash synthesized content. (Mocked - No Credentials)"
        response = self.model.generate_content(prompt)
        return response.text

    def analyze_context(self, state: Any) -> dict:
        """Analyze agent state using Gemini reasoning capabilities."""
        if self.is_mocked:
            return {
                "reasoning": "Gemini reasoning logs applied. (Mock)",
                "safety_passed": True
            }

        prompt = (
            "You are a Safety Critic evaluating a generated daily briefing draft. "
            "Check for the following criteria:\n"
            "1. PII/Safety: No highly sensitive personal data exposed unsafely.\n"
            "2. Grounding: The draft must accurately reflect the provided source "
            "context without hallucinations.\n"
            "3. Tone: The tone must be strictly professional and concise.\n\n"
            f"Draft Briefing: {state}\n\n"
            "Respond ONLY with a valid JSON object in this format (no markdown tags): "
            '{"safety_passed": true/false, '
            '"feedback": "Detailed reasoning or instructions for rewrite"}'
        )
        try:
            response = self.model.generate_content(prompt)
            # Remove any possible markdown block formatting from the response
            cleaned_text = response.text.replace('```json', '').replace('```', '').strip()
            result = json.loads(cleaned_text)
            return {
                "reasoning": result.get("feedback", "No feedback provided."),
                "safety_passed": result.get("safety_passed", False)
            }
        except Exception as e:
            print(f"⚠️ Critic parsing failed: {e}. Defaulting to fail.")
            return {"reasoning": f"Parsing error: {e}", "safety_passed": False}
