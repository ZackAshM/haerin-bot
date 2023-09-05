"""This contains functions that used in initializing the bot"""

import config
import json
import discord
from discord.ext import commands
import aiosqlite

with open('config.json', 'r') as config_file:
    configData = json.load(config_file)

async def load_extensions(bot):
    for cog in configData['COGS']:
        try:
            await bot.load_extension(cog)
        except Exception as e:
            print(f'Error loading cog {cog}: {e}')

async def get_prefix(bot, message):
    """Prefix function to allow customizable prefix"""
    if message:
        async with aiosqlite.connect(configData["DATABASE"]) as db:
            async with db.cursor() as cursor:
                await cursor.execute("SELECT prefix FROM config WHERE guildID=?", (message.guild.id,))
                result = await cursor.fetchone()
            if result is not None:
                return commands.when_mentioned_or(result[0])(bot,message)
            else:
                return commands.when_mentioned_or(configData['DEFAULT_PREFIX'])(bot,message)
            
async def initialize_database_per_guild(guild):
    """Create database row for a guild in all tables"""
    guildID = guild.id
    database = configData["DATABASE"]
    db_tables = configData["DATABASE_TABLES"]

    for table_name in db_tables.keys():
        db_tables[table_name]["guildID INTEGER PRIMARY KEY"] = guildID  # set guild ID

        # prepare data for sql command strings
        columns_full = db_tables[table_name].keys()
        default_values = db_tables[table_name].values()
        cols = ', '.join([col.split(' ')[0] for col in columns_full])
        question_string = ', '.join(['?'] * len(default_values))

        # now update guild row data in all database tables
        async with aiosqlite.connect(database) as db:
            async with db.cursor() as cursor:
                await cursor.execute(f'SELECT COUNT(*) FROM {table_name} WHERE guildID = ?', (guildID,))
                exists = await cursor.fetchone()
                if not exists[0]:
                    await cursor.execute(
                        f'INSERT INTO {table_name} ({cols}) VALUES ({question_string})', (*default_values,)
                    )
                    await db.commit()