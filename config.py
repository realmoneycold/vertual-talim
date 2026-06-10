import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "8841689690:AAEhSoesoSM289Wt8FLydCbkDenbs47ruyI")
    WEBAPP_URL: str = os.getenv("WEBAPP_URL", "https://gleaming-frangipane-336680.netlify.app/")
    DB_FILE: str = os.getenv("DB_FILE", "database.db")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    

    ADMIN_IDS: list[int] = [8978922616]  # Main admin

    @classmethod
    def validate(cls):
        if not cls.BOT_TOKEN:
            raise ValueError("BOT_TOKEN is not set in environment variables.")
        if not cls.ADMIN_IDS:
            raise ValueError("ADMIN_IDS is not set or invalid in environment variables.")
