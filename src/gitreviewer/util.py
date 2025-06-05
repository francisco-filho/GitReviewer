import os
import logging
from dotenv import load_dotenv

load_dotenv(override=True)

logging.basicConfig(level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.ERROR)
logger = logging.getLogger("gitreviewer")

DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "gemini-2.5-flash-preview-05-20")
