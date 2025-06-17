from __future__ import annotations

import asyncpg
import confspec
import hikari
import lightbulb

from remindme import config as configuration
from remindme import db
from remindme import extensions
from remindme.interaction_handlers import components as components_interaction_handler
from remindme.interaction_handlers import modals as modals_interaction_handler

config = confspec.load("config.yml", cls=configuration.Config)

bot = hikari.RESTBot(token=config.token, public_key=config.public_key)
client = lightbulb.client_from_app(bot)


async def pool_teardown(pool: asyncpg.Pool) -> None:
    await pool.close()


async def start_client(_: hikari.RESTBot) -> None:
    default_registry = client.di.registry_for(lightbulb.di.Contexts.DEFAULT)

    pool = await asyncpg.create_pool(
        host=config.db.host,
        port=config.db.port,
        database=config.db.database,
        user=config.db.username,
        password=config.db.password,
    )
    default_registry.register_value(asyncpg.Pool, pool, teardown=pool_teardown)
    default_registry.register_value(db.Queries, db.Queries(pool))  # type: ignore

    component_token = components_interaction_handler.handler.set(
        ch := components_interaction_handler.ComponentHandler(client)
    )
    default_registry.register_value(components_interaction_handler.ComponentHandler, ch)

    modal_token = modals_interaction_handler.handler.set(ch := modals_interaction_handler.ModalHandler(client))
    default_registry.register_value(modals_interaction_handler.ModalHandler, ch)

    try:
        await client.load_extensions_from_package(extensions, recursive=True)
    finally:
        components_interaction_handler.handler.reset(component_token)
        modals_interaction_handler.handler.reset(modal_token)

    await client.start()


async def stop_client(_: hikari.RESTBot) -> None:
    await client.stop()


bot.add_startup_callback(start_client)
bot.add_shutdown_callback(stop_client)

bot.run(port=config.port)
