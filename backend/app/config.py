from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "mysql+pymysql://root:password@localhost:3306/prs01"
    SECRET_KEY: str = "change-this-secret-key-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480
    UPLOAD_DIR: str = "uploads"
    COOKIE_1688: str = ""
    PROXY_URL: str = ""  # HTTP proxy for scraping, e.g. http://user:pass@host:port
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://ai.t8star.org/v1"
    DOUBAO_API_KEY: str = ""
    DOUBAO_BASE_URL: str = "https://ark.volces.com/api/v3"
    DOUBAO_MODEL: str = ""
    DOUBAO_PROMPT: str = ""

    class Config:
        env_file = ".env"

settings = Settings()
