import asyncio
import os
import sys
import click
import discord
from loguru import logger
from dotenv import load_dotenv
from discord.ext import commands
from EmbedManager import EmbedManager
from NewsUpdater import NewsUpdater

load_dotenv(dotenv_path='.env')
TOKEN = os.getenv('DISCORD_TOKEN')
NEWS_CHANNEL_ID = int(os.getenv('NEWS_CHANNEL_ID'))

# Configure intents
intents = discord.Intents.default()
intents.message_content = True
intents.presences = True
intents.members = True

bot = commands.Bot(command_prefix=']', intents = intents)
bot.add_cog(EmbedManager(bot))
bot.add_cog(NewsUpdater(bot))

def is_guild_owner():
    def predicate(ctx):
        return ctx.guild is not None and ctx.guild.owner_id == ctx.author.id
    return commands.check(predicate)

@bot.command(name='add_cog')
@commands.check_any(commands.is_owner(), is_guild_owner())
async def add_cog(ctx, cog_name: str):
    bot.load_extension(cog_name)
    logger.success(f"Loaded cog: {cog_name}")
    await ctx.send(f"Added cog {cog_name}.")

@bot.command(name='remove_cog')
@commands.check_any(commands.is_owner(), is_guild_owner())
async def remove_cog(ctx, cog_name: str):
    bot.remove_cog(cog_name)
    logger.success(f"Removed cog: {cog_name}")
    await ctx.send(f"Removed cog {cog_name}.")

@click.command()
@click.option(
    "-d",
    "--debug",
    is_flag=True,
    help="Enable debug mode. Prints debug messages to the console.",
)
def main(debug: bool):
    if not debug:
        # Default loguru level is DEBUG
        logger.remove()
        logger.add(os.sys.stderr, level="INFO")
    
    bot.run(TOKEN)


if __name__ == "__main__":
    main()
    
