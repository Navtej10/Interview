from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    llm_provider: str = "anthropic"

    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-6"

    groq_api_key: str = ""
    groq_model: str = "llama3-8b-8192"

    openai_api_key: str = ""
    openai_model: str = "gpt-4o"

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen3:8b"

    frontend_origin: str = "http://localhost:5173"
    
    liveportrait_reference_face: str = "assets/default_face.jpg"
    # Memory configurations
    short_term_window: int = 6
    
    # Termination and struggle policies
    max_consecutive_weak: int = 3
    max_consecutive_irrelevant: int = 2
    max_consecutive_non_answers: int = 2
    max_recovery_attempts: int = 2

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
