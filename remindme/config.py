from __future__ import annotations

import msgspec


class Config(msgspec.Struct, kw_only=True):
    """Base configuration."""

    token: str
    public_key: str
    port: int
    db: DatabaseConfig


class DatabaseConfig(msgspec.Struct, kw_only=True):
    """Database configuration."""

    host: str
    port: int
    database: str
    username: str
    password: str
