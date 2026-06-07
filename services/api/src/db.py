import os
import psycopg_pool

_pool: psycopg_pool.AsyncConnectionPool | None = None

DSN = (
    f"host={os.getenv('POSTGRES_HOST', 'timescaledb')} "
    f"port={os.getenv('POSTGRES_PORT', '5432')} "
    f"dbname={os.getenv('POSTGRES_DB', 'oliveoil')} "
    f"user={os.getenv('POSTGRES_USER', 'oliveoil_app')} "
    f"password={os.getenv('POSTGRES_PASSWORD', '')}"
)


async def create_pool() -> None:
    global _pool
    _pool = psycopg_pool.AsyncConnectionPool(DSN, min_size=2, max_size=10, open=False)
    await _pool.open()


async def close_pool() -> None:
    if _pool:
        await _pool.close()


async def get_db():
    """FastAPI dependency — yields one connection from the pool per request."""
    async with _pool.connection() as conn:
        yield conn


def get_pool() -> psycopg_pool.AsyncConnectionPool:
    """Direct pool access for WebSocket handlers."""
    return _pool
