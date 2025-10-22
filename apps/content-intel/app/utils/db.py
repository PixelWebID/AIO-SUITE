"""Database connectivity stubs."""

from typing import Any, Dict


async def get_connection() -> None:
    """
    Placeholder for the real database connection pool.

    The production service will connect to Postgres or AlloyDB. We return None so
    callers can stub logic without failing imports.
    """

    return None


async def log_generation_job(payload: Any, response: Any) -> None:
    """Persist metadata about a generation job (no-op skeleton)."""

    print("log_generation_job", {"keyword": getattr(payload, "keyword", None)})


async def log_gap_job(payload: Any, response: Any, *, trends: Any = None) -> None:
    """Persist metadata about content gap analysis jobs."""

    print(
        "log_gap_job",
        {
            "keyword": getattr(payload, "keyword", None),
            "trends": trends or [],
        },
    )
