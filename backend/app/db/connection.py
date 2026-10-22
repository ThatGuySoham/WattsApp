"""PostgreSQL connection pool (psycopg 3)."""
from contextlib import contextmanager
from pathlib import Path

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from app.config import DATABASE_URL

pool = ConnectionPool(
    conninfo=DATABASE_URL,
    min_size=1,
    max_size=5,
    open=False,
    kwargs={"row_factory": dict_row},
    # Neon computes may scale to zero; check connections before handing them out.
    check=ConnectionPool.check_connection,
)


def open_pool() -> None:
    pool.open(wait=True, timeout=60)


def close_pool() -> None:
    pool.close()


@contextmanager
def get_conn():
    """Yield a pooled connection; commits on success, rolls back on error."""
    with pool.connection() as conn:
        yield conn


def apply_schema() -> None:
    sql = (Path(__file__).parent / "schema.sql").read_text(encoding="utf-8")
    with get_conn() as conn:
        conn.execute(sql)
