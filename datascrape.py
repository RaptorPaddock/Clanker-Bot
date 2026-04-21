import asyncio
from pathlib import Path

import discord

import config
import db
import utilitys


async def run():
    print("[1/4] Starting datascrape...")

    # Fetch Discord lore using a temporary client
    intents = discord.Intents.default()
    intents.message_content = True
    client = discord.Client(intents=intents)
    lore: list = []

    @client.event
    async def on_ready():
        nonlocal lore
        print(f"[2/4] Connected to Discord as {client.user}. Fetching channel history...")
        lore = await utilitys.get_lore(client)
        await client.close()

    await client.start(config.DISCORD_TOKEN)

    print(f"[3/4] Ingesting {len(lore)} messages into database...")
    utilitys.ingest_others(lore)
    print(f"[3/4] Done ingesting Discord messages.")

    # Process text files in the content/ folder
    folder = Path(__file__).parent / "content"
    txt_files = list(folder.glob("*.txt")) if folder.exists() else []
    if txt_files:
        print(f"[4/4] Processing {len(txt_files)} text file(s) in content/...")
        for txt_path in txt_files:
            print(f"      Reading {txt_path.name}...")
            content = txt_path.read_text(encoding="utf-8", errors="replace")
            lines = [ln.strip() for ln in content.splitlines() if ln.strip()]
            print(f"      Ingesting {len(lines)} lines from {txt_path.name}...")
            for idx in range(len(lines) - 1):
                first = utilitys.clean_message(lines[idx])
                second = utilitys.clean_message(lines[idx + 1])
                for token in first.split():
                    db.add_menu_item(token)
                    for next_token in second.split():
                        db.add_ingredient_or_increment(token, next_token)
            print(f"      Done with {txt_path.name}. Deleting...")
            try:
                txt_path.unlink()
            except FileNotFoundError:
                pass
            except PermissionError:
                print(f"      Could not delete {txt_path.name}: file is in use")
    else:
        print("[4/4] No text files found in content/. Skipping.")

    print("Done! Datascrape complete.")


if __name__ == "__main__":
    db.init_db()
    asyncio.run(run())
