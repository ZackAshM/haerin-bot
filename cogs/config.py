import discord
from discord.ext import commands
import json
import aiosqlite
from utils.database import db_execute

with open('config.json', 'r') as config_file:
    configData = json.load(config_file)

def is_owner():
    async def predicate(ctx):
        return ctx.author.id == int(configData["AUTHOR"])
    return commands.check(predicate)

class Config(commands.Cog):
    """Control config options for Haerin Bot"""
    def __init__(self, bot):
        self.bot = bot
        self.db = configData["DATABASE"]

    
    @commands.command(
            aliases = ['prefix'],
            brief = "Set prefix"
    )
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def set_prefix(self, ctx, new_prefix=None):
        """
        Command: **[set_prefix | prefix]**

        Set a new prefix

        __Usage:__
        `{prefix}set_prefix <new prefix>`

        Permissions:
        administrator
        """

        current_prefix = (await db_execute(self.db, 'SELECT prefix FROM config WHERE guildID=?', ctx.guild.id))[0]
        
        if new_prefix is None:
            await ctx.send(f'>>> {self.set_prefix.help.format(prefix=current_prefix)}\n\nCurrent prefix is set to `{current_prefix}`')
            return
        
        if len(new_prefix) >= 4:
            await ctx.send('Invalid prefix. Choose something shorter.')
            return
        
        await db_execute(self.db, 'UPDATE config SET prefix=? WHERE guildID=?', new_prefix, ctx.guild.id, exec_type='update')
        await ctx.send(f'Prefix has been set to `{new_prefix}`. If there are issues, '+
                    f'use "{self.bot.user.mention} `set_prefix <new prefix>`" to set a different prefix')


    # -------------------------------------------------
    # -- OWNER ONLY -----------------------------------
    # -------------------------------------------------


    @commands.command(
        name = 'reload',
        aliases = ['r'],
        brief = 'Reload extensions/cogs',
        hidden=True
    )
    @is_owner()
    async def reload(self, ctx, *cogs):
        """
        Command: **[reload | r]**

        Reload extensions/cogs. Use the argument `all` to reload all cogs (excluding config).

        __Usage:__
        `{prefix}reload [<cog1 name> <cog2 name> ... | all]`

        Permissions:
        is_owner
        """
        prefix = (await db_execute(self.db, 'SELECT prefix FROM config WHERE guildID=?', ctx.guild.id))[0]

        if not cogs:
            await ctx.send(f'>>> {self.reload.help.format(prefix=prefix)}')
        
        if (len(cogs) == 1) and (cogs[0].lower() == 'all'):
            cogs = [cog for cog in self.bot.cogs]

        for cog in cogs:
            if (len(cogs) > 1) and (cog.lower() == 'config'):
                continue
            try:
                await self.bot.reload_extension(f'cogs.{cog.lower()}')
                await ctx.send(f'Reloaded cog: {cog.lower()}')
            except commands.ExtensionError as e:
                await ctx.send(f'Error reloading cog: {e}')
    
    @commands.command(
        name='command',
        brief='run custom command',
        hidden=True
    )
    @is_owner()
    async def runcommand(self, ctx):
        """
        Command: **command**

        Use this to write a one-use command on the backend and run it in discord.

        __Usage:__
        `{prefix}command`

        Permissions:
        is_owner
        """

        # insert 1 time use here
        # async with aiosqlite.connect(self.db) as db:
        #     async with db.cursor() as cursor:
        #         await cursor.execute("ALTER TABLE message DROP COLUMN embedColor")
        #     await db.commit()

        return

    @commands.command(
        name='invite',
        brief='create bot invite',
        hidden=True
    )
    async def invite_url(self, ctx):
        """
        Command: **invite**

        Create a bot invite with the configured permissions.

        __Usage:__
        `{prefix}invite`

        Permissions:
        is_owner
        """
        await ctx.author.send(configData['INVITE_URL'])

async def setup(bot):
    await bot.add_cog(Config(bot))