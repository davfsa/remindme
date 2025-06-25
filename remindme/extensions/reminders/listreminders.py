from __future__ import annotations

import typing

import hikari
import lightbulb

import remindme
from remindme import db
from remindme import interaction_handlers
from remindme.utils import components
from remindme.utils import keys

loader = remindme.Loader()

REMINDERS_PER_PAGE = 5


async def _get_reminders_list(
    ctx: lightbulb.Context | interaction_handlers.ComponentContext, queries: db.Queries, *, offset: int = 0
) -> typing.Sequence[hikari.api.ComponentBuilder] | None:
    count = await queries.get_reminders_count_for(user_id=ctx.interaction.user.id)
    assert count is not None
    if count == 0:
        return None

    reminders = await queries.get_reminders_for(
        user_id=ctx.interaction.user.id, offset=offset, limit=REMINDERS_PER_PAGE
    )
    return components.make_reminder_list_component(
        reminders, offset=offset, limit=REMINDERS_PER_PAGE, total_count=count
    )


@loader.command
class ListReminders(lightbulb.SlashCommand, name="listreminders", description="List active reminders"):
    __slots__ = ()

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context, queries: db.Queries) -> None:
        list_components = await _get_reminders_list(ctx=ctx, queries=queries)

        if list_components:
            await ctx.respond(components=list_components, ephemeral=True)
        else:
            await ctx.respond("No currently active reminders.", ephemeral=True)


@loader.component(keys.REMINDER_LIST_MOVE)
async def list_move_callback(
    ctx: interaction_handlers.ComponentContext, queries: db.Queries = lightbulb.di.INJECTED
) -> None:
    offset = int(ctx.arguments[0])
    list_components = await _get_reminders_list(ctx=ctx, queries=queries, offset=offset)

    if list_components:
        await ctx.respond(components=list_components, edit=True)
    else:
        await ctx.respond(component=components.wrap_text("No currently active reminders"), edit=True)


@loader.component(keys.REMINDER_VIEW)
async def reminder_view_callback(
    ctx: interaction_handlers.ComponentContext, queries: db.Queries = lightbulb.di.INJECTED
) -> None:
    reminder_id = int(ctx.arguments[0])
    offset = int(ctx.arguments[1])

    reminder = await queries.get_reminder(id_=reminder_id)
    if not reminder:
        await ctx.respond("Reminder not found", ephemeral=True)
        return

    await ctx.respond(components=components.make_reminder_view_component(reminder, offset=offset), edit=True)


@loader.component(keys.REMINDER_DELETE)
async def reminder_delete_callback(
    ctx: interaction_handlers.ComponentContext, queries: db.Queries = lightbulb.di.INJECTED
) -> None:
    reminder_id = int(ctx.arguments[0])
    offset = int(ctx.arguments[1])

    await queries.delete_reminder(id_=reminder_id)

    list_components = await _get_reminders_list(ctx=ctx, queries=queries, offset=offset)

    if list_components:
        await ctx.respond(components=list_components, edit=True)
    else:
        await ctx.respond(component=components.wrap_text("No currently active reminders"), edit=True)
