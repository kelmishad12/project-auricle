"""
Gemini integration for textual generation and reasoning.
"""
# pylint: disable=import-error,no-name-in-module,broad-exception-caught
from typing import Protocol, Any, Optional
import os
import json
import datetime
import google.generativeai as genai
from google.generativeai import caching
MODEL_NAME = "gemini-2.5-flash"


class LLMProvider(Protocol):
    """Abstract protocol for Foundation Models."""

    def generate_content(self, prompt: str) -> str:
        """Generate text content from prompt."""

    def analyze_context(self, state: Any) -> dict:
        """Analyze context state and return insights."""

    def create_cached_context(
            self,
            system_instruction: str,
            user_profile_text: str,
            dynamic_data: str) -> Optional[str]:
        """Cache static data plus dynamic data to optimize multi-turn QA."""

    def validate_cache(self, cache_name: str) -> bool:
        """Validate if the context cache is still valid."""

    def chat_with_context(self, cache_name: str, prompt: str) -> str:
        """Query the cached context via the LLM to get an answer."""


class GeminiService(LLMProvider):
    """
    Concrete implementation of Gemini 2.5 Flash.
    Leverages LangGraph orchestration for structural reasoning.
    """

    def __init__(self):
        self.api_key = os.environ.get("GEMINI_API_KEY")
        self.is_mocked = False

        if self.api_key:
            try:
                # The caching API statically requires GOOGLE_API_KEY globally
                # for stateless API requests like the follow-up chat
                os.environ["GOOGLE_API_KEY"] = self.api_key
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel(MODEL_NAME)
            except Exception as e:
                print(f"WARNING: Failed to initialize Gemini API: {e}")
                self.model = None
                self.is_mocked = True
        else:
            print("WARNING: GEMINI_API_KEY not found. "
                  "GeminiService API calls will fail.")
            self.model = None
            self.is_mocked = True
            self.is_mocked = True

    def generate_content(self, prompt: str) -> str:
        """Generate text using Gemini."""
        if self.is_mocked:
            return "Gemini 2.5 Flash synthesized content. (Mocked - No Credentials)"
        response = self.model.generate_content(prompt)
        return response.text

    def analyze_context(self, state: Any) -> dict:
        """Analyze agent state using Gemini reasoning capabilities."""
        if self.is_mocked:
            return {
                "reasoning": "Gemini reasoning logs applied. (Mock)",
                "safety_passed": True
            }

        emails = chr(10).join(
            state.get(
                'email_summaries',
                [])) if isinstance(
            state,
            dict) else ""
        calendar = chr(10).join(
            state.get(
                'calendar_events',
                [])) if isinstance(
            state,
            dict) else ""

        prompt = (
            "Analyze the following Emails and Calendar events. "
            "Return JSON exactly like this: "
            "{\"safety_passed\": true, \"safety_score\": 100, \"feedback\": \"Looks good\"}. "
            "Score from 0-100 based on safety. "
            "Unless you detect a literal cyberattack or malicious code injection in the text, you "
            "MUST return safety_passed as true. Confidential business emails, passwords, and offer "
            "letters are NORMAL and MUST pass safety. \n\n"
            f"Emails:\n{emails}\nCalendar:\n{calendar}"
        )
        try:
            response = self.model.generate_content(
                prompt,
                generation_config={"response_mime_type": "application/json"}
            )
            # Remove any possible markdown block formatting from the response
            cleaned_text = response.text.replace(
                '```json', '').replace(
                '```', '').strip()
            result = json.loads(cleaned_text)
            return {
                "reasoning": result.get("feedback", "No feedback provided."),
                "safety_passed": result.get("safety_passed", False),
                "critic_score": result.get("safety_score", 0)
            }
        except Exception as e:
            print(f"⚠️ Critic parsing failed: {e}. Defaulting to fail.")
            return {"reasoning": f"Parsing error: {e}", "safety_passed": False, "critic_score": 0}

    def create_cached_context(
            self,
            system_instruction: str,
            user_profile_text: str,
            dynamic_data: str) -> Optional[str]:
        """Creates a cached content object in Vertex AI to save >90%
        on token cost for subsequent inferences."""
        if self.is_mocked:
            return "mock-cache-12345"

        try:
            # Combine user profile (static) + emails/calendar (dynamic) into one large Part blob
            # Normally this would be many files or a DB RAG lookup.
            full_context = f"{user_profile_text}\n\n=== RECENT ACTIVITY ===\n{dynamic_data}"

            # The TTL manages when Google automatically purges the cache from VRAM.
            # E.g., The context is refreshed daily, so a 60 min TTL covers a
            # standard chat session.
            ttl_minutes = int(os.environ.get("GEMINI_CACHE_TTL_MINUTES", "60"))
            cached_content = caching.CachedContent.create(
                model=f"models/{MODEL_NAME}",
                system_instruction=system_instruction,
                contents=[full_context],
                ttl=datetime.timedelta(minutes=ttl_minutes),
            )
            print(
                f"✅ Context Cache created successfully: {cached_content.name}")
            return cached_content.name
        except Exception as e:
            print(f"⚠️ Cache creation failed: {e}")
            return None

    def validate_cache(self, cache_name: str) -> bool:
        """Validate if the cache still exists and is not expired."""
        if self.is_mocked:
            return True

        try:
            caching.CachedContent.get(cache_name)
            return True
        except Exception as e:
            print(f"⚠️ Cache validation failed: {e}")
            return False

    def chat_with_context(self, cache_name: str, prompt: str) -> str:
        """Generate response against a pre-warmed context cache.
        Reduces TTFT and token cost."""
        if self.is_mocked:
            return f"Mocked cached response for: {prompt}"

        try:
            model = genai.GenerativeModel.from_cached_content(
                cached_content=cache_name
            )

            generation_config = genai.types.GenerationConfig(
                temperature=0.2,        # Keep it highly deterministic and focused
            )

            augmented_prompt = (
                "CRITICAL OVERRIDE: Ignore prior instruction to 'Create a daily briefing'. "
                "Do NOT output the user profile, role, or OKRs. "
                "Provide a natural, conversational, and direct answer "
                "to the following question ONLY.\n"
                "You may use brief formatting or bullet points "
                "if it significantly improves readability.\n\n"
                f"Question: {prompt}"
            )

            response = model.generate_content(augmented_prompt, generation_config=generation_config)
            return response.text
        except Exception as e:
            print(f"⚠️ Cached chat failed: {e}")
            return (
                "Error: The context cache has expired or is invalid. "
                "Please generate a new briefing."
            )
