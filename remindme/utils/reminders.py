from __future__ import annotations

import datetime
import typing

import dateparser
import hikari
import lightbulb

from remindme import component_handler
from remindme.db import models
from remindme.db import queries as db_queries
from remindme.utils import components

if typing.TYPE_CHECKING:
    type ContextT = lightbulb.Context | lightbulb.components.ModalContext | component_handler.ComponentContext


def _dehumanize_time(when_str: str) -> datetime.datetime | None:
    now = datetime.datetime.now(tz=datetime.UTC)

    # noinspection PyTypeChecker
    when = dateparser.parse(
        when_str, settings={"RETURN_AS_TIMEZONE_AWARE": True, "RELATIVE_BASE": now, "PREFER_DATES_FROM": "future"}
    )
    if when is None or when < now:
        return None

    return when


async def create_reminder(
    *,
    ctx: ContextT,
    when_str: str,
    description: str,
    queries: db_queries.Queries,
    public_ack: bool,
    reference_message: hikari.Message | None = None,
) -> None:
    when = _dehumanize_time(when_str)
    if when is None:
        await ctx.respond("Unknown time format", ephemeral=True)
        return

    reminder: models.Reminder
    if reference_message:
        reminder = await queries.create_reminder_with_reference(
            user_id=ctx.user.id,
            expire_at=when,
            description=description,
            reference_message_id=reference_message.id,
            reference_channel_id=reference_message.channel_id,
            reference_guild_id=reference_message.guild_id,
        )
    else:
        reminder = await queries.create_reminder(user_id=ctx.user.id, expire_at=when, description=description)

    response_id = await ctx.respond(
        components=components.make_create_reminder_component(reminder), ephemeral=not public_ack
    )

    if reference_message is None:
        response = await ctx.fetch_response(response_id)

        # If the message was sent as an ephemeral (either by the users selection or Discords)
        # then do a best-effort and link to the messages surrounding when the command was executed
        linked_message_id = ctx.interaction.id if response.flags & hikari.MessageFlag.EPHEMERAL != 0 else response.id

        await queries.add_reminder_reference_message(
            id_=reminder.id,
            reference_message_id=linked_message_id,
            reference_channel_id=ctx.channel_id,
            reference_guild_id=ctx.guild_id,
        )


async def reschedule_reminder(
    ctx: ContextT, reminder: models.Reminder, when_str: str, queries: db_queries.Queries
) -> None:
    when = _dehumanize_time(when_str)
    if when is None:
        await ctx.respond("Unknown time format", ephemeral=True)
        return

    reminder = await queries.reschedule_reminder(id_=reminder.id, expire_at=when)

    await ctx.respond(components=components.make_create_reminder_component(reminder, snoozed=True), ephemeral=True)


async def send_reminder(reminder: models.Reminder, *, queries: db_queries.Queries, rest: hikari.api.RESTClient) -> None:
    dm_channel_id = await queries.get_dm_channel_for_user(user_id=reminder.user_id)
    if not dm_channel_id:
        try:
            dm_channel = await rest.create_dm_channel(reminder.user_id)
        except hikari.ForbiddenError:
            # The user deauthorized the app, oh well :)
            await queries.delete_reminder(id_=reminder.id)
            return

        dm_channel_id = dm_channel.id
        await queries.add_dm_channel(channel_id=dm_channel_id, user_id=reminder.user_id)

    try:
        await rest.create_message(dm_channel_id, components=components.make_reminder_component(reminder))
    except hikari.ForbiddenError:
        # The user deauthorized the app, oh well :)
        await queries.delete_reminder(id_=reminder.id)
        return

    await queries.mark_reminder_as_handled(id_=reminder.id)
