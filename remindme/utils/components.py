from __future__ import annotations

import typing

import hikari

from remindme.utils import keys

if typing.TYPE_CHECKING:
    import datetime

    import hikari.api.special_endpoints

    from remindme.db import models


def wrap_text(text: str) -> hikari.impl.TextDisplayComponentBuilder:
    return hikari.impl.TextDisplayComponentBuilder(content=text)


def _make_reminder_container(reminder: models.Reminder) -> hikari.impl.ContainerComponentBuilder:
    assert reminder.reference_message_id is not None
    assert reminder.reference_channel_id is not None

    guild_part = "@me" if reminder.reference_guild_id is None else reminder.reference_guild_id

    return hikari.impl.ContainerComponentBuilder(
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
    )


def make_reminder_component(
    reminder: models.Reminder, *, snoozed_until: datetime.datetime | None = None
) -> typing.Sequence[hikari.api.ComponentBuilder]:
    top_content: str
    if snoozed_until:
        timestamp = int(snoozed_until.timestamp())
        top_content = f"*Snoozed until <t:{timestamp}:F> (<t:{timestamp}:R>)*"
    else:
        top_content = "Reminder!"

    components: list[hikari.api.ComponentBuilder] = [
        hikari.impl.TextDisplayComponentBuilder(content=top_content),
        _make_reminder_container(reminder),
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


def make_reminder_view_component(
    reminder: models.Reminder, *, offset: int
) -> typing.Sequence[hikari.api.ComponentBuilder]:
    timestamp = int(reminder.expire_at.timestamp())

    reminder_container = (
        _make_reminder_container(reminder)
        .add_component(hikari.impl.SeparatorComponentBuilder(divider=True, spacing=hikari.SpacingType.SMALL))
        .add_component(hikari.impl.TextDisplayComponentBuilder(content=f"-# <t:{timestamp}:F> (<t:{timestamp}:R>)"))
    )

    return [
        reminder_container,
        hikari.impl.MessageActionRowBuilder(
            components=[
                hikari.impl.InteractiveButtonBuilder(
                    style=hikari.ButtonStyle.SECONDARY,
                    label="Back",
                    custom_id=keys.make_key(keys.REMINDER_LIST_MOVE, offset),
                ),
                hikari.impl.InteractiveButtonBuilder(
                    style=hikari.ButtonStyle.DANGER,
                    label="Delete",
                    custom_id=keys.make_key(keys.REMINDER_DELETE, reminder.id, offset),
                ),
            ]
        ),
    ]


def _trim_to_size(text: str, *, size: int) -> str:
    if len(text) > (size - 3):
        return text[: size - 3] + "..."

    return text


def make_reminder_list_component(
    reminders: typing.Sequence[models.Reminder], *, offset: int, limit: int, total_count: int
) -> typing.Sequence[hikari.api.ComponentBuilder]:
    container_components: list[hikari.api.special_endpoints.ContainerBuilderComponentsT] = []
    for reminder in reminders:
        timestamp = int(reminder.expire_at.timestamp())

        container_components.extend(
            (
                hikari.impl.SectionComponentBuilder(
                    accessory=hikari.impl.InteractiveButtonBuilder(
                        style=hikari.ButtonStyle.PRIMARY,
                        label="View",
                        custom_id=keys.make_key(keys.REMINDER_VIEW, reminder.id, offset),
                    ),
                    components=[
                        hikari.impl.TextDisplayComponentBuilder(content=_trim_to_size(reminder.description, size=500)),
                        hikari.impl.TextDisplayComponentBuilder(content=f"-# <t:{timestamp}:F> (<t:{timestamp}:R>)"),
                    ],
                ),
            )
        )

        if reminder != reminders[-1]:
            container_components.append(
                hikari.impl.SeparatorComponentBuilder(divider=False, spacing=hikari.SpacingType.LARGE)
            )

    return [
        hikari.impl.ContainerComponentBuilder(components=container_components),
        hikari.impl.MessageActionRowBuilder(
            components=[
                hikari.impl.InteractiveButtonBuilder(
                    is_disabled=offset <= 0,
                    style=hikari.ButtonStyle.SECONDARY,
                    emoji="\u2b05\ufe0f",  # Left Arrow Block
                    custom_id=keys.make_key(keys.REMINDER_LIST_MOVE, offset - limit),
                ),
                hikari.impl.InteractiveButtonBuilder(
                    is_disabled=(offset + limit >= total_count),
                    style=hikari.ButtonStyle.SECONDARY,
                    emoji="\u27a1\ufe0f",  # Right Arrow Block
                    custom_id=keys.make_key(keys.REMINDER_LIST_MOVE, offset + limit),
                ),
            ]
        ),
    ]
