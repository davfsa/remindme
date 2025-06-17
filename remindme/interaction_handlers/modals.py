from __future__ import annotations

import contextvars
import typing

import hikari
import lightbulb

from remindme.interaction_handlers import base

if typing.TYPE_CHECKING:
    import asyncio


handler: contextvars.ContextVar[ModalHandler] = contextvars.ContextVar("component_handler")


class ModalContext(lightbulb.components.MessageResponseMixinWithEdit[hikari.ModalInteraction]):
    __slots__ = ("_interaction", "arguments", "client", "values")

    def __init__(
        self, client: lightbulb.Client, interaction: hikari.ModalInteraction, initial_response_sent: asyncio.Event
    ) -> None:
        super().__init__(initial_response_sent)

        self.client = client
        self._interaction = interaction
        self.arguments = interaction.custom_id.split(":")[1:]

        self.values: dict[str, str] = {}
        for row in interaction.components:
            for component in row:
                self.values[component.custom_id] = component.value

    @property
    def interaction(self) -> hikari.ModalInteraction:
        return self._interaction


class ModalHandler(base.BaseInteractionHandler[hikari.ModalInteraction, ModalContext]):
    _context_type_ = ModalContext
    _interaction_type_ = hikari.ModalInteraction


class ModalLoadable(base.BaseLoadable[ModalHandler]):
    _handler_contextvar_ = handler
