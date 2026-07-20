import os
import json
import asyncio
from dotenv import load_dotenv

load_dotenv(override=True)  # override=True ensures .env is always re-read fresh

USE_GROQ = os.getenv("USE_GROQ", "false").lower() == "true"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")


class GPTService:
    """
    Unified AI service that supports both OpenAI and Groq.
    Set USE_GROQ=true in .env to use Groq (llama) for development.
    Set USE_GROQ=false for production with OpenAI GPT-5.6-luna.
    """

    def __init__(self):
        self.use_groq = USE_GROQ
        if self.use_groq:
            self._init_groq()
        else:
            self._init_openai()

    def _init_groq(self):
        try:
            from groq import AsyncGroq
            self.client = AsyncGroq(api_key=GROQ_API_KEY, timeout=20.0)
            self.groq_models = [
                "llama-3.1-8b-instant",
                "llama-3.3-70b-versatile",
                "qwen/qwen3.6-27b",
                "openai/gpt-oss-20b",
                "groq/compound-mini"
            ]
            self.model = self.groq_models[0]
            print(f"[GPTService] Using Groq: {self.model}")
        except ImportError:
            print("[GPTService] Groq not installed, falling back to OpenAI")
            self.use_groq = False
            self._init_openai()

    def _init_openai(self):
        try:
            from openai import AsyncOpenAI
            self.client = AsyncOpenAI(api_key=OPENAI_API_KEY, timeout=20.0)
            self.openai_models = ["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo"]
            self.model = self.openai_models[0]
            print(f"[GPTService] Using OpenAI: {self.model}")
        except ImportError:
            print("[GPTService] OpenAI not installed")
            self.client = None

    async def call(self, prompt: str, system: str = "") -> str:
        """Call AI and return raw text response."""
        if not self.client:
            return "AI service unavailable. Please configure API keys."

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        return await self.call_messages(messages)

    async def call_messages(self, messages: list, temperature: float = 0.7) -> str:
        """Call AI with automatic fallback across multiple models if rate limits (429) or errors occur."""
        if not self.client:
            return "AI service unavailable. Please configure API keys."

        models_to_try = []
        if self.use_groq and self.client:
            groq_list = getattr(self, "groq_models", [
                "llama-3.1-8b-instant",
                "llama-3.3-70b-versatile",
                "qwen/qwen3.6-27b",
                "openai/gpt-oss-20b",
                "groq/compound-mini"
            ])
            models_to_try = [self.model] + [m for m in groq_list if m != self.model]
        elif not self.use_groq and self.client:
            openai_list = getattr(self, "openai_models", ["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo"])
            models_to_try = [self.model] + [m for m in openai_list if m != self.model]
        else:
            models_to_try = [self.model]

        last_err = None
        for model_name in models_to_try:
            try:
                response = await asyncio.wait_for(
                    self.client.chat.completions.create(
                        model=model_name,
                        messages=messages,
                        temperature=temperature,
                        max_tokens=4096,
                    ),
                    timeout=20.0
                )
                if model_name != self.model:
                    print(f"[GPTService] Switched active model to: {model_name}")
                    self.model = model_name
                return response.choices[0].message.content or ""
            except Exception as e:
                print(f"[GPTService] Model {model_name} failed ({type(e).__name__}): {e}")
                last_err = e
                continue

        # If all Groq models failed, attempt fallback to OpenAI if API key exists
        if self.use_groq and OPENAI_API_KEY:
            print("[GPTService] All Groq models failed. Attempting automatic fallback to OpenAI client...")
            try:
                from openai import AsyncOpenAI
                openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY, timeout=20.0)
                for openai_model in ["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo"]:
                    try:
                        response = await asyncio.wait_for(
                            openai_client.chat.completions.create(
                                model=openai_model,
                                messages=messages,
                                temperature=temperature,
                                max_tokens=4096,
                            ),
                            timeout=20.0
                        )
                        print(f"[GPTService] Switched over to OpenAI model: {openai_model}")
                        self.client = openai_client
                        self.use_groq = False
                        self.model = openai_model
                        return response.choices[0].message.content or ""
                    except Exception as ex:
                        print(f"[GPTService] OpenAI model {openai_model} failed: {ex}")
                        last_err = ex
            except Exception as ex:
                last_err = ex

        raise RuntimeError(f"AI call failed on all available fallback models. Last error: {str(last_err)}")

    async def call_json(self, prompt: str, system: str = "") -> dict:
        """Call AI and parse JSON response. Retries once on parse failure."""
        multilingual_instruction = (
            "LANGUAGE RULE: The user may write in ANY language — Urdu, Roman Urdu, Hindi, Arabic, "
            "English, or any other language. You MUST understand the input in whatever language it is "
            "written. ALWAYS respond in English JSON only. Never reject input due to language.\n\n"
        )
        json_system = multilingual_instruction + (system or "") + (
            "\n\nIMPORTANT: You MUST return ONLY valid JSON. "
            "No markdown, no code blocks, no explanation. Pure JSON only."
        )

        for attempt in range(2):
            raw = await self.call(prompt, json_system)
            # Strip markdown code blocks if present
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                lines = cleaned.split("\n")
                # Remove first and last lines (``` markers)
                lines = lines[1:] if lines[0].startswith("```") else lines
                lines = lines[:-1] if lines and lines[-1].strip() == "```" else lines
                cleaned = "\n".join(lines)
            try:
                return json.loads(cleaned)
            except json.JSONDecodeError as e:
                print(f"[GPTService] JSON parse attempt {attempt + 1} failed: {e}")
                if attempt == 0:
                    # Retry with stricter prompt
                    prompt = prompt + "\n\nCRITICAL: Your previous response was not valid JSON. Return ONLY the JSON object, nothing else."
                    await asyncio.sleep(1)
                else:
                    raise ValueError(f"AI returned invalid JSON after 2 attempts: {raw[:200]}")

        return {}


# Singleton instance
gpt_service = GPTService()
