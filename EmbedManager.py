import asyncio
import json
import re
from email import message

import discord
import requests
from discord.ext import bridge, commands

MAX_EMBED_LENGTH = 4096
MULTIPAGE_TIMEOUT = 900  # Timeout period for page flipping with reacts


class EmbedManager(commands.Cog, name="EmbedManager"):
    def __init__(self, bot):
        self.bot = bot
        self.multipage_timeout = MULTIPAGE_TIMEOUT

    @staticmethod
    def generate_embed(title, passage, author_data, passage_url, color):
        embed = discord.Embed(
            title=title, description=passage, url=passage_url, color=color
        )
        embed.set_author(
            name=author_data["name"],
            url=author_data["url"],
            icon_url=author_data["icon"],
        )
        # embed.set_thumbnail(url=author_data["thumbnail"])
        return embed

    async def multi_page(self, ctx, embeds):
        pages = len(embeds)
        cur_page = 0
        for i, em in enumerate(embeds):
            pg = i + 1
            em.set_footer(text=f"Page {pg} of {pages}")

        message = await ctx.send(embed=embeds[0])

        await message.add_reaction("◀️")
        await message.add_reaction("▶️")

        valid_emoji = ["◀️", "▶️", "🗑️"]

        def check(reaction, user):
            # Make sure nobody except the command sender can interact with the "menu"
            # The user can't flip pages in multiple messages at once either
            nonlocal message
            return (
                user == ctx.author
                and reaction.message.id == message.id
                and str(reaction.emoji) in valid_emoji
            )

        while True:
            try:
                # wait for a reaction to be added
                # times out after MULTIPAGE_TIMEOUT seconds
                reaction, user = await self.bot.wait_for(
                    "reaction_add", timeout=self.multipage_timeout, check=check
                )

                if str(reaction.emoji) == "▶️" and cur_page != pages - 1:
                    cur_page += 1
                    await message.edit(embed=embeds[cur_page])
                    await message.remove_reaction(reaction, user)

                elif str(reaction.emoji) == "◀️" and cur_page > 0:
                    cur_page -= 1
                    await message.edit(embed=embeds[cur_page])
                    await message.remove_reaction(reaction, user)
                elif str(reaction.emoji) == "🗑️":
                    # Bot messages can be deleted by reacting with the waste basket emoji
                    await message.delete()
                    break
                else:
                    # remove reactions if the user tries to go forward on the last page or
                    # backwards on the first page
                    await message.remove_reaction(reaction, user)
            except (asyncio.TimeoutError, discord.errors.Forbidden):
                # end the loop if user doesn't react after MULTIPAGE_TIMEOUT seconds
                for r in valid_emoji:
                    await message.remove_reaction(r, self.bot.user)
                await message.clear_reactions()
                break

    async def deletables(self, ctx, messages):
        # Makes messages deletable by reacting wastebasket on them
        # Check mark reacts make reactions go away (but one may still delete them!)
        last_message = messages[-1]

        await last_message.add_reaction("✅")
        await last_message.add_reaction("🗑️")

        valid_emoji = ["✅", "🗑️"]

        def check(reaction, user):
            # Make sure nobody except the command sender can interact with the "menu"
            # The user can't flip pages in multiple messages at once either
            nonlocal last_message
            return (
                user == ctx.author
                and reaction.message.id == last_message.id
                and str(reaction.emoji) in valid_emoji
            )

        while True:
            try:
                # wait for a reaction to be added
                # times out after MULTIPAGE_TIMEOUT seconds
                reaction, user = await self.bot.wait_for(
                    "reaction_add", timeout=60, check=check
                )

                if str(reaction.emoji) == "✅":
                    await last_message.clear_reactions()
                elif str(reaction.emoji) == "🗑️":
                    for m in messages:
                        await m.delete()
                    break
                else:
                    # remove reactions if the user tries to go forward on the last page or
                    # backwards on the first page
                    await last_message.remove_reaction(reaction, user)
            except (asyncio.TimeoutError, discord.errors.Forbidden):
                # end the loop if user doesn't react after MULTIPAGE_TIMEOUT seconds
                for r in valid_emoji:
                    await last_message.remove_reaction(r, self.bot.user)
                await last_message.clear_reactions()
                break

    @bridge.bridge_command(
        name="create_embed", help="Creates an embed based on a json file."
    )
    async def create_embed(self, ctx, channel_id: int = None):
        if not ctx.message.attachments:
            await ctx.send("You need to attach a valid json file.")
        try:
            attachment_url = ctx.message.attachments[0].url
            file_request = requests.get(attachment_url)
            json_code = json.loads(file_request.text)
        except ValueError:
            await ctx.send("The file was not a valid json file.")
            return

        embed = discord.Embed.from_dict(json_code)

        if channel_id:
            channel = self.bot.get_channel(channel_id)
            await channel.send(embed=embed)
        else:
            await ctx.send(embed=embed)

    @bridge.bridge_command(
        name="edit_embed", help="Edit an already existing embed based on a json file."
    )
    async def edit_embed(self, ctx, message_link: str):
        if not ctx.message.attachments:
            await ctx.send("You need to attach a valid json file.")
        try:
            attachment_url = ctx.message.attachments[0].url
            file_request = requests.get(attachment_url)
            json_code = json.loads(file_request.text)
        except ValueError:
            await ctx.send("The file was not a valid json file.")
            return

        channel_id, message_id = message_link.rsplit("/")[-2:]
        channel_id, message_id = int(channel_id), int(message_id)
        channel = self.bot.get_channel(channel_id)
        msg = await channel.fetch_message(message_id)
        embed = discord.Embed.from_dict(json_code)
        await msg.edit(embed=embed)


def setup(bot):
    bot.add_cog(EmbedManager(bot))
    print("EmbedManager cog up and ready!")
