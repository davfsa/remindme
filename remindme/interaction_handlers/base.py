from __future__ import annotations

import abc
import asyncio
import typing

import hikari
import lightbulb

InteractionT_co = typing.TypeVar("InteractionT_co", bound="InteractionProtocol", covariant=True)
ContextT = typing.TypeVar("ContextT", bound="ContextProtocol")
HandlerT = typing.TypeVar("HandlerT", bound="BaseInteractionHandler")

if typing.TYPE_CHECKING:
    import contextvars

    InteractionCallbackT = typing.Callable[["ContextT"], typing.Coroutine[typing.Any, typing.Any, None]]

    class ContextProtocol(typing.Protocol[InteractionT_co]):
        def __init__(
            self, client: lightbulb.Client, interaction: InteractionT_co, initial_response_sent: asyncio.Event
        ) -> None: ...

    class InteractionProtocol(typing.Protocol):
        @property
        def custom_id(self) -> str: ...


class BaseInteractionHandler(typing.Generic[InteractionT_co, ContextT]):
    __slots__ = ("_client", "_context_type", "_handlers")

    _context_type_: type[ContextT] = NotImplemented
    _interaction_type_: type[InteractionT_co] = NotImplemented

    def __init__(self, client: lightbulb.Client) -> None:
        if self._context_type_ is NotImplemented:
            msg = "'_context_type_' has not been set"
            raise RuntimeError(msg)

        if self._interaction_type_ is NotImplemented:
            msg = "'_interaction_type_' has not been set"
            raise RuntimeError(msg)

        self._client = client
        self._handlers: dict[str, InteractionCallbackT] = {}

        app = client.app
        assert isinstance(app, hikari.InteractionServerAware)
        app.interaction_server.set_listener(self._interaction_type_, self._handle_interaction, replace=True)  # type: ignore

    async def _handle_interaction(self, interaction: InteractionProtocol) -> typing.AsyncGenerator[None]:
        callback = self._handlers.get(interaction.custom_id.split(":")[0])

        if not callback:
            msg = f"No callback found for id: {interaction.custom_id}"
            raise RuntimeError(msg)

        ctx = self._context_type_(self._client, interaction, (ir := asyncio.Event()))
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

    async def _handle_with_context(self, ctx: ContextT, callback: InteractionCallbackT[ContextT]) -> None:
        async with self._client.di.enter_context(lightbulb.di.Contexts.DEFAULT):
            await callback(ctx)

    def add(self, common_prefix: str, callback: InteractionCallbackT[ContextT]) -> None:
        if common_prefix in self._handlers:
            msg = f"common prefix '{common_prefix}' already registered"
            raise ValueError(msg)

        self._handlers[common_prefix] = callback

    def remove(self, common_prefix: str) -> None:
        self._handlers.pop(common_prefix, None)


class BaseLoadable(lightbulb.Loadable, typing.Generic[HandlerT], abc.ABC):
    __slots__ = ("_callback", "_common_prefix")

    _handler_contextvar_: contextvars.ContextVar[HandlerT] = NotImplemented

    def __init__(self, common_prefix: str, callback: InteractionCallbackT) -> None:
        if self._handler_contextvar_ is NotImplemented:
            msg = "'_handler_contextvar_' has not been set"
            raise RuntimeError(msg)

        self._common_prefix = common_prefix
        self._callback = callback

    async def load(self, client: lightbulb.Client) -> None:  # noqa: ARG002
        current_handler = self._handler_contextvar_.get()
        current_handler.add(self._common_prefix, lightbulb.di.with_di(self._callback))

    async def unload(self, client: lightbulb.Client) -> None:  # noqa: ARG002
        current_handler = self._handler_contextvar_.get()
        current_handler.remove(self._common_prefix)
