import asyncio
import datetime
import json
import os
from random import choice
from time import mktime

import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv
from instagrapi import Client

load_dotenv(dotenv_path=".env")

NOEREH_COLORS = [8373350, 16569858, 15677476, 16359196, 16233938, 10207719, 14005905]
LOGIN_SESSION_FILE = "config/session.json"
RAND_DELAY_RANGE = [1, 10]
LOOP_MINUTES = 10
FEED_LENGTH = 11


def filter_new_medias(medias: list, last_time: int) -> list:
    # GUIDs of the entries are always assumed to be sorted (high -> low = newest -> oldest)
    new_entries = []
    for m in medias:
        e_timestamp = int(m.taken_at.timestamp())
        if e_timestamp > last_time:
            if m.video_duration <= 120:
                new_entries.append(m)
        else:
            break
    return new_entries


class InstaReposter(commands.Cog, name="InstaReposter"):
    def __init__(self, bot, anno_channel_id: int = 0):
        self.bot = bot
        self.username = os.getenv("INSTA_USERNAME")
        self.user_id = os.getenv("INSTA_ID")
        self.cl = Client()
        try:
            self.cl.load_settings(LOGIN_SESSION_FILE)
        except FileNotFoundError:
            self.cl.login(self.username, os.getenv("INSTA_PASS"))
            self.cl.dump_settings(LOGIN_SESSION_FILE)
        else:
            self.cl.login(self.username, os.getenv("INSTA_PASS"))

        self.cl.delay_range = RAND_DELAY_RANGE

        self.anno_channel_id = (
            anno_channel_id
            if anno_channel_id != 0
            else int(os.getenv("ANNO_CHANNEL_ID"))
        )

        self.last_time = -1
        if self.last_time == -1:
            # If last_time has never been updated, update it to the current unix timestamp
            # so that the bot doesn't spam the newsfeed channel with news on the first-time run.
            self.last_time = int(mktime(datetime.datetime.now().timetuple()))

        self.check_and_send_insta_embeds.start()

    def create_embed(self, media):
        # Creates an embed object that can be sent in discord
        print(f"Handling media: {media.code}")
        time_data = media.taken_at
        username = media.user.username
        full_name = media.user.full_name
        embed = discord.Embed(
            title=f"@{username} på instagram",
            url=f"https://www.instagram.com/p/{media.code}",
            description=media.caption_text,
            color=choice(NOEREH_COLORS),
            timestamp=time_data,
        )

        embed.set_author(
            name=full_name,
            url=f"https://www.instagram.com/{username}/",
            icon_url="https://cdn.sanity.io/images/g3qdmru2/production/016074ca8a2fbcdeed29522b3b236c37f056cffa-2400x2400.jpg?w=256&h=256",
        )
        # media_type: 1- photo, 2- video, IGTV, Reel, 8- album
        file_path = None
        if media.media_type == 1:
            file_path = self.cl.photo_download(media.pk, "data")
            embed.set_image(url=f"attachment://{file_path.name}")
        elif media.media_type == 2:
            file_path = self.cl.video_download(media.pk, "data")
        elif media.media_type == 8:
            file_path = self.cl.photo_download(media.resources[0].pk, "data")
            embed.set_image(url=f"attachment://{file_path.name}")

        discord_file = discord.File(file_path, filename=file_path.name)

        return embed, discord_file

    @tasks.loop(minutes=LOOP_MINUTES)
    async def check_and_send_insta_embeds(self):
        self.cl.get_timeline_feed()
        new_medias = filter_new_medias(
            self.cl.user_medias(self.user_id, FEED_LENGTH), self.last_time
        )

        if not new_medias:
            return

        self.last_time = int(new_medias[0].taken_at.timestamp())

        e_pairs = [(self.create_embed(m)) for m in new_medias]

        if e_pairs:
            message_channel = self.bot.get_channel(self.anno_channel_id)
            for embed, discord_file in reversed(e_pairs):
                await message_channel.send(file=discord_file, embed=embed)

    @check_and_send_insta_embeds.before_loop
    async def before_check(self):
        print("Waiting for bot to be ready before checking insta feed...")
        await self.bot.wait_until_ready()
        print("Ready to post insta feed")
        await asyncio.wait(LOOP_MINUTES * 60)

    @commands.command(name="insta_post", help="Post an instagram post")
    async def insta_post(self, ctx, insta_url: str, channel_id: int = 0):
        post_code = insta_url.rsplit("p/", maxsplit=1)[-1].replace("/", "")
        media_pk = self.cl.media_pk_from_code(post_code)
        media = self.cl.media_info(media_pk)
        embed, discord_file = self.create_embed(media)
        if channel_id != 0:
            message_channel = self.bot.get_channel(channel_id)
            await message_channel.send(file=discord_file, embed=embed)
        else:
            await ctx.send(file=discord_file, embed=embed)


def setup(bot):
    bot.add_cog(InstaReposter(bot))
    print("NewsUpdater cog up and ready!")
