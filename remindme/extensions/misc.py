from __future__ import annotations

import datetime

import lightbulb

loader = lightbulb.Loader()


@loader.command
class Ping(lightbulb.SlashCommand, name="ping", description="Ping the bot!"):
    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        latency = datetime.datetime.now(tz=datetime.UTC) - ctx.interaction.created_at

        await ctx.respond(f"Pong in {latency.total_seconds() * 1_000:.0f}ms!", ephemeral=True)
