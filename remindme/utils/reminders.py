from __future__ import annotations

import datetime
import typing

import dateparser
import hikari

from remindme.utils import components

if typing.TYPE_CHECKING:
    import lightbulb

    from remindme import db
    from remindme import interaction_handlers
    from remindme.db import models

    type ScheduleContextT = (
        lightbulb.Context | interaction_handlers.ModalContext | interaction_handlers.ComponentContext
    )
    type RescheduleContextT = interaction_handlers.ModalContext | interaction_handlers.ComponentContext


def _dehumanize_time(when_str: str) -> datetime.datetime | None:
    now = datetime.datetime.now(tz=datetime.UTC)

    # noinspection PyTypeChecker
    when = dateparser.parse(
        when_str,
        settings={
            "RETURN_AS_TIMEZONE_AWARE": True,
            "RELATIVE_BASE": now,
            "PREFER_DATES_FROM": "future",
            "PARSERS": ["relative-time", "absolute-time"],
            "TIMEZONE": "CEST",
        },
    )
    if when is None or when < now:
        return None

    return when


async def create_reminder(
    *,
    ctx: ScheduleContextT,
    when_str: str,
    description: str | None,
    queries: db.Queries,
    public_ack: bool,
    reference_message_id: int | None = None,
    reference_channel_id: int | None = None,
    reference_guild_id: int | None = None,
) -> None:
    await ctx.defer(ephemeral=not public_ack)

    description = description or "*No description provided*"

    when = _dehumanize_time(when_str)
    if when is None:
        await ctx.respond("Unknown time format", ephemeral=True)
        return

    reminder: models.Reminder | None
    if reference_message_id is not None:
        reminder = await queries.create_reminder_with_reference(
            user_id=ctx.interaction.user.id,
            expire_at=when,
            description=description,
            reference_message_id=reference_message_id,
            reference_channel_id=reference_channel_id,
            reference_guild_id=reference_guild_id or None,
        )
    else:
        reminder = await queries.create_reminder(
            user_id=ctx.interaction.user.id, expire_at=when, description=description
        )

    assert reminder is not None

    response_id = await ctx.respond(
        components=components.make_create_reminder_component(reminder), ephemeral=not public_ack
    )

    if reference_message_id is None:
        response = await ctx.fetch_response(response_id)

        # If the message was sent as an ephemeral (either by the users selection or Discords)
        # then do a best-effort and link to the messages surrounding when the command was executed
        linked_message_id = ctx.interaction.id if response.flags & hikari.MessageFlag.EPHEMERAL != 0 else response.id

        await queries.add_reminder_reference_message(
            id_=reminder.id,
            reference_message_id=linked_message_id,
            reference_channel_id=ctx.interaction.channel_id,
            reference_guild_id=ctx.interaction.guild_id,
        )


async def reschedule_reminder(
    ctx: RescheduleContextT, reminder: models.Reminder, when_str: str, original_message_id: int, queries: db.Queries
) -> None:
    await ctx.defer(ephemeral=True)

    when = _dehumanize_time(when_str)
    if when is None:
        await ctx.respond("Unknown time format", ephemeral=True)
        return

    updated_reminder = await queries.reschedule_reminder(id_=reminder.id, expire_at=when)
    assert updated_reminder is not None

    await ctx.respond(
        components=components.make_create_reminder_component(updated_reminder, snoozed=True), ephemeral=True
    )
    await ctx.edit_response(
        original_message_id, components=components.make_reminder_component(reminder, snoozed_until=when)
    )


async def send_reminder(reminder: models.Reminder, *, queries: db.Queries, rest: hikari.api.RESTClient) -> None:
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
