"""FastAPI application entry point.

Initializes the TOR Drafting and Review API with:
- Async lifespan handler (DB pool, Redis, MinIO)
- CORS middleware (configurable frontend origin)
- Request ID injection middleware
- Request logging middleware
- API v1 router
"""

import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.v1.endpoints import health as health_endpoints
from app.api.v1.router import api_router
from app.config import get_settings
from app.exception_handlers import register_exception_handlers

logger = logging.getLogger("tor_app")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)


# -----------------------------------------------------------------------------
# Lifespan: manage shared resources (DB engine, Redis, MinIO)
# -----------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler.

    On startup: create async DB engine + sessionmaker, Redis client, MinIO client.
    On shutdown: dispose engine, close Redis.
    Gracefully handles missing services (logs warnings but still starts).
    """
    settings = get_settings()

    # --- Database ---
    try:
        engine = create_async_engine(
            settings.database_url,
            pool_size=20,
            max_overflow=10,
            echo=False,
        )
        session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        app.state.db_engine = engine
        app.state.db_session_factory = session_factory
        from app.infra import set_session_factory

        set_session_factory(session_factory)
        logger.info("Database engine created: %s", settings.postgres_host)
    except Exception as exc:
        logger.warning("Failed to create database engine: %s", exc)
        app.state.db_engine = None
        app.state.db_session_factory = None
        from app.infra import set_session_factory as _clear_sf

        _clear_sf(None)

    # --- Redis ---
    try:
        import redis.asyncio as aioredis

        redis_client = aioredis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=5,
        )
        # Verify connectivity with a ping
        await redis_client.ping()
        app.state.redis = redis_client
        logger.info("Redis connected: %s:%d", settings.redis_host, settings.redis_port)
    except Exception as exc:
        logger.warning("Redis not reachable (app will start without caching): %s", exc)
        app.state.redis = None

    # --- MinIO ---
    try:
        from minio import Minio

        minio_client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=False,  # Use HTTP for local dev; configure HTTPS in production
        )
        # Ensure the default bucket exists
        if not minio_client.bucket_exists(settings.minio_bucket):
            minio_client.make_bucket(settings.minio_bucket)
            logger.info("MinIO bucket created: %s", settings.minio_bucket)
        app.state.minio = minio_client
        logger.info("MinIO connected: %s", settings.minio_endpoint)
    except Exception as exc:
        logger.warning("MinIO not reachable (app will start without file storage): %s", exc)
        app.state.minio = None

    # --- MongoDB (originals / GridFS) ---
    try:
        from pymongo import MongoClient

        mongo_client = MongoClient(settings.mongo_uri, serverSelectionTimeoutMS=4000)
        mongo_client.admin.command("ping")
        app.state.mongo = mongo_client
        from app.infra import set_mongo_client

        set_mongo_client(mongo_client)
        logger.info("MongoDB connected: %s", settings.mongo_uri)
    except Exception as exc:
        logger.warning("MongoDB not reachable (originals store degraded): %s", exc)
        app.state.mongo = None

    # --- Neo4j (GraphRAG) ---
    try:
        from neo4j import AsyncGraphDatabase

        neo4j_driver = AsyncGraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )
        await neo4j_driver.verify_connectivity()
        app.state.neo4j = neo4j_driver
        from app.infra import set_neo4j_driver

        set_neo4j_driver(neo4j_driver)
        logger.info("Neo4j connected: %s", settings.neo4j_uri)
    except Exception as exc:
        logger.warning("Neo4j not reachable (GraphRAG degraded to pgvector): %s", exc)
        app.state.neo4j = None

    # --- Run pending Alembic migrations ---
    if app.state.db_engine is not None:
        try:
            import asyncio
            import sys
            from pathlib import Path

            alembic_bin = Path(sys.executable).parent / "alembic"
            proc = await asyncio.create_subprocess_exec(
                str(alembic_bin),
                "upgrade",
                "head",
                cwd="/app",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            if proc.returncode != 0:
                detail = (stderr or stdout).decode("utf-8", errors="replace")
                raise RuntimeError(detail or "alembic upgrade failed")
            logger.info("Alembic migrations applied successfully")
        except Exception as exc:
            logger.warning(
                "Failed to run Alembic migrations (app will start anyway): %s", exc
            )

        try:
            from sqlalchemy import select

            from app.config import apply_runtime_overlay
            from app.models.ai_runtime_settings import AiRuntimeSettings
            from app.providers.constants import AI_OVERLAY_FIELDS

            async with session_factory() as session:
                result = await session.execute(
                    select(AiRuntimeSettings).where(AiRuntimeSettings.id == 1)
                )
                row = result.scalar_one_or_none()
                if row and isinstance(row.payload, dict):
                    apply_runtime_overlay(
                        {
                            key: value
                            for key, value in row.payload.items()
                            if key in AI_OVERLAY_FIELDS
                        }
                    )
                    logger.info("Applied AI runtime settings overlay from database")
        except Exception as exc:
            logger.warning("Could not load AI runtime settings overlay: %s", exc)

    # ---- Yield control to the application ----
    yield

    # --- Shutdown ---
    if app.state.db_engine is not None:
        await app.state.db_engine.dispose()
        logger.info("Database engine disposed")

    if app.state.redis is not None:
        await app.state.redis.close()
        logger.info("Redis connection closed")

    mongo = getattr(app.state, "mongo", None)
    if mongo is not None:
        mongo.close()
        logger.info("MongoDB connection closed")

    neo4j = getattr(app.state, "neo4j", None)
    if neo4j is not None:
        await neo4j.close()
        logger.info("Neo4j connection closed")


# -----------------------------------------------------------------------------
# Application instance
# -----------------------------------------------------------------------------

app = FastAPI(
    title="TOR Drafting and Review API",
    description="API for drafting, reviewing, and exporting Terms of Reference documents compliant with Thai procurement law (พ.ร.บ. 2560)",
    version="0.1.0",
    lifespan=lifespan,
    redirect_slashes=False,
)


# -----------------------------------------------------------------------------
# Exception Handlers: standardized error response envelope
# -----------------------------------------------------------------------------

register_exception_handlers(app)


# -----------------------------------------------------------------------------
# Middleware: CORS
# -----------------------------------------------------------------------------

settings = get_settings()
_cors_origins = [item.strip() for item in settings.cors_origins.split(",") if item.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins or ["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID", "Accept", "Cookie"],
)


# -----------------------------------------------------------------------------
# Middleware: Request ID injection
# -----------------------------------------------------------------------------


@app.middleware("http")
async def request_id_middleware(request: Request, call_next) -> Response:
    """Inject a unique request ID and security headers into every response."""
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    response: Response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; "
        "script-src 'self'; font-src 'self' data:; connect-src 'self' http://localhost:4000"
    )
    return response


# -----------------------------------------------------------------------------
# Middleware: Request logging
# -----------------------------------------------------------------------------


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next) -> Response:
    """Log method, path, status code, and duration for every request."""
    start_time = time.perf_counter()
    response: Response = await call_next(request)
    duration_ms = (time.perf_counter() - start_time) * 1000

    logger.info(
        "%s %s -> %d (%.1fms)",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response


# -----------------------------------------------------------------------------
# Include routers
# -----------------------------------------------------------------------------

app.include_router(health_endpoints.router)
app.include_router(api_router)
