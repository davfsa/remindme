from __future__ import annotations

import asyncio
import datetime
import logging
import uuid

import hikari
import lightbulb

from remindme.component_handler import ComponentContext
from remindme.component_handler import ComponentLoadable
from remindme.db import queries as db_queries  # noqa: TC001 - Move to type checking block (needed here for linkd)
from remindme.utils import components
from remindme.utils import constants
from remindme.utils import reminders as utils

logger = logging.getLogger("remindme.ext.reminders")
loader = lightbulb.Loader()

REMINDER_POST_EXPIRE_LIFETIME = datetime.timedelta(hours=3)


class RemindMeModal(lightbulb.components.Modal):
    __slots__ = ("_target", "description", "public_ack", "when")

    def __init__(self, target: hikari.Message) -> None:
        self._target = target
        self.when = self.add_short_text_input("When to get reminded")
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

        await utils.create_reminder(
            ctx=ctx,
            queries=queries,
            description=description,
            when_str=ctx.value_for(self.when),
            public_ack=public,
            reference_message=self._target,
        )


@loader.command
class RemindMeSlashCommand(lightbulb.SlashCommand, name="remindme", description="Create a reminder"):
    __slots__ = ()

    when = lightbulb.string("when", "When do you want to be reminded?", max_length=100)
    description = lightbulb.string(
        "description", "What do you want to be reminded about?", max_length=4000, default="*No description provided*"
    )
    public_ack = lightbulb.boolean("public_ack", "Whether to send a public acknowledgement", default=True)

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context, queries: db_queries.Queries) -> None:
        await utils.create_reminder(
            ctx=ctx, queries=queries, description=self.description, when_str=self.when, public_ack=self.public_ack
        )


@loader.command
class RemindMeMessageCommand(
    lightbulb.MessageCommand, name="Remind Me", description="Create a reminder about this message"
):
    __slots__ = ()

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        modal = RemindMeModal(self.target)

        await ctx.respond_with_modal("Create a reminder", c_id := str(uuid.uuid4()), components=modal)

        try:
            await modal.attach(ctx.client, c_id, timeout=60)
        except TimeoutError:
            pass


async def snooze_select_callback(ctx: ComponentContext, queries: db_queries.Queries = lightbulb.di.INJECTED) -> None:
    reminder_id = int(ctx.arguments[0])
    reminder = await queries.get_reminder(id_=reminder_id)

    if reminder is None:
        await ctx.respond("This reminder has expired", ephemeral=True)
        return

    value = ctx.interaction.values[0]

    if value == "custom":
        await ctx.respond("Not yet", ephemeral=True)
        return

    await ctx.respond(components=components.make_reminder_component(reminder, snoozed=True), edit=True)
    await utils.reschedule_reminder(ctx=ctx, reminder=reminder, when_str=value, queries=queries)


loader.add(ComponentLoadable(constants.REMINDER_SNOOZE_SELECT_CUSTOM_ID, snooze_select_callback))


@loader.task(lightbulb.uniformtrigger(5), auto_start=True)
async def check_reminders(queries: db_queries.Queries, rest: hikari.api.RESTClient) -> None:
    expired_reminders = await queries.get_expired_reminders()

    if not expired_reminders:
        return

    returned = await asyncio.gather(
        *(utils.send_reminder(reminder=r, queries=queries, rest=rest) for r in expired_reminders),
        return_exceptions=True,
    )

    for r in returned:
        if isinstance(r, Exception):
            logger.error("failed to send reminder", exc_info=r)


@loader.task(lightbulb.uniformtrigger(10), auto_start=True)
async def cleanup_reminders(queries: db_queries.Queries) -> None:
    now = datetime.datetime.now(tz=datetime.UTC)
    handled_reminders = await queries.get_handled_reminders(expire_at=now - REMINDER_POST_EXPIRE_LIFETIME)

    if not handled_reminders:
        return

    returned = await asyncio.gather(
        *(queries.delete_reminder(id_=r.id) for r in handled_reminders), return_exceptions=True
    )

    for r in returned:
        if isinstance(r, Exception):
            logger.error("failed to delete reminder", exc_info=r)
