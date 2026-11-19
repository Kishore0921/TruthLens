from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from backend.config import DATABASE_URL, ORIGINALS_DIR, PROCESSED_DIR, REPORTS_DIR

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    from backend import models  # noqa
    Base.metadata.create_all(bind=engine)
    for d in [ORIGINALS_DIR, PROCESSED_DIR, REPORTS_DIR]:
        d.mkdir(parents=True, exist_ok=True)
