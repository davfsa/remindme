from __future__ import annotations

import msgspec


class Config(msgspec.Struct, kw_only=True):
    """Base configuration."""

    token: str
    db: DatabaseConfig


class DatabaseConfig(msgspec.Struct, kw_only=True):
    """Database configuration."""

    host: str
    port: int = 5432
    database: str
    username: str
    password: str
