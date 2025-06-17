from __future__ import annotations

import typing

import hikari

from remindme.utils import keys

if typing.TYPE_CHECKING:
    import datetime

    from remindme.db import models


def make_reminder_component(
    reminder: models.Reminder, *, snoozed_until: datetime.datetime | None = None
) -> typing.Sequence[hikari.api.ComponentBuilder]:
    assert reminder.reference_message_id is not None
    assert reminder.reference_channel_id is not None

    guild_part = "@me" if reminder.reference_guild_id is None else reminder.reference_guild_id

    top_content: str
    if snoozed_until:
        timestamp = int(snoozed_until.timestamp())
        top_content = f"*Snoozed until <t:{timestamp}:F> (<t:{timestamp}:R>)*"
    else:
        top_content = "Reminder!"

    components: list[hikari.api.ComponentBuilder] = [
        hikari.impl.TextDisplayComponentBuilder(content=top_content),
        hikari.impl.ContainerComponentBuilder(
            components=[
                hikari.impl.TextDisplayComponentBuilder(content=reminder.description),
                hikari.impl.MessageActionRowBuilder(
                    components=[
                        hikari.impl.LinkButtonBuilder(
                            url=f"https://discord.com/channels/{guild_part}/{reminder.reference_channel_id}/{reminder.reference_message_id}",
                            label="Jump to message",
                        )
                    ]
                ),
            ]
        ),
    ]

    if not snoozed_until:
        components.append(
            hikari.impl.MessageActionRowBuilder(
                components=[
                    hikari.impl.TextSelectMenuBuilder(
                        placeholder="Snooze",
                        custom_id=keys.make_key(keys.REMINDER_SNOOZE_SELECT, reminder.id),
                        options=[
                            hikari.impl.SelectOptionBuilder(label="10 minutes", value="10 minutes"),
                            hikari.impl.SelectOptionBuilder(label="30 minutes", value="30 minutes"),
                            hikari.impl.SelectOptionBuilder(label="1 hour", value="1 hour"),
                            hikari.impl.SelectOptionBuilder(label="6 hours", value="6 hours"),
                            hikari.impl.SelectOptionBuilder(label="1 day", value="1 day"),
                            hikari.impl.SelectOptionBuilder(label="Custom", value="custom"),
                        ],
                    )
                ]
            )
        )

    return components


def make_create_reminder_component(
    reminder: models.Reminder, *, snoozed: bool = False
) -> typing.Sequence[hikari.api.ComponentBuilder]:
    timestamp = int(reminder.expire_at.timestamp())
    action = "snoozed" if snoozed else "created"

    return [
        hikari.impl.TextDisplayComponentBuilder(content=f"**Reminder {action}!**"),
        hikari.impl.ContainerComponentBuilder(
            components=[
                hikari.impl.TextDisplayComponentBuilder(content=reminder.description),
                hikari.impl.SeparatorComponentBuilder(divider=True, spacing=hikari.SpacingType.SMALL),
                hikari.impl.TextDisplayComponentBuilder(content=f"-# <t:{timestamp}:F> (<t:{timestamp}:R>)"),
            ]
        ),
    ]
