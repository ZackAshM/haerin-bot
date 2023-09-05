import discord
from discord.ext import commands
from discord.errors import Forbidden

import json
import aiosqlite

from utils.database import db_execute

"""This custom help command is a perfect replacement for the default one on any Discord Bot written in Discord.py!
However, you must put "bot.remove_command('help')" in your bot, and the command must be in a cog for it to work.

Original concept by Jared Newsom (AKA Jared M.F.)
[Deleted] https://gist.github.com/StudioMFTechnologies/ad41bfd32b2379ccffe90b0e34128b8b
Rewritten and optimized by github.com/nonchris
https://gist.github.com/nonchris/1c7060a14a9d94e7929aa2ef14c41bc2

You need to set three variables to make that cog run.
Have a look at line 51 to 57
"""

with open('config.json', 'r') as config_file:
    configData = json.load(config_file)

async def send_embed(ctx, embed):
    """
    Function that handles the sending of embeds
    -> Takes context and embed to send
    - tries to send embed in channel
    - tries to send normal message when that fails
    - tries to send embed private with information abot missing permissions
    If this all fails: https://youtu.be/dQw4w9WgXcQ
    """
    try:
        await ctx.send(embed=embed)
    except Forbidden:
        try:
            await ctx.send("Hey, seems like I can't send embeds. Please check my permissions :)")
        except Forbidden:
            await ctx.author.send(
                f"Hey, seems like I can't send any message in {ctx.channel.name} on {ctx.guild.name}\n"
                f"May you inform the server team about this issue? :slight_smile: ", embed=embed)

# command iteration to handle multiple levels of subcommands
async def get_command_help(commands, input, prefix):
    """
    Get help embed of the subcommand requested. Go through all levels
    of subcommands requested in input.
    """
    invalid = discord.Embed(title="Invalid command",
                            description=f"Invalid command. This could be that the command does not exist, or you do not have permissions for this command.",
                            color=discord.Color.yellow())
    # command iteration
    for command in commands:
        if command.name.lower() == input[1].lower():
            # command detected
            if not command.hidden:
                try: 
                    if len(input) > 2:
                        # subcommand was requested
                        emb = await get_command_help(command.commands, input[1:], prefix)
                        break
                    else:
                        # subcommand was not requested
                        emb = discord.Embed(
                            title=f'{prefix}{command}', 
                            description=f'{command.help.format(prefix=prefix)}',
                            color=discord.Color.dark_green())
                        break
                    
                except AttributeError as e:
                    # subcommand was requested, but there are no subcommands
                    emb = invalid
                    break
    else:
        # went through all commands and did not match input
        emb = invalid
    
    return emb
    
        


