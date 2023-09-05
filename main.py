import config
import json
import discord
from discord.ext import commands
# import aiosqlite


from utils.database import createTable, db_execute
import utils.bot_initialization as bot_init

with open('config.json', 'r') as config_file:
    configData = json.load(config_file)

logger = config.logging.getLogger("bot")

# the main function
def run():

    print('- Haerin Bot starting...')

    # -- INTENTS --
    intents = discord.Intents.default()
    intents.guilds = True
    intents.members = True
    intents.emojis_and_stickers = True
    intents.guild_messages = True
    intents.dm_messages = True
    intents.message_content = True
    intents.guild_reactions = True
    intents.guild_typing = True
    intents.webhooks = True

    # -------------

    bot = commands.Bot(command_prefix=bot_init.get_prefix, 
                       intents=intents)
    bot.remove_command('help')

    @bot.event
    async def on_ready():

        # initialize database - create all tables and update columns
        db_tables = configData["DATABASE_TABLES"]
        for table_name in db_tables.keys():
            db_path = configData["DATABASE"]
            default_values = db_tables[table_name]
            await createTable(db_path, table_name, default_values)

        # initialize all guilds if needed
        for guild in bot.guilds:
            await bot_init.initialize_database_per_guild(guild)

        # initialize extensions/cogs
        await bot_init.load_extensions(bot)

        # Set the bot's status
        activity = discord.Activity(type=discord.ActivityType.listening, name="Zero by NewJeans", 
                                    # url="https://youtu.be/XIOoqJyx8E4?si=qEVr46AJISjDToUc", 
                                    # state='https://youtu.be/XIOoqJyx8E4?si=qEVr46AJISjDToUc',
                                    # details='testing where this shows up'
                                    )
        await bot.change_presence(activity=activity)

        logger.info(f"User: {bot.user} (ID: {bot.user.id})")

        print('- Haerin Bot is running '+'-'*50)

    @bot.event
    async def on_guild_join(guild):
        await bot_init.initialize_database_per_guild(guild)
    
    @bot.event
    async def on_command_error(ctx, error):
        """Send a message if an input error occured"""
        prefix = (await db_execute(configData['DATABASE'], 'SELECT prefix FROM config WHERE guildID = ?', ctx.guild.id))[0]
        helpStr = f'Use `{prefix}help` for help'
        tooLong = '...' if len(str(error)) > 2000 else ''
        err = str(error)[:int(2000 - len(helpStr))]
        emb = discord.Embed(
            title='Input Error',
            description=f'{err}{tooLong}\n\n({helpStr})',
            color=discord.Color.yellow(),
        )
        emb.set_thumbnail(url='https://cdn.discordapp.com/attachments/825734128917413959/1145924966462791832/haerin-thumbnail.gif')

        await ctx.reply(embed=emb, delete_after=20)

    bot.run(configData["TOKEN"], root_logger=True)

if __name__ == "__main__":
    run()