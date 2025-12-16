import os
from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()

def get_llm_client():
    provider = os.getenv("LLM_PROVIDER", "longcat")

    if provider == "longcat":
        api_key = os.getenv("LONGCAT_API_KEY")
        base_url = os.getenv("LONGCAT_BASE_URL")
        model = os.getenv("LONGCAT_MODEL")

        if not api_key:
            raise RuntimeError("LONGCAT_API_KEY not set in .env")

        return (
            OpenAI(
                api_key=api_key,
                base_url=base_url,
            ),
            model,
        )

    elif provider == "openrouter":
        api_key = os.getenv("OPENROUTER_API_KEY")
        model = os.getenv("OPENROUTER_MODEL")

        if not api_key:
            raise RuntimeError("OPENROUTER_API_KEY not set in .env")

        return (
            OpenAI(
                api_key=api_key,
                base_url="https://openrouter.ai/api/v1",
            ),
            model,
        )

    else:
        raise ValueError(f"Unsupported LLM_PROVIDER: {provider}")
