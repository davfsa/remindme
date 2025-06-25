-- name: GetReminder :one
SELECT *
FROM reminders
WHERE id = $1;

-- name: GetExpiredReminders :many
SELECT *
FROM reminders
WHERE expire_at < NOW()
  AND handled = FALSE;

-- name: GetHandledReminders :many
SELECT *
FROM reminders
WHERE handled = TRUE
  AND expire_at < $1;
;

-- name: GetRemindersCountFor :one
SELECT COUNT(*)
FROM reminders
WHERE user_id = $1
  AND handled = FALSE;

-- name: GetRemindersFor :many
SELECT *
FROM reminders
WHERE user_id = $1
  AND handled = FALSE
ORDER BY expire_at DESC
OFFSET $2 ROWS FETCH NEXT $3 ROWS ONLY;

-- name: CreateReminder :one
INSERT INTO reminders (user_id, description, expire_at)
VALUES ($1, $2, $3)
RETURNING *;
;

-- name: CreateReminderWithReference :one
INSERT INTO reminders (user_id, description, expire_at, reference_message_id, reference_channel_id, reference_guild_id)
VALUES ($1, $2, $3, $4, $5, $6)
RETURNING *;

-- name: AddReminderReferenceMessage :exec
UPDATE reminders
SET reference_message_id=$1,
    reference_channel_id=$2,
    reference_guild_id=$3
WHERE id = $4;

-- name: MarkReminderAsHandled :exec
UPDATE reminders
SET handled = TRUE
WHERE id = $1;

-- name: RescheduleReminder :one
UPDATE reminders
SET handled   = FALSE,
    expire_at = $1
WHERE id = $2
RETURNING *;

-- name: DeleteReminder :exec
DELETE
FROM reminders
WHERE id = $1;

-- name: GetDmChannelForUser :one
SELECT channel_id
FROM dm_channels
WHERE user_id = $1;

-- name: AddDmChannel :exec
INSERT INTO dm_channels (user_id, channel_id)
VALUES ($1, $2);