import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    WEBAPP_URL: str = os.getenv("WEBAPP_URL", "https://gleaming-frangipane-336680.netlify.app/")
    DB_FILE: str = os.getenv("DB_FILE", "database.db")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "") # Neon PostgreSQL Connection URI
    
    # Parse list of integers from comma-separated string
    ADMIN_IDS: list[int] = [
        int(x.strip()) 
        for x in os.getenv("ADMIN_IDS", "").split(",") 
        if x.strip().isdigit()
    ]

    @classmethod
    def validate(cls):
        if not cls.BOT_TOKEN:
            raise ValueError("BOT_TOKEN is not set in environment variables.")
        if not cls.ADMIN_IDS:
            raise ValueError("ADMIN_IDS is not set or invalid in environment variables.")
