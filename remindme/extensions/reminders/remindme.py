from __future__ import annotations

import lightbulb

import remindme
from remindme import db
from remindme import interaction_handlers
from remindme.utils import keys
from remindme.utils import modals
from remindme.utils import reminders as utils

loader = remindme.Loader()


@loader.command
class RemindMeSlashCommand(lightbulb.SlashCommand, name="remindme", description="Create a reminder"):
    __slots__ = ()

    when = lightbulb.string("when", "When do you want to be reminded?", max_length=100)
    description = lightbulb.string(
        "description", "What do you want to be reminded about?", max_length=4000, default=None
    )
    public_ack = lightbulb.boolean("public_ack", "Whether to send a public acknowledgement", default=True)

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context, queries: db.Queries) -> None:
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
        await ctx.respond_with_modal(
            "Create a reminder",
            keys.make_key(
                keys.REMINDER_CREATE_FROM_MESSAGE_MODAL_CUSTOM_ID,
                self.target.guild_id or 0,
                self.target.channel_id,
                self.target.id,
            ),
            components=modals.make_reminder_from_message_modal(self.target.content or ""),
        )


@loader.component(keys.REMINDER_SNOOZE_SELECT)
async def snooze_select_callback(
    ctx: interaction_handlers.ComponentContext, queries: db.Queries = lightbulb.di.INJECTED
) -> None:
    reminder_id = int(ctx.arguments[0])
    reminder = await queries.get_reminder(id_=reminder_id)

    if reminder is None:
        await ctx.respond("This reminder has expired", ephemeral=True)
        return

    value = ctx.interaction.values[0]

    if value == "custom":
        await ctx.respond_with_modal(
            "Choose custom snooze time",
            custom_id=keys.make_key(keys.REMINDER_SNOOZE_INPUT_CUSTOM, reminder_id),
            components=modals.snooze_input_custom_modal,
        )
        return

    original_message = ctx.interaction.message

    await utils.reschedule_reminder(
        ctx=ctx, reminder=reminder, when_str=value, queries=queries, original_message_id=original_message.id
    )


@loader.modal(keys.REMINDER_SNOOZE_INPUT_CUSTOM)
async def snooze_with_custom_time_callback(
    ctx: interaction_handlers.ModalContext, queries: db.Queries = lightbulb.di.INJECTED
) -> None:
    reminder_id = int(ctx.arguments[0])
    reminder = await queries.get_reminder(id_=reminder_id)

    if reminder is None:
        await ctx.respond("This reminder has expired", ephemeral=True)
        return

    original_message = ctx.interaction.message
    assert original_message is not None

    await utils.reschedule_reminder(
        ctx=ctx,
        reminder=reminder,
        when_str=ctx.values["when"],
        original_message_id=original_message.id,
        queries=queries,
    )


@loader.modal(keys.REMINDER_CREATE_FROM_MESSAGE_MODAL_CUSTOM_ID)
async def create_submit(ctx: interaction_handlers.ModalContext, queries: db.Queries = lightbulb.di.INJECTED) -> None:
    await utils.create_reminder(
        ctx=ctx,
        queries=queries,
        description=ctx.values["description"],
        when_str=ctx.values["when"],
        public_ack=ctx.values["public_ack"].lower() == "true",
        reference_guild_id=int(ctx.arguments[0]),
        reference_channel_id=int(ctx.arguments[1]),
        reference_message_id=int(ctx.arguments[2]),
    )
