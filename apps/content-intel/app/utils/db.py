"""SQLAlchemy helpers for persisting article metadata and logs."""

from __future__ import annotations

import json
from contextlib import contextmanager
from datetime import datetime
from typing import Dict, Iterable, List, Optional

from sqlalchemy import JSON, Column, DateTime, Integer, String, Text, create_engine, func
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker

from ..config import settings

Base = declarative_base()
EngineSingleton: Optional[Engine] = None
SessionLocal: Optional[sessionmaker] = None


class ArticleRecord(Base):
    __tablename__ = 'aio_articles'

    id = Column(Integer, primary_key=True)
    history_id = Column(String(64), unique=True, nullable=False)
    keyword = Column(String(255), nullable=False)
    geo = Column(String(16), nullable=False)
    tone = Column(String(32), nullable=False)
    status = Column(String(32), default='draft')
    article_html = Column(Text)
    meta_json = Column(JSON)
    metrics_json = Column(JSON)
    warnings_json = Column(JSON)
    simhash = Column(String(32))
    checksum_sha1 = Column(String(64))
    created_at = Column(DateTime, default=datetime.utcnow)


class ReferenceRecord(Base):
    __tablename__ = 'aio_refs'

    id = Column(Integer, primary_key=True)
    article_history_id = Column(String(64), nullable=False)
    title = Column(Text)
    url = Column(Text)
    snippet = Column(Text)
    domain = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)


class LogRecord(Base):
    __tablename__ = 'aio_logs'

    id = Column(Integer, primary_key=True)
    history_id = Column(String(64), nullable=True)
    level = Column(String(16), default='info')
    message = Column(Text)
    payload_json = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)


class APIKeyRecord(Base):
    __tablename__ = 'aio_api_keys'

    id = Column(Integer, primary_key=True)
    provider = Column(String(64), unique=True, nullable=False)
    key_encrypted = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


def init_engine() -> None:
    global EngineSingleton, SessionLocal
    if EngineSingleton is not None:
        return
    database_url = settings.database_url or 'sqlite:///./content_intel.sqlite3'
    EngineSingleton = create_engine(database_url, echo=False, future=True)
    SessionLocal = sessionmaker(bind=EngineSingleton, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(EngineSingleton)


@contextmanager
def session_scope() -> Iterable[Session]:
    if SessionLocal is None:
        init_engine()
    session: Session = SessionLocal()  # type: ignore
    try:
        yield session
        session.commit()
    except SQLAlchemyError:
        session.rollback()
        raise
    finally:
        session.close()


def store_article(history_id: str, keyword: str, geo: str, tone: str, html: str, meta: Dict, metrics: Dict, warnings: List[str]) -> None:
    record = ArticleRecord(
        history_id=history_id,
        keyword=keyword,
        geo=geo,
        tone=tone,
        article_html=html,
        meta_json=meta,
        metrics_json=metrics,
        warnings_json=warnings,
        simhash=metrics.get('simhash'),
        checksum_sha1=metrics.get('checksum_sha1'),
    )
    with session_scope() as session:
        session.merge(record)


def store_references(history_id: str, references: List[Dict]) -> None:
    rows = []
    now = datetime.utcnow()
    for ref in references:
        rows.append(
            ReferenceRecord(
                article_history_id=history_id,
                title=ref.get('title'),
                url=ref.get('url'),
                snippet=ref.get('snippet'),
                domain=ref.get('domain'),
                created_at=now,
            )
        )
    if not rows:
        return
    with session_scope() as session:
        session.query(ReferenceRecord).filter(ReferenceRecord.article_history_id == history_id).delete()
        session.add_all(rows)


def log_event(history_id: Optional[str], level: str, message: str, payload: Optional[Dict] = None) -> None:
    row = LogRecord(
        history_id=history_id,
        level=level,
        message=message,
        payload_json=payload or {},
    )
    with session_scope() as session:
        session.add(row)


def fetch_recent_simhashes(limit: int = 50) -> List[Dict[str, str]]:
    with session_scope() as session:
        rows = (
            session.query(ArticleRecord.history_id, ArticleRecord.simhash)
            .filter(ArticleRecord.simhash.isnot(None))
            .order_by(ArticleRecord.created_at.desc())
            .limit(limit)
            .all()
        )
        return [dict(history_id=row[0], simhash=row[1]) for row in rows]


def fetch_existing_keywords() -> List[str]:
    with session_scope() as session:
        rows = session.query(func.distinct(ArticleRecord.keyword)).all()
    return [row[0] for row in rows if row[0]]


def fetch_latest_articles(limit: int = 50) -> List[Dict[str, object]]:
    with session_scope() as session:
        rows = (
            session.query(
                ArticleRecord.history_id,
                ArticleRecord.keyword,
                ArticleRecord.geo,
                ArticleRecord.meta_json,
                ArticleRecord.metrics_json,
            )
            .order_by(ArticleRecord.created_at.desc())
            .limit(limit)
            .all()
        )
    results: List[Dict[str, object]] = []
    for history_id, keyword, geo, meta, metrics in rows:
        results.append(
            {
                "history_id": history_id,
                "keyword": keyword,
                "geo": geo,
                "meta": meta or {},
                "metrics": metrics or {},
            }
        )
    return results


def save_api_key(provider: str, key_encrypted: str) -> None:
    record = APIKeyRecord(provider=provider, key_encrypted=key_encrypted)
    with session_scope() as session:
        session.merge(record)


def load_api_key(provider: str) -> Optional[str]:
    with session_scope() as session:
        record: Optional[APIKeyRecord] = (
            session.query(APIKeyRecord)
            .filter(APIKeyRecord.provider == provider)
            .one_or_none()
        )
    return record.key_encrypted if record else None
