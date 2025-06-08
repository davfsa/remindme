-- name: GetExpiredReminders :many
SELECT *
FROM reminders
WHERE expire_at < NOW();

-- name: CreateReminder :one
INSERT INTO reminders (user_id, description, expire_at)
VALUES ($1, $2, $3)
RETURNING *;
;

-- name: CreateReminderWithReference :one
INSERT INTO reminders (user_id, description, expire_at, reference_message_id, reference_channel_id, reference_guild_id)
VALUES ($1, $2, $3, $4, $5, $6)
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