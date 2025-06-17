from __future__ import annotations

import contextvars
import typing

import hikari
import lightbulb

from remindme.interaction_handlers import base

if typing.TYPE_CHECKING:
    import asyncio


handler: contextvars.ContextVar[ComponentHandler] = contextvars.ContextVar("component_handler")


class ComponentContext(lightbulb.components.MessageResponseMixinWithEdit[hikari.ComponentInteraction]):
    __slots__ = ("_interaction", "arguments", "client")

    def __init__(
        self, client: lightbulb.Client, interaction: hikari.ComponentInteraction, initial_response_sent: asyncio.Event
    ) -> None:
        super().__init__(initial_response_sent)

        self.client = client
        self._interaction = interaction
        self.arguments = interaction.custom_id.split(":")[1:]

    @property
    def interaction(self) -> hikari.ComponentInteraction:
        return self._interaction

    async def respond_with_modal(
        self,
        title: str,
        custom_id: str,
        component: hikari.UndefinedOr[hikari.api.ComponentBuilder] = hikari.UNDEFINED,
        components: hikari.UndefinedOr[typing.Sequence[hikari.api.ComponentBuilder]] = hikari.UNDEFINED,
    ) -> None:
        async with self._response_lock:
            if self._initial_response_sent.is_set():
                msg = "cannot respond with a modal if an initial response has already been sent"
                raise RuntimeError(msg)

            await self.interaction.create_modal_response(title, custom_id, component, components)
            self._initial_response_sent.set()


class ComponentHandler(base.BaseInteractionHandler[hikari.ComponentInteraction, ComponentContext]):
    _context_type_ = ComponentContext
    _interaction_type_ = hikari.ComponentInteraction


class ComponentLoadable(base.BaseLoadable[ComponentHandler]):
    _handler_contextvar_ = handler
