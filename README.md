CLANKERBOT
==========
A Discord chatbot that learns from channel history and text files,
then generates responses using a weighted Markov chain.

REQUIREMENTS
------------
Python 3.10+
Discord

SETUP
-----
1. Fill in config.py:
   - DISCORD_TOKEN    : your bot token (Discord token may be hard coded in which may lead to vulnerabilities)
   - CHANNEL_ID       : ID of the channel the bot reads history from
   - STORAGE_LOCATION : path to database (e.g. data/clanker.db)

2. Enable the following in the Discord Developer Portal:
   - Message Content Intent (required to read messages)


RUNNING THE BOT
---------------
    python main.py


TRAINING FROM FILES
-------------------
Drop .txt files into the /content folder.
Run manually:
    python datascrape.py


FILE STRUCTURE
--------------
main.py         Bot entry point, Discord events, hourly job
utilitys.py     Message cleaning, attention, response generation, lore fetching
db.py           SQLite helpers (menu items and ingredients)
config.py       Tokens, IDs, and settings
datascrape.py   Standalone script to train from /content .txt files
data/           SQLite database lives here
content/        Drop .txt training files here


COMMANDS
--------
!ping   Replies with "pong!" — basic connectivity check
