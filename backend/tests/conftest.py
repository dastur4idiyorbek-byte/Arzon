"""Test sozlamalari — muhit o'zgaruvchilari app import'idan OLDIN o'rnatiladi."""
import os
import tempfile

# Settings import paytida keshlanadi — shuning uchun bu yerda, eng boshda.
_db_fd, _db_path = tempfile.mkstemp(suffix=".db")
os.environ["DATABASE_URL"] = f"sqlite:///{_db_path}"
os.environ["MINIAPP_BOT_TOKEN"] = "TEST:BOT-TOKEN-123"
os.environ["SAVDO_BOT_TOKEN"] = "TEST:BOT-TOKEN-123"
os.environ["INTERNAL_API_TOKEN"] = "internal-secret-xyz"
os.environ["SUPER_ADMIN_IDS"] = "999999"
os.environ["MENEJER_IDS"] = "777777"
os.environ["JWT_SECRET"] = "test-jwt-secret"
os.environ["SUPER_ADMIN_EMAILS"] = "boss@arzon.kg"
os.environ["MENEJER_EMAILS"] = "menejer@arzon.kg"
os.environ["ANTHROPIC_API_KEY"] = ""  # AI zaxira javob rejimida

# Jadvallarni yaratamiz (TestClient lifespan'siz ishlatilishi mumkin).
from app.database import init_db  # noqa: E402

init_db()
