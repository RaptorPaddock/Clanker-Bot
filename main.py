import asyncio
from pathlib import Path

import discord
from discord.ext import commands, tasks

import config
import db
import utilitys

# Startup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (id: {bot.user.id})")

@bot.event
async def on_message(message: discord.Message):
    """Handle incoming messages and optionally train or respond."""
    if message.author.bot:
        return
    content = message.content or ""
    if utilitys.contains_trigger(content, config.TRIGGER_WORD):
        cleaned = utilitys.clean_message(content)
        reply_text = utilitys.gen_response(cleaned)
        if reply_text:
            await message.channel.send(reply_text)
            print(f"Replied to message: {content} with: {reply_text}")
    # Always process commands so e.g. !ping works regardless of trigger words
    await bot.process_commands(message)

@bot.command()
async def ping(ctx: commands.Context):
    await ctx.send("pong!")

async def main() -> None:
    db.init_db()
    await bot.start(config.DISCORD_TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
