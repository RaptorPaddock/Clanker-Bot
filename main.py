import asyncio
import re
import discord
import random
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

import db
import config

CHANNEL_ID = config.CHANNEL_ID
TRIGGER_WORD = config.TRIGGER_WORD
MAX_GENERATED_TOKENS = config.MAX_GENERATED_TOKENS
CHANNEL_HISTORY_LIMIT = config.CHANNEL_HISTORY_LIMIT


_URL_RE = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
_DISCORD_TAG_RE = re.compile(r"<(@!?\d+|@&\d+|#\d+|a?:\w+:\d+)>")


def clean_message(text: str) -> str:
    """Removes unessary things"""
    text = _URL_RE.sub("", text)
    text = _DISCORD_TAG_RE.sub("", text)
    text = text.replace("@everyone", "").replace("@here", "")
    text = text.replace("\r", " ").replace("\n", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def ingest_dd(pellets: str, response: str) -> None:
    """Train on a user message and the bot's reply."""
    resp_tokens = clean_message(response).split()
    for token in clean_message(pellets).split():
        db.add_menu_item(token)
        for resp_token in resp_tokens:
            db.add_ingredient_or_increment(token, resp_token)


def ingest_others(lore: List[str]) -> None:
    """Train on consecutive lore lines."""
    for i in range(len(lore) - 1):
        first_tokens = lore[i].split()
        next_tokens = lore[i + 1].split()
        for token in first_tokens:
            db.add_menu_item(token)
            for next_token in next_tokens:
                db.add_ingredient_or_increment(token, next_token)


def attention_score(token: str, idx: int, tokens: List[str], trigger_idx: int) -> float:
    """Combined attention score: rarity * position * trigger proximity."""
    # 1. Rarity: tokens with less training data are more specific/informative
    ingredients = db.list_ingredients(token)
    total_count = sum(c for _, c in ingredients) if ingredients else 0
    rarity = 1.0 / (1.0 + total_count)
    # 2. Position: words later in the message are more relevant (recency)
    position = (idx + 1) / len(tokens)
    # 3. Trigger proximity: words closer to the trigger word carry more intent
    distance = abs(idx - trigger_idx)
    proximity = 1.0 / (1.0 + distance)
    return rarity * position * proximity


def gen_response(pellets: str) -> str:
    """Generate a response by weighted-random sampling of trained ingredients."""
    max_tokens: int = MAX_GENERATED_TOKENS
    separator = " "
    stop_chars = ".!?"
    tokens = pellets.split()
    trigger_idx = next(
        (i for i, t in enumerate(tokens) if contains_trigger(t)),
        len(tokens) - 1,
    )
    input_weights: Dict[str, float] = defaultdict(float)
    for idx, token in enumerate(tokens):
        score = attention_score(token, idx, tokens, trigger_idx)
        for ingredient, count in db.list_ingredients(token):
            input_weights[ingredient] += float(count) * score
    if not input_weights:
        return ""
    stop_set = set(stop_chars)
    out_parts: List[str] = []
    current_weights: Dict[str, float] = input_weights
    for _ in range(max_tokens):
        items: List[Tuple[str, float]] = [(k, w) for k, w in current_weights.items() if w > 0]
        if not items:
            break
        chosen = random.choices([k for k, _ in items], weights=[w for _, w in items], k=1)[0]
        out_parts.append(chosen)
        if stop_set and any(ch in separator.join(out_parts) for ch in stop_set):
            break
        next_ingredients = db.list_ingredients(chosen)
        if next_ingredients:
            current_weights = defaultdict(float)
            for ingredient, count in next_ingredients:
                current_weights[ingredient] += float(count)
        else:
            current_weights = input_weights
    return separator.join(out_parts)


def contains_trigger(text: str, triggers=None) -> bool:
    text = (text or "").lower()
    """Checks for trigger words"""
    if not text:
        return False
    triggers = TRIGGER_WORD if triggers is None else triggers
    trigger_list = (
        [str(t).lower() for t in triggers]
        if isinstance(triggers, (list, tuple, set))
        else [str(triggers).lower()]
    )
    return any(t and t in text for t in trigger_list)


async def get_user_input(
    client: discord.Client,
    user_id: int,
    channel_id: int,
    timeout: int = 60,
) -> Optional[discord.Message]:
    """For future self training"""
    def check(m: discord.Message) -> bool:
        return m.author.id == user_id and m.channel.id == channel_id
    try:
        return await client.wait_for("message", check=check, timeout=timeout)
    except asyncio.TimeoutError:
        return None


async def get_lore(bot: discord.Client) -> List[str]:
    """Fetch and clean historical messages from the configured lore channel."""
    channel = bot.get_channel(CHANNEL_ID)
    if channel is None:
        print("Channel not found (wrong ID) or bot lacks access.")
        return []
    lines: List[str] = []
    since = datetime.now(timezone.utc) - timedelta(days=CHANNEL_HISTORY_LIMIT)
    print(f"      Fetching up to {CHANNEL_HISTORY_LIMIT} days of history from channel {CHANNEL_ID}...")
    async for msg in channel.history(limit=None, after=since, oldest_first=True):
        text = clean_message(msg.content or "")
        if not text:
            continue
        lines.append(text)
        if len(lines) % 500 == 0:
            print(f"      ...fetched {len(lines)} messages so far")
    print(f"      Fetched {len(lines)} messages total from lore channel")
    return lines
