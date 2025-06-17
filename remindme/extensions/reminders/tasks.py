from __future__ import annotations

import asyncio
import datetime
import logging

import hikari  # noqa: TC002 - Needed for DI
import lightbulb

import remindme
from remindme import db
from remindme.utils import reminders as utils

logger = logging.getLogger("remindme.ext.reminders")
loader = remindme.Loader()

REMINDER_POST_EXPIRE_LIFETIME = datetime.timedelta(hours=3)


@loader.task(lightbulb.uniformtrigger(5), auto_start=True, max_failures=-1)
async def check_reminders(queries: db.Queries, rest: hikari.api.RESTClient) -> None:
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


@loader.task(lightbulb.uniformtrigger(10), auto_start=True, max_failures=-1)
async def cleanup_reminders(queries: db.Queries) -> None:
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
