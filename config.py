import os

from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://127.0.0.1:27017")
MONGO_DB = os.getenv("MONGO_DB", "s0571_doc")

SHORT_TERM_N = int(os.getenv("SHORT_TERM_N", "12"))
SUMMARIZE_EVERY_USER_MSGS = int(os.getenv("SUMMARIZE_EVERY_USER_MSGS", "5"))
LIFETIME_EVERY_SUMMARIES = int(os.getenv("LIFETIME_EVERY_SUMMARIES", "2"))
TOP_K_EPISODES = int(os.getenv("TOP_K_EPISODES", "4"))
MAX_FACTS_PER_MESSAGE = 3
CHAT_LOG = os.getenv("CHAT_LOG", "reports/hw06/raw/chat_log.csv")

AGENT_FILE = "AGENT.md"
MEMORY_FILE = "MEMORY.md"
MEMORY_MAX_LINES = 40
MEMORY_MAX_AGE_HOURS = 24

JWT_SECRET = os.getenv("JWT_SECRET", "s0571-local-dev-secret")
JWT_ALGORITHM = "HS256"
TOKEN_MINUTES = int(os.getenv("TOKEN_MINUTES", "30"))
ROLES = ("reader", "writer", "moderator")
