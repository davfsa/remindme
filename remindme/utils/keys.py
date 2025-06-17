from __future__ import annotations

REMINDER_SNOOZE_SELECT = "remindme_snooze_select"
REMINDER_CREATE_FROM_MESSAGE_MODAL_CUSTOM_ID = "remindme_create_from_message_modal"
REMINDER_SNOOZE_INPUT_CUSTOM = "remindme_snooze_custom_modal"


def make_key(master_key: str, *args: object) -> str:
    return f"{master_key}:" + ":".join(str(arg) for arg in args)
