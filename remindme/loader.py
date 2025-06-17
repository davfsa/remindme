from __future__ import annotations

import typing

import lightbulb

from remindme import interaction_handlers

if typing.TYPE_CHECKING:
    ContextT = typing.TypeVar("ContextT")
    InteractionCallbackT = typing.Callable[
        typing.Concatenate[ContextT, ...], typing.Coroutine[typing.Any, typing.Any, None]
    ]


class Loader(lightbulb.Loader):
    def component(
        self, custom_id: str
    ) -> typing.Callable[
        [InteractionCallbackT[interaction_handlers.ComponentContext]],
        InteractionCallbackT[interaction_handlers.ComponentContext],
    ]:
        def _inner(
            func: InteractionCallbackT[interaction_handlers.ComponentContext],
        ) -> InteractionCallbackT[interaction_handlers.ComponentContext]:
            self.add(interaction_handlers.ComponentLoadable(custom_id, func))
            return func

        return _inner

    def modal(
        self, custom_id: str
    ) -> typing.Callable[
        [InteractionCallbackT[interaction_handlers.ModalContext]],
        InteractionCallbackT[interaction_handlers.ModalContext],
    ]:
        def _inner(
            func: InteractionCallbackT[interaction_handlers.ModalContext],
        ) -> InteractionCallbackT[interaction_handlers.ModalContext]:
            self.add(interaction_handlers.ModalLoadable(custom_id, func))
            return func

        return _inner
