from src.db import engine
from src.models import Base

print("[INFO] Creating tables...")

Base.metadata.create_all(engine)

print("✅ Tables created!")
