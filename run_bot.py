import asyncio
import os
import sys

import discord
from discord.ext import bridge, commands
from dotenv import load_dotenv

from EmbedManager import EmbedManager

# from InstaReposter import InstaReposter
from NewsUpdater import NewsUpdater

load_dotenv(dotenv_path=".env")
TOKEN = os.getenv("DISCORD_TOKEN")

# Configure intents
intents = discord.Intents.default()
intents.message_content = True
intents.presences = True
intents.members = True

bot = bridge.Bot(command_prefix="]", intents=intents)
bot.add_cog(EmbedManager(bot))
bot.add_cog(NewsUpdater(bot))
# bot.add_cog(InstaReposter(bot))


def is_guild_owner():
    def predicate(ctx):
        return ctx.guild is not None and ctx.guild.owner_id == ctx.author.id

    return commands.check(predicate)


@bot.bridge_command(name="add_cog")
@commands.check_any(commands.is_owner(), is_guild_owner())
async def add_cog(ctx, cog_name: str):
    bot.load_extension(cog_name)
    await ctx.send(f"Added cog {cog_name}.")


@bot.bridge_command(name="remove_cog")
@commands.check_any(commands.is_owner(), is_guild_owner())
async def remove_cog(ctx, cog_name: str):
    bot.remove_cog(cog_name)
    await ctx.send(f"Removed cog {cog_name}.")


def main():
    bot.run(TOKEN)


if __name__ == "__main__":
    main()
