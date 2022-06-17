import asyncio
import discord
import json
import feedparser
import datetime
from time import mktime
from discord.ext import commands, tasks
from utilities import load_json

LANGS = ["sme", "smj", "sma"]

def parse_feed(url: str, cat: str = "") -> list:
    fd = feedparser.parse(url)
    entries = fd.entries
    if cat:
        valid_entries = []
        for e in entries:
            if "tags" in e:
                cats = [t.term for t in e.tags]
                if cat == "Sápmi": # YLE sme needs special treatment
                    if not any([c in cats for c in ["Säämi", "Sää´mjânnam"]]):
                        valid_entries.append(e)
                elif (cat in cats):
                    valid_entries.append(e)
            elif cat == "Ođđasat - Davvisámegillii":
                # If entry has no tags the NRK article is sme.
                valid_entries.append(e)
        return valid_entries
    return entries

def filter_new_entries(entries: list, last_time: int) -> list:
    # GUIDs of the entries are always assumed to be sorted (high -> low = newest -> oldest)
    new_entries = []
    for e in entries:
        e_time = mktime(e.published_parsed)
        if e_time > last_time:
            new_entries.append(e)
        else:
            break
    return new_entries

def create_embed(entry, category: dict):
    # Creates an embed object that can be sent in discord
    try:
        timestamp = datetime.datetime.fromtimestamp(mktime(entry.published_parsed))
        embed = discord.Embed(title=entry.title, url=entry.link, description=entry.summary, color=category["color"], timestamp=timestamp)
        
        embed.set_author(name=category["name"], url=category["url"], icon_url=category["icon_url"])
        #embed.set_thumbnail(url=category["thumbnail"])
        if "media_content" in entry:
            embed.set_image(url=entry.media_content[0]["url"])
        elif len(entry.links) > 1:
            for link in entry.links:
                if link["type"] == "image/jpeg":
                    # The thumbnails of Yle's newsfeed are found here
                    # Remove "//w_205,h_115,q_70" in url to find a higher res thumbnail
                    embed.set_image(url=link["href"].replace(r"//w_205,h_115,q_70", ""))
        # send with await ctx.send(embed=embed)
        return embed
    except Exception as err:
        print(err)
        exit(1)
    
    
def update_feed_and_create_embeds(last_time: int, category: dict):
    entries = parse_feed(category["rss"], cat=category["name"])
    new_entries = filter_new_entries(entries, last_time)
    embed_pairs = [(create_embed(e, category), int(mktime(e.published_parsed)) ) for e in new_entries]
    embed_pairs.reverse() # Reverse embeds in the order to be sent (oldest to newest)
    return embed_pairs


class NewsUpdater(commands.Cog, name='NewsUpdater'):
    def __init__(self, bot, channel_id: int):
        self.bot = bot
        self.channel_id = channel_id
        self.newsfeeds = load_json("config/newsfeeds.json")
        self.check_and_send_news_embeds.start()

    @tasks.loop(minutes=5)
    async def check_and_send_news_embeds(self):
        try:
            to_send = []
            for lang in LANGS:
                e_pairs = update_feed_and_create_embeds(self.newsfeeds["last_time"], self.newsfeeds[lang])
                to_send.extend(e_pairs)

            to_send.sort(key=lambda pair: pair[1])
            
            if to_send:
                self.newsfeeds["last_time"] = to_send[-1][1]

                with open("config/newsfeeds.json", "w", encoding="utf-8") as f:
                    f.write(json.dumps(self.newsfeeds, indent="\t", ensure_ascii=False))
                message_channel = self.bot.get_channel(self.channel_id)
                for embed, t in to_send:
                    await message_channel.send(embed=embed)
        except Exception as err:
            print(err)
            exit(1)

    @check_and_send_news_embeds.before_loop
    async def before_check(self):
        print("Waiting for bot to be ready before printing news...")
        await self.bot.wait_until_ready()
        print("Ready")

def setup(bot):
    bot.add_cog(NewsUpdater(bot))
    print("NewsUpdater cog up and ready!")