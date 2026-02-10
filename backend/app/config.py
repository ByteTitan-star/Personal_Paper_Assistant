from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Personal Scholar Agent API"
    api_prefix: str = "/api"
    data_dir: str = "data"
    templates_dir: str = "templates"
    cors_origins: str = "*"
    max_chunk_chars: int = 900
    chunk_overlap: int = 120
    llm_model_name: str = "DemoPipeline-v1"
    embedding_model_name: str = "TokenOverlapRetriever-v1"
    model_provider: str = "LocalRuleEngine"
    pipeline_mode: str = "DeterministicDraft"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def cors_origin_list(self) -> list[str]:
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
