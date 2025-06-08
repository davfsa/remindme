CREATE TABLE IF NOT EXISTS reminders
(
    id                   BIGSERIAL                NOT NULL,
    user_id              BIGINT                   NOT NULL,
    description          VARCHAR(4000)            NOT NULL,
    expire_at            TIMESTAMP WITH TIME ZONE NOT NULL,
    reference_message_id BIGINT,
    reference_channel_id BIGINT,
    reference_guild_id   BIGINT
);

CREATE INDEX IF NOT EXISTS idx_reminders_expire_at ON reminders (expire_at DESC);

CREATE TABLE IF NOT EXISTS dm_channels
(
    user_id    BIGINT NOT NULL,
    channel_id BIGINT NOT NULL
);