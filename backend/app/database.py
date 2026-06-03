from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import settings
from contextlib import contextmanager
import os

# Создаем директорию для базы данных, если её нет
db_dir = os.path.dirname(settings.database_url.replace("sqlite:///", ""))
if db_dir and not os.path.exists(db_dir):
    os.makedirs(db_dir, exist_ok=True)

is_sqlite = "sqlite" in settings.database_url

# Настройки пула соединений.
# По умолчанию у файлового SQLite используется QueuePool (pool_size=5, max_overflow=10).
# Этого не хватает, т.к. webhook/обновления держат соединение во время долгих
# вызовов к Bitrix24 — пул исчерпывается и запросы падают по таймауту.
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if is_sqlite else {},
    pool_size=20,
    max_overflow=40,
    pool_timeout=30,
    pool_recycle=1800,
    pool_pre_ping=True,
)

if is_sqlite:
    # WAL + busy_timeout позволяют одновременно читать и писать без "database is locked"
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=30000")
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency для получения сессии базы данных"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def session_scope(expire_on_commit: bool = False):
    """
    Короткоживущая сессия БД с автоматическим commit/rollback/close.

    Использовать для коротких операций чтения/записи, чтобы не удерживать
    соединение из пула во время длительных сетевых вызовов (например, к Bitrix24).
    expire_on_commit=False позволяет обращаться к атрибутам объектов после выхода
    из блока (объекты остаются заполненными после commit/close).
    """
    db = SessionLocal(expire_on_commit=expire_on_commit)
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