class Help(commands.Cog):
    """Sends this help message"""

    def __init__(self, bot):
        self.bot = bot
        self.db = configData["DATABASE"]

    @commands.command(
            name='help',
            aliases = ['h']
    )
    # @commands.bot_has_permissions(add_reactions=True,embed_links=True)
    async def help(self, ctx, *input):
        """
        Command: **[help | h]**

        Shows all modules. Give a module and/or commands to get more info on a specific one.

        __Usage:__
        `{prefix}help <module>`
        ↳ Get more info on a module
        `{prefix}help (<module>) <command> (<subcommand> <subcommand> ...)`
        ↳ Get more info on a specific command or subcommand in a module. In some cases, the module name is the same as the command. Then the module name is not needed.
        """
	
	# !SET THOSE VARIABLES TO MAKE THE COG FUNCTIONAL!
        guildPrefix = (await db_execute(self.db, 'SELECT prefix FROM config WHERE guildID = ?', ctx.guild.id))[0]
        prefix = guildPrefix
        version = configData['VERSION']
        owner = configData['AUTHOR']
        # owner_name = configData['USERNAME']

        # checks if owner is on this server - used to 'tag' owner
        try:
            owner = ctx.guild.get_member(int(owner)).mention
        except AttributeError as e:
            owner = owner

        # checks if cog parameter was given
        # if not: sending all modules and commands not associated with a cog
        invalid = False
        if not input:

            # starting to build embed
            emb = discord.Embed(
                title='Help', color=discord.Color.green(),
                description=f'Use `{prefix}help <module>` to gain more information about that module\n'+
                f'**{"-"*40}**'
                )

            # iterating trough cogs, gathering descriptions
            cogs_desc = ''
            for cog in sorted(self.bot.cogs):
                if cog == 'Config':
                    continue
                cogs_desc += f'`{cog.lower()}`\n↳{self.bot.cogs[cog].__doc__}\n\n'

            # Config treated special
            if ctx.author.id == int(configData['AUTHOR']):
                cogs_desc += f'**Config Options** (`config`)\n'
                config_cog = self.bot.cogs['Config']
                for command in config_cog.get_commands():
                    if not command.hidden:
                        cogs_desc += f'`{command.name}` - {command.brief}\n'

            # adding 'list' of cogs to embed
            emb.add_field(name='Modules', value=cogs_desc, inline=False)

            # iterating trough uncategorized commands
            commands_desc = ''
            for command in self.bot.walk_commands():
                # if cog not in a cog
                # listing command if cog name is None and command isn't hidden
                if not command.cog_name and not command.hidden:
                    commands_desc += f'{command.name} - {command.brief}\n'

            # adding those commands to embed
            if commands_desc:
                emb.add_field(name='Not belonging to a module', value=commands_desc, inline=False)

            # setting information about author
            # emb.add_field(name="About", value=f"Haerin Bot by {owner}")
            emb.set_footer(text=f"Haerin Bot v{version} by {owner}")
            emb.add_field(name='-'*40, value=f'** **', inline=False)
            emb.add_field(name='Symbols in Command Usage:', value=f'- `{prefix}` - bot prefix\n- `< X >` - Insert name of X (ex: `<server id>` = 1061792414165115000)\n- `( X )` - "`X`" is an optional parameter\n- `[ X | Y ]` - Choose between `X` or `Y`', inline=False)
            emb.add_field(name='** **', value=f'If you run into unexpected errors, send them to {owner}', inline=False)

        # block called when one cog-name is given
        # trying to find matching cog and it's commands
        elif len(input) == 1:

            # iterating trough cogs
            for cog in sorted(self.bot.cogs):

                # check if cog is the matching one
                if cog.lower() == input[0].lower():

                    # config only for author
                    if (cog.lower() == 'config') and (ctx.author.id != int(configData['AUTHOR'])):
                        continue

                    # check for single command cog
                    if len(self.bot.get_cog(cog).get_commands()) == 1:
                        single_command = self.bot.get_cog(cog).get_commands()[0]
                        if not single_command.hidden and single_command.name.lower() == cog.lower():
                            # Found a cog with only one visible command that has the same name as the cog
                            emb = discord.Embed(
                                title=f'{prefix}{single_command}',
                                description=f'{single_command.help.format(prefix=prefix)}',
                                color=discord.Color.dark_green()
                            )
                            emb.set_footer(text=f"Haerin Bot v{version} by {owner}")
                            # emb.add_field(name='-'*40, value=f'** **', inline=False)
                            # emb.add_field(name='** **', value=f'If you run into unexpected errors, send them to {owner}', inline=False)
                            break

                    # making title - getting description from doc-string below class
                    emb = discord.Embed(
                        title=f'{cog} - Commands', 
                        description=(
                            self.bot.cogs[cog].__doc__+
                            f'\nUse `{prefix}help {cog.lower()} <command>` for more information on a command.'+
                            f'\n**{"-"*40}**'),
                        color=discord.Color.dark_green()
                        )

                    # getting commands from cog
                    for command in self.bot.get_cog(cog).get_commands():
                        # if cog is not hidden
                        if not command.hidden:
                            field = f'>>> {command.help.format(prefix=prefix)}'
                            if len(field) >= 1024:
                                field = f'>>> For more information, use `{prefix}help {cog.lower()} {command.name}`'
                            emb.add_field(name=f"`{prefix}{command.name}`", value=field, inline=False)
                    # found cog - breaking loop
                    emb.set_footer(text=f"Haerin Bot v{version} by {owner}")
                    # emb.add_field(name='-'*40, value=f'** **', inline=False)
                    # emb.add_field(name='** **', value=f'If you run into unexpected errors, send them to {owner}', inline=False)
                    break

            # if input not found
            # yes, for-loops have an else statement, it's called when no 'break' was issued
            else:
                invalid = True
                emb = discord.Embed(title="Invalid module",
                                    description=f"Module `{input[0]}` invalid. This could be that the module does not exist, or you do not have permissions for this module.",
                                    color=discord.Color.yellow())

        # command
        elif len(input) > 1:

            # iterating trough cogs
            for cog in sorted(self.bot.cogs):

                # check if cog is the matching one
                if cog.lower() == input[0].lower():

                    commands = self.bot.get_cog(cog).get_commands()

                    # config only for author
                    if (cog.lower() == 'config') and (ctx.author.id != int(configData['AUTHOR'])):
                        continue

                    # check for single command cog
                    if len(self.bot.get_cog(cog).get_commands()) == 1:
                        single_command = self.bot.get_cog(cog).get_commands()[0]
                        if not single_command.hidden and single_command.name.lower() == cog.lower():
                            if single_command.name.lower() == input[1].lower():
                                # user used single command as a module, which works fine too
                                emb = discord.Embed(title=f'{prefix}{single_command}', 
                                                    description=f'{single_command.help.format(prefix=prefix)}',
                                                    color=discord.Color.dark_green())
                                emb.set_footer(text=f"Haerin Bot v{version} by {owner}")
                                # emb.add_field(name='-'*40, value=f'** **', inline=False)
                                # emb.add_field(name='** **', value=f'If you run into unexpected errors, send them to {owner}', inline=False)
                                break

                            # single command followed by subcommand(s)
                            try:
                                commands = single_command.commands
                            except AttributeError:
                                invalid = True
                                emb = discord.Embed(title="Invalid command",
                                                    description=f"Invalid command. This could be that the command does not exist, or you do not have permissions for this command.",
                                                    color=discord.Color.yellow())
                                break

                    emb = await get_command_help(commands, input, prefix)
                    emb.set_footer(text=f"Haerin Bot v{version} by {owner}")
                    # emb.add_field(name='-'*40, value=f'** **', inline=False)
                    # emb.add_field(name='** **', value=f'If you run into unexpected errors, send them to {owner}', inline=False)
                    break
            
            else:
                invalid = True
                emb = discord.Embed(title="Invalid module",
                                    description=f"Module `{input[0]}` invalid. This could be that the module does not exist, or you do not have permissions for this module.",
                                    color=discord.Color.yellow())

        else:
            emb = discord.Embed(title="How did you get here...",
                                description="I don't know how you got here. But I didn't see this coming at all.\n"
                                            "Would you please be so kind to report that issue to me on github?\n"
                                            "https://github.com/nonchris/discord-fury/issues\n"
                                            "Thank you! ~OG Help Module writer Chris",
                                color=discord.Color.red())

        # sending reply embed using our own function defined above
        delete_after = 10 if invalid else None
        await ctx.reply(embed=emb, delete_after=delete_after)


async def setup(bot):
    await bot.add_cog(Help(bot))
