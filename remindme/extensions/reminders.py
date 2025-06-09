from __future__ import annotations

import asyncio
import datetime
import logging
import typing
import uuid

import dateparser
import dateparser.conf
import hikari.impl
import lightbulb

from remindme.db import queries as db_queries  # noqa: TC001 - Move to type checking block (needed here for linkd)

if typing.TYPE_CHECKING:
    from remindme.db import models

logger = logging.getLogger("remindme.ext.reminders")
loader = lightbulb.Loader()


class RemindMeModal(lightbulb.components.Modal):
    __slots__ = ("_target", "description", "public_ack", "when")

    def __init__(self, target: hikari.Message) -> None:
        self._target = target
        self.when = self.add_short_text_input("When to get alerted")
        self.description = self.add_short_text_input(
            "Description", placeholder="Linked message content", required=False
        )
        self.public_ack = self.add_short_text_input(
            "Make the acknowledgement public?", value="true", placeholder="false", required=False
        )

    @lightbulb.di.with_di
    async def on_submit(self, ctx: lightbulb.components.ModalContext, queries: db_queries.Queries) -> None:
        public = ctx.value_for(self.public_ack).lower() == "true"
        description = ctx.value_for(self.description) or self._target.content or "*Linked message*"

        await create_reminder(
            ctx=ctx,
            queries=queries,
            description=description,
            when_str=ctx.value_for(self.when),
            public_ack=public,
            reference_message=self._target,
        )


@loader.command
class RemindMeSlash(lightbulb.SlashCommand, name="remindme", description="Create a reminder"):
    description = lightbulb.string("description", "What do you want to be reminded about?", max_length=4000)
    when = lightbulb.string("when", "When do you want to be reminded?", max_length=100)
    public_ack = lightbulb.boolean("public_ack", "Whether to send a public acknowledgement", default=True)

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context, queries: db_queries.Queries) -> None:
        await create_reminder(
            ctx=ctx, queries=queries, description=self.description, when_str=self.when, public_ack=self.public_ack
        )


@loader.command
class RemindMeContext(lightbulb.MessageCommand, name="Remind Me", description="Create a reminder about this message"):
    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        modal = RemindMeModal(self.target)

        await ctx.respond_with_modal("Create a reminder", c_id := str(uuid.uuid4()), components=modal)

        try:
            await modal.attach(ctx.client, c_id, timeout=30)
        except TimeoutError:
            pass


def make_reminder_component(reminder: models.Reminder) -> typing.Sequence[hikari.api.ComponentBuilder]:
    container = hikari.impl.ContainerComponentBuilder(
        components=[hikari.impl.TextDisplayComponentBuilder(content=reminder.description)]
    )

    if reminder.reference_message_id:
        assert reminder.reference_message_id is not None
        assert reminder.reference_channel_id is not None

        guild_part = "@me" if reminder.reference_guild_id is None else reminder.reference_guild_id
        container.add_component(hikari.impl.SeparatorComponentBuilder(divider=False, spacing=hikari.SpacingType.SMALL))
        container.add_component(
            hikari.impl.MessageActionRowBuilder(
                components=[
                    hikari.impl.LinkButtonBuilder(
                        url=f"https://discord.com/channels/{guild_part}/{reminder.reference_channel_id}/{reminder.reference_message_id}",
                        label="Jump to message",
                    )
                ]
            )
        )

    return [hikari.impl.TextDisplayComponentBuilder(content="**Reminder!**"), container]


def make_create_reminder_component(reminder: models.Reminder) -> typing.Sequence[hikari.api.ComponentBuilder]:
    timestamp = int(reminder.expire_at.timestamp())

    return [
        hikari.impl.TextDisplayComponentBuilder(content="**Reminder created!**"),
        hikari.impl.ContainerComponentBuilder(
            components=[
                hikari.impl.TextDisplayComponentBuilder(content=reminder.description),
                hikari.impl.SeparatorComponentBuilder(divider=True, spacing=hikari.SpacingType.SMALL),
                hikari.impl.TextDisplayComponentBuilder(content=f"-# <t:{timestamp}:F> (<t:{timestamp}:R>)"),
            ]
        ),
    ]


async def create_reminder(
    *,
    ctx: lightbulb.Context | lightbulb.components.ModalContext,
    when_str: str,
    description: str,
    queries: db_queries.Queries,
    public_ack: bool,
    reference_message: hikari.Message | None = None,
) -> None:
    now = datetime.datetime.now(tz=datetime.UTC)

    when = dateparser.parse(when_str, settings={"RETURN_AS_TIMEZONE_AWARE": True, "RELATIVE_BASE": now})
    if when is None:
        await ctx.respond("Unknown time format", ephemeral=True)
        return

    if when < now:
        # Transform to future time
        when = now + (now - when)

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

    response_id = await ctx.respond(components=make_create_reminder_component(reminder), ephemeral=not public_ack)

    if public_ack and reference_message is None:
        if response_id == -1:
            response_id = (await ctx.fetch_response(response_id)).id

        await queries.add_reminder_reference_message(
            id_=reminder.id,
            reference_message_id=response_id,
            reference_channel_id=ctx.channel_id,
            reference_guild_id=ctx.guild_id,
        )


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
        await rest.create_message(dm_channel_id, components=make_reminder_component(reminder))
    except hikari.ForbiddenError:
        # The user deauthorized the app, oh well :)
        pass

    await queries.delete_reminder(id_=reminder.id)


@loader.task(lightbulb.uniformtrigger(5), auto_start=True)
async def check_reminders(queries: db_queries.Queries, rest: hikari.api.RESTClient) -> None:
    expired_reminders = await queries.get_expired_reminders()

    if not expired_reminders:
        return

    returned = await asyncio.gather(
        *(send_reminder(reminder=r, queries=queries, rest=rest) for r in expired_reminders), return_exceptions=True
    )

    for r in returned:
        if isinstance(r, Exception):
            logger.error("failed to send reminder", exc_info=r)
