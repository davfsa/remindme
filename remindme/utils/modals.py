from __future__ import annotations

import hikari.impl

# TODO: Would be nice to have a way to specify these in the future and know what values it will have
#       and grab them from the custom ID. Might require some tooling tho


def make_reminder_from_message_modal(content: str) -> list[hikari.impl.ModalActionRowBuilder]:
    return [
        hikari.impl.ModalActionRowBuilder().add_text_input("when", "When to get reminded", required=True),
        hikari.impl.ModalActionRowBuilder().add_text_input(
            "description",
            "Description",
            value=content,
            placeholder="None",
            style=hikari.TextInputStyle.PARAGRAPH,
            required=False,
            max_length=4000,
        ),
        hikari.impl.ModalActionRowBuilder().add_text_input(
            "public_ack",
            "Make the acknowledgement public?",
            value="true",
            placeholder="false",
            max_length=5,
            required=False,
        ),
    ]


snooze_input_custom_modal = [
    hikari.impl.ModalActionRowBuilder().add_text_input("when", "When to get reminded", required=True)
]
