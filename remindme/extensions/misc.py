from __future__ import annotations

import lightbulb

loader = lightbulb.Loader()


@loader.command
class Ping(lightbulb.SlashCommand, name="ping", description="Ping the bot!"):
    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        await ctx.respond("Pong!")
