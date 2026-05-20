"""Pytest configuration and shared fixtures for ollog test suite.

This file owns all shared fixtures. Plans 01-03 and 01-04 must NOT modify it.
"""
import pytest
import pytest_asyncio
from pymongo import AsyncMongoClient
from beanie import init_beanie


@pytest_asyncio.fixture(scope="function")
async def test_db():
    """Function-scoped test database — creates and drops for each test."""
    import socket
    try:
        s = socket.create_connection(("localhost", 27017), timeout=1)
        s.close()
    except OSError:
        pytest.skip("MongoDB not available at localhost:27017")

    from app.qso.models import QSO
    client = AsyncMongoClient(
        "mongodb://localhost:27017/?directConnection=true",
        serverSelectionTimeoutMS=2000,
    )
    db = client["ollog_test"]
    await init_beanie(database=db, document_models=[QSO])
    yield db
    await client.drop_database("ollog_test")
    await client.aclose()
