"""Pytest configuration and shared fixtures for ollog test suite.

This file owns all shared fixtures. Plans 01-03 and 01-04 must NOT modify it.
"""
import pytest
import pytest_asyncio
from pymongo import AsyncMongoClient
from beanie import init_beanie


@pytest_asyncio.fixture(scope="session")
async def mongo_client():
    """Session-scoped async MongoDB client for integration tests."""
    client = AsyncMongoClient("mongodb://localhost:27017")
    yield client
    client.close()


@pytest_asyncio.fixture(scope="function")
async def test_db(mongo_client):
    """Function-scoped test database — dropped after each test for isolation."""
    from app.qso.models import QSO
    db = mongo_client["ollog_test"]
    await init_beanie(database=db, document_models=[QSO])
    yield db
    await db.client.drop_database("ollog_test")
