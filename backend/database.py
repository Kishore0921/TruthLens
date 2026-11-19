import sqlite3
from sqlalchemy import create_engine, inspect
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

def _run_sqlite_migrations():
    """Safely apply schema migrations to preserve existing investigation records."""
    # Check if SQLite file
    db_file = DATABASE_URL.replace("sqlite:///", "")
    try:
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()

        # Check existing columns in investigations
        cursor.execute("PRAGMA table_info(investigations);")
        inv_cols = [row[1] for row in cursor.fetchall()]
        if inv_cols:
            if "structured_facts_json" not in inv_cols:
                cursor.execute("ALTER TABLE investigations ADD COLUMN structured_facts_json TEXT DEFAULT '{}';")
            if "ai_enabled" not in inv_cols:
                cursor.execute("ALTER TABLE investigations ADD COLUMN ai_enabled BOOLEAN DEFAULT 0;")
            if "ai_provider" not in inv_cols:
                cursor.execute("ALTER TABLE investigations ADD COLUMN ai_provider VARCHAR DEFAULT 'gemini';")

        # Check existing columns in correlations
        cursor.execute("PRAGMA table_info(correlations);")
        corr_cols = [row[1] for row in cursor.fetchall()]
        if corr_cols:
            if "source_evidence_id" not in corr_cols:
                cursor.execute("ALTER TABLE correlations ADD COLUMN source_evidence_id VARCHAR;")
            if "target_evidence_id" not in corr_cols:
                cursor.execute("ALTER TABLE correlations ADD COLUMN target_evidence_id VARCHAR;")
            if "limitations_json" not in corr_cols:
                cursor.execute("ALTER TABLE correlations ADD COLUMN limitations_json TEXT DEFAULT '[]';")

        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Migration notice: {e}")

def init_db():
    from backend import models  # noqa
    Base.metadata.create_all(bind=engine)
    _run_sqlite_migrations()
    
    # Ensure default AI provider configs exist if not already present
    db = SessionLocal()
    try:
        from backend.models import AIProviderConfig
        from backend.config import GEMINI_DEFAULT_MODEL, OPENAI_DEFAULT_MODEL
        for pid, name, model in [
            ("gemini", "Google Gemini", GEMINI_DEFAULT_MODEL),
            ("openai", "OpenAI", OPENAI_DEFAULT_MODEL),
            ("anthropic", "Anthropic Claude", "claude-3-5-sonnet-20241022"),
            ("huggingface", "Hugging Face Inference", "meta-llama/Llama-3.2-3B-Instruct")
        ]:
            existing = db.query(AIProviderConfig).filter(AIProviderConfig.id == pid).first()
            if not existing:
                cfg = AIProviderConfig(
                    id=pid,
                    provider_name=name,
                    selected_model=model,
                    connection_status="not_configured"
                )
                db.add(cfg)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Provider seed notice: {e}")
    finally:
        db.close()

    for d in [ORIGINALS_DIR, PROCESSED_DIR, REPORTS_DIR]:
        d.mkdir(parents=True, exist_ok=True)
