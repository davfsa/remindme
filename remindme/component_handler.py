from __future__ import annotations

import asyncio
import contextvars
import typing

import hikari
import lightbulb

if typing.TYPE_CHECKING:
    type ComponentCallbackT = typing.Callable[[ComponentContext], typing.Coroutine[typing.Any, typing.Any, None]]

handler: contextvars.ContextVar[ComponentHandler] = contextvars.ContextVar("component_handler")


class ComponentContext(lightbulb.components.MessageResponseMixinWithEdit[hikari.ComponentInteraction]):
    """Class representing the context for a single command invocation."""

    __slots__ = ("arguments", "client", "interaction")

    def __init__(
        self, client: lightbulb.Client, interaction: hikari.ComponentInteraction, initial_response_sent: asyncio.Event
    ) -> None:
        super().__init__(initial_response_sent)

        self.client = client
        self.interaction = interaction
        self.arguments = interaction.custom_id.split(":")[1:]

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


class ComponentHandler:
    __slots__ = ("_client", "_handlers")

    def __init__(self, client: lightbulb.Client) -> None:
        self._handlers: dict[str, ComponentCallbackT] = {}
        self._client = client

        app = client.app
        assert isinstance(app, hikari.InteractionServerAware)
        app.interaction_server.set_listener(hikari.ComponentInteraction, self._handle_interaction, replace=True)

    async def _handle_interaction(self, interaction: hikari.ComponentInteraction) -> typing.AsyncGenerator[None]:
        callback = self._handlers.get(interaction.custom_id.split(":")[0])

        if not callback:
            msg = f"No callback found for id: {interaction.custom_id}"
            raise RuntimeError(msg)

        ctx = ComponentContext(self._client, interaction, (ir := asyncio.Event()))
        callback_task = asyncio.create_task(self._handle_with_context(ctx, callback))
        event_wait_task = asyncio.create_task(ir.wait())
        tasks = (event_wait_task, callback_task)

        finished, unfinished = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)

        yield None

        if callback_task not in finished:
            await callback_task

        for task in tasks:
            if task.done():
                continue

            task.cancel()

            try:
                await task
            except asyncio.CancelledError:
                pass

    async def _handle_with_context(self, ctx: ComponentContext, callback: ComponentCallbackT) -> None:
        async with self._client.di.enter_context(lightbulb.di.Contexts.DEFAULT):
            await callback(ctx)

    def add(self, common_prefix: str, callback: ComponentCallbackT) -> None:
        if common_prefix in self._handlers:
            msg = f"common prefix '{common_prefix}' already registered"
            raise ValueError(msg)

        self._handlers[common_prefix] = callback

    def remove(self, common_prefix: str) -> None:
        self._handlers.pop(common_prefix, None)


class ComponentLoadable(lightbulb.Loadable):
    __slots__ = ("_callback", "_common_prefix")

    def __init__(self, common_prefix: str, callback: ComponentCallbackT) -> None:
        self._common_prefix = common_prefix
        self._callback = callback

    async def load(self, _: lightbulb.Client) -> None:
        current_handler = handler.get()
        current_handler.add(self._common_prefix, lightbulb.di.with_di(self._callback))

    async def unload(self, _: lightbulb.Client) -> None:
        current_handler = handler.get()
        current_handler.remove(self._common_prefix)
