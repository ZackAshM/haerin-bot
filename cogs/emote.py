import discord
from discord.ext import commands, tasks
import json
# import aiosqlite
from utils.database import db_execute
import requests
import asyncio
from io import BytesIO

with open('config.json', 'r') as config_file:
    configData = json.load(config_file)

class Emote(commands.Cog):
    """Commands related to emote shenanigans"""

    def __init__(self, bot):

        self.bot = bot
        self._timed_update.start()
        self.db = configData["DATABASE"]

    def is_bot(self, message):
        return message.author == self.bot.user
        
    @commands.group(
            name='emote',
            invoke_without_command=True
    )
    async def emote(self, ctx):
        """
        Module: **emote**

        Commands for emote shenanigans.

        __Usage:__
        - **Adding/Removing/Sourcing**
        `{prefix}emote add` - Adds emotes based on the linked or uploaded images
        `{prefix}emote remove` - Removes given emotes
        `{prefix}emote rename` - Rename an existng emote
        `{prefix}emote source` - Post the source images of the emotes given

        - **Emote Logging**
        `{prefix}emote log` - Set the channel and settings for logging emotes
    
        - **Emote Gallery Display**
        `{prefix}emote display` - Post display gallery of emotes in server, set channel for auto displaying

        - **Tutorial**
        `{prefix}emote tutorial` - Shows a guide for using Haerin Bot's emote commands

        For more information of a command, use `{prefix}help emote <command>`
        """
        await self._emote_help(ctx)
    

    async def _emote_help(self, ctx):
        """Give the help result for the emote module"""
        prefix = (await db_execute(self.db, 'SELECT prefix FROM config WHERE guildID=?', ctx.guild.id))[0]
        emb = discord.Embed(title=f'{prefix}emote',
                            description=f'{self.emote.help.format(prefix=prefix)}',
                            color=discord.Color.dark_green())
        await ctx.send(embed=emb)


    # -------------------------------------------------
    # -- ADDING/REMOVING/SOURCING ---------------------
    # -------------------------------------------------


    @emote.command(
            name='add',
            brief='Add emotes'
    )
    @commands.has_permissions(create_expressions=True)
    async def emote_add(self, ctx, *args):
        """
        Command: **emote add**
        
        Adds emotes based on the linked or uploaded images. Provide the names in order of upload. If no names are provided, naming defaults to the filenames.

        __Usage:__
        `{prefix}emote add (<emote name 1> <emote name 2> ...) <source link/upload 1> <source link/upload 2> ...`

        Source links must be 'http' links. Supported formats are PNG, JPG, and GIF.

        Permissions:
        create_expressions
        """

        # determine upload style
        all_sources = False
        if not args: # no names, all uploads
            all_sources = True
            sources = [source.url for source in ctx.message.attachments]
        elif ("http" in args[0]) and ("http" in args[-1]): # all links
            all_sources = True
            sources = args
        else: # names
            if "http" in args[-1]: # links and names
                if (len(args) % 2 == 1) or ("http" in args[0]): # odd or only sources
                    await ctx.send("Invalid input. There must be equal emote names to sources and sources must be all upload or all links.")
                    return
                splitInd = int(len(args)/2)
                emote_names = args[:splitInd]
                sources = args[splitInd:]
            else: # uploads and names
                emote_names = args
                sources = [source.url for source in ctx.message.attachments]
                if len(emote_names) != len(sources):
                    await ctx.send("Invalid input. There must be equal emote names to sources and sources must be all upload or all links.")
                    return

        emote_sources = []
        filenames = []
        for source in sources:
                filenames.append(source.split('/')[-1].split('.')[0])
                response = requests.get(source)
                emote_sources.append(response.content)
        
        if all_sources:
            emote_names = filenames

        # truncate emote names
        emote_names = [name[:32] for name in emote_names]

        successAdd = []
        successSources = []
        failAdd = []
        for name, source in zip(emote_names, emote_sources):
            try:
                # Create the emote in the guild
                emote = await ctx.guild.create_custom_emoji(name=name, image=source)
                successAdd.append(str(emote))
                successSources.append((name, source, emote.animated))
            except Exception as e:
                failAdd.append((name, e))
                pass

        if successAdd:
            await ctx.send(f"Emotes added successfully:")
            await ctx.send(' '.join(successAdd))

        if failAdd:
            await ctx.send(f"Failed to add:")
            for name, e in failAdd:
                await ctx.send(f"{name}: {e}")

        srcChID = (await db_execute(self.db, 'SELECT sourceChannelID FROM emotelog WHERE guildID=?', ctx.guild.id))[0]
        if srcChID:
            srcCh = discord.utils.get(ctx.guild.channels, id=int(srcChID))
            for name, source, ani in successSources:
                fileExt = '.gif' if ani else '.png'
                file = discord.File(BytesIO(source), filename=name+fileExt)
                await srcCh.send(content=f'`:{name}:`', file=file)

    @emote.command(
            name='remove',
            brief='remove emotes'
    )
    @commands.has_permissions(manage_expressions=True)
    async def emote_remove(self, ctx, *emotes):
        """
        Command **emote remove**

        Removes the emote(s) given. If emote logging is enabled, a post is made to log the removal. 
        Use "nolog" in this case to not update the log.
        You can provide a custom header before the emotes that will replace "Removed:" (usually to reflect reasons for removal, like "Tranferred to <server>:").

        __Usage:__
        `{prefix}emote remove (nolog) (<custom header>) <:emote1:> <:emote2:> ...`
        
        The emotes must be spaced apart evenly by either 0 or 1 spaces.

        Permissions:
        manage_expressions
        """

        prefix = (await db_execute(self.db, 'SELECT prefix FROM config WHERE guildID = ?', ctx.guild.id))[0]
        log = True # default

        if emotes[0].lower() == 'nolog':
            log = False
            emotes = emotes[1:]
        
        customMsg = ''
        if emotes[0].lower()[0] != '<':
            emoteStartInd = 0
            for word in emotes:
                if word.lower()[0] == '<':
                    break
                emoteStartInd += 1
            else:
                raise ValueError('Invalid input.')
                return
            customMsg = ' '.join(emotes[:emoteStartInd])
            emotes = emotes[emoteStartInd:]

        # check if emotes were not spaced
        re_arg = ''
        for emote in emotes:
            re_arg += ' ' + str(emote).replace('><', '> <')
        try:
            emoteIDs = [int(name.split(':')[-1][:-1]) for name in re_arg.split(' ')[1:]]
        except:
            await ctx.send(f'Invalid input. Use `{prefix}help emote remove` for more information')
            return
        emotes = [ctx.guild.get_emoji(id) for id in emoteIDs]

        # get log channel
        if log:
            emoteLogChID = (await db_execute(self.db, 'SELECT logChannelID FROM emotelog WHERE guildID=?', ctx.guild.id))[0]
            if emoteLogChID:
                emoteLogCh = discord.utils.get(ctx.guild.channels, id=int(emoteLogChID))
            at_least_one_removed = False

        # remove emotes
        successRemove = []
        failRemove = []
        for emote, id in zip(emotes, emoteIDs):
            try:
                if emote in ctx.guild.emojis:
                    emote_name = emote.name
                    if log:
                        if not at_least_one_removed:
                            if emoteLogChID:
                                updateMsg = f'**{customMsg}**' if customMsg else '**Removed:**'
                                await emoteLogCh.send(updateMsg)
                            at_least_one_removed = True
                        if emoteLogChID:
                            await emoteLogCh.send(emote)
                    await emote.delete()
                    successRemove.append(f'`:{emote_name}:`')
                else:
                    try:
                        emt = discord.utils.get(self.bot.emojis, id=id)
                        emote_name = emt.name
                    except:
                        emote_name = id
                    failRemove.append((f'`:{emote_name}:`', 'This emote is not in this server'))
            except Exception as e:
                failRemove.append((f'`:{id}:`', e))

        if successRemove:
            await ctx.send(f"Successfully removed emotes: {', '.join(successRemove)}")
        
        if failRemove:
            await ctx.send(f"Failed to remove emotes:")
            for name, e in failRemove:
                await ctx.send(f"{name}: {e}")


    @emote.command(
            name='rename',
            brief='rename an existing emote'
    )
    @commands.has_permissions(manage_expressions=True)
    async def emote_rename(self, ctx, emote : discord.Emoji, newName : str = ''):
        """
        Command: **emote rename**

        Rename an existing emote.

        __Usage:__
        `{prefix}emote rename <:emote:> <new name>`

        Permissions:
        manage_expressions
        """

        if len(newName) < 2:
            raise ValueError('A new name must be given with at least 2 characters length.')
        
        oldName = emote.name
        await emote.edit(name=newName)

        await ctx.send(f'Emote `{oldName}` successfully renamed to `{newName}`')


    @emote.command(
        name='source',
        brief='return emote source'
    )
    async def emote_source(self, ctx, *emotes: discord.PartialEmoji):
        """
        Command: **emote source**

        Posts the source images of the emotes.

        __Usage:__
        `{prefix}emote source <:emote1:> <:emote2:> ...`
        
        The emotes must be spaced apart evenly by 1 space. Only gives sources for the first 10 emotes.

        Permissions:
        None
        """
        emote_files = []
        for emote in emotes:
            if isinstance(emote, discord.PartialEmoji):
                emote_file = await emote.to_file()
            emote_files.append(emote_file)
            if len(emote_files) >= 10:
                break

        await ctx.send(files=emote_files)


    # -------------------------------------------------
    # -- LOGGING --------------------------------------
    # -------------------------------------------------


    @emote.group(
            name='log',
            invoke_without_command=True
    )
    @commands.has_permissions(manage_expressions=True, create_expressions=True, manage_channels=True)
    async def emotelog(self, ctx, channel=''):
        """
        Command: **emote log**

        Log emote updates automatically into a channel. Updates are provided every 30 mins, or manually using the update command.

        __Usage:__
        `{prefix}emote log <#channel>`
        ↳ Set the channel for which emote log updates are posted
        `{prefix}emote log autopublish [on | off]`
        ↳ Enable or disable autopublishing
        `{prefix}emote log source`
        ↳ Set a channel to log emote sources when `{prefix}emote add` is used
        `{prefix}emote log update`
        ↳ Immediately post the current emote log update
        `{prefix}emote log check`
        ↳ See the awaiting update
        `{prefix}emote log disable`
        ↳ Disable posting emote log updates
        `{prefix}emote log clear`
        ↳ Clear the awaiting emote log

        Permissions:
        manage_expressions
        create_expressions
        manage_channels
        """

        prefix = (await db_execute(self.db, 'SELECT prefix FROM config WHERE guildID = ?', ctx.guild.id))[0]

        # handle empty string
        if channel == '':
            # get log channel
            currentLogChannelID =(await db_execute(self.db, 'SELECT logChannelID FROM emotelog WHERE guildID=?', ctx.guild.id))[0]
            if currentLogChannelID:
                currentLogChannel = discord.utils.get(ctx.guild.channels, id=int(currentLogChannelID))
                await ctx.send(f"Emote log channel is currently set to {currentLogChannel.mention}")
            else:
                await ctx.send(f"No channel is set for emote logging. Use `{prefix}emote log <#channel>` to select a channel and enable emote logging")
            return

        # check if input is a channel
        channelID = channel[2:-1]
        try:
            newLogChannel = discord.utils.get(ctx.guild.channels, id=int(channelID))
        except ValueError:
            await ctx.send(f"Invalid channel. Use `{prefix}emote log <#channel>` to select a channel to enable emote logging")
            return

        # if a channel, set it
        if newLogChannel:
            await db_execute(self.db, 'UPDATE emotelog SET logChannelID=? WHERE guildID=?', channelID, ctx.guild.id, exec_type='update')
            await ctx.send(f"Emote log updates will now post to {newLogChannel.mention}")
        else:
            await ctx.send(f"Invalid channel. Use `{prefix}emote log <#channel>` to select a channel to enable emote logging")

    
    @emotelog.command(
            name='autopublish',
            brief='sets auto publishing'
    )
    @commands.has_permissions(manage_expressions=True, create_expressions=True, manage_channels=True, manage_webhooks=True)
    async def emotelog_autopublish(self, ctx, option=''):
        """
        Command: **emote log autopublish**

        Enable or disable autopublishing if emote log is a news/announcements channel.

        __Usage:__
        `{prefix}emote log autopublish [on | off]`

        Permissions:
        manage_expressions
        create_expressions
        manage_channels
        manage_webhooks
        """

        prefix = (await db_execute(self.db, 'SELECT prefix FROM config WHERE guildID=?', ctx.guild.id))[0]

        if option.lower() == 'on':
            desiredStatus = 1
        elif option.lower() == 'off':
            desiredStatus = 0
        else:
            desiredStatus = ''
        currentStatus = (await db_execute(self.db, 'SELECT autopublish FROM emotelog WHERE guildID=?', ctx.guild.id))[0]

        # handle invalid argument
        if (option == '') or (desiredStatus == ''):
            emb = discord.Embed(title=f'{prefix}emote log autopublish',
                                description=f'{self.emotelog_autopublish.help.format(prefix=prefix)}',
                                color=discord.Color.dark_green())
            await ctx.send(embed=emb)
            return
        
        statusStr = 'on' if desiredStatus else 'off'

        if desiredStatus == currentStatus:
            await ctx.send(f'Autopublish is already set to {statusStr}')
            return
        else:
            await db_execute(self.db, "UPDATE emotelog SET autopublish=? WHERE guildID=?", desiredStatus, ctx.guild.id, exec_type='update')
        
        await ctx.send(f'Autopublish is now set to {statusStr}')


    @emotelog.command(
            name='source',
            brief='set a source logging channel'
    )
    @commands.has_permissions(manage_expressions=True, create_expressions=True, manage_channels=True)
    async def emotelog_source(self, ctx, channel=''):
        """
        Command: **emote log source**

        Set a channel to log emote sources when `{prefix}emote add` is used. Use 'disable' to disble source logging.

        __Usage:__
        `{prefix}emote log source [ <#channel> | disable ]`

        Permissions:
        manage_expressions
        create_expressions
        manage_channels
        """
        prefix = (await db_execute(self.db, 'SELECT prefix FROM config WHERE guildID = ?', ctx.guild.id))[0]
        currentSourceChannelID = (await db_execute(self.db, 'SELECT sourceChannelID FROM emotelog WHERE guildID=?',ctx.guild.id))[0]
        
        # handle empty
        if channel == '':
            if currentSourceChannelID:
                try:
                    srcCh = discord.utils.get(ctx.guild.channels, id=int(currentSourceChannelID))
                    if srcCh:
                        await ctx.send(f"Source logging channel is currently set to {srcCh.mention}")
                        return
                except:
                    pass
            await ctx.send(f"Source logging is currently disabled")
            return
        
        if channel.lower() == 'disable':
            await db_execute(self.db, 'UPDATE emotelog SET sourceChannelID=? WHERE guildID=?', 0, ctx.guild.id, exec_type='update')
            await ctx.send('Source logging is now disabled')
            return
        
        # check valid channel
        channelID = channel[2:-1]
        try:
            srcCh = discord.utils.get(ctx.guild.channels, id=int(channelID))
            if srcCh is None:
                raise ValueError
        except:
            raise ValueError('Invalid channel.')
            return
        
        # set channel
        await db_execute(self.db, 'UPDATE emotelog SET sourceChannelID=? WHERE guildID=?', srcCh.id, ctx.guild.id, exec_type='update')
        await ctx.send(f'Source logging is now set to {srcCh.mention}. Emote sources will be logged there whenever `{prefix}emote add` is used.')


    @emotelog.command(
            name='update',
            brief='update the emote log'
    )
    @commands.has_permissions(manage_expressions=True, create_expressions=True, manage_messages=True)
    async def emotelog_update(self, ctx, *, custom_header=None):
        """
        Command: **emote log update**

        Post the update to the emote log immediately, if any updates have been made in the past half hour.
        Provide a custom header to replace "Added:" (usually to reflect more info, for instance "Added (cr:@user):"). However note that this header will be used for all emotes in the current update batch.
        If you would like to provide a custom header for only certain additions, invoke `{prefix}emote log update` first, then make the emote additions and use this command with the custom header.

        __Usage:__
        `{prefix}emote log update (<custom header>)`

        Permissions:
        manage_expressions
        create_expressions
        manage_messages
        """

        prefix = (await db_execute(self.db, 'SELECT prefix FROM config WHERE guildID = ?', ctx.guild.id))[0]

        logChID, updateMsg, updateMsgSt = await db_execute(self.db, 'SELECT logChannelID, updateMessage, updateMessageStickers FROM emotelog WHERE guildID=?', ctx.guild.id)
        logChannel = discord.utils.get(ctx.guild.channels, id=int(logChID))

        if logChID:
            if updateMsg or updateMsgSt:
                hdr = custom_header if custom_header else ''
                await self._send_update(ctx.guild.id, header=hdr)
                await ctx.send(f"Emote log has been updated in {logChannel.mention}")
            else:
                await ctx.send("There are currently no emote updates")
        else:
            await ctx.send(f"A channel to log emotes must be set. Use `{prefix}emote log <#channel>` to do so")


    @emotelog.command(
            name='check',
            brief='see awaiting update'
    )
    @commands.has_permissions(manage_expressions=True, create_expressions=True, manage_messages=True)
    async def emotelog_check(self, ctx):
        """
        Command: **emote log check**

        See the current awaiting log update. Posts in this channel.

        __Usage:__
        `{prefix}emote log check`

        Permissions:
        manage_expressions
        create_expressions
        manage_messages
        """

        updateMsg, updateMsgStick = await db_execute(self.db, 'SELECT updateMessage, updateMessageStickers FROM emotelog WHERE guildID=?', ctx.guild.id)

        if (updateMsg == '') and (updateMsgStick == ''):
            await ctx.send('There is currently no awaiting log update')
            return
        
        if updateMsg:
            hdr = f'**Added:**'
            await ctx.send(hdr)
            await ctx.send(updateMsg)

        # handle stickers
        if updateMsgStick:
            stickers = []
            stickerCount = 0
            for stickerID in updateMsgStick.split(' '):
                sticker = self.bot.get_sticker(int(stickerID))
                stickers.append(sticker)
                stickerCount += 1
                if stickerCount >= 3:
                    await ctx.send(stickers=stickers)
                    stickers = []
                    stickerCount = 0
            if stickers:
                await ctx.send(stickers=stickers)


    @emotelog.command(
        name='disable',
        brief='disable emote logging'
    )
    @commands.has_permissions(manage_expressions=True, create_expressions=True, manage_channels=True, manage_messages=True)
    async def emotelog_disable(self, ctx):
        """
        Command: **emote log disable**

        Disable logging emotes.

        __Usage:__
        `{prefix}emote log disable

        Permissions:
        manage_expressions
        create_expressions
        manage_channels
        manage_messages
        """

        prefix = (await db_execute(self.db, 'SELECT prefix FROM config WHERE guildID = ?', ctx.guild.id))[0]

        logChID = (await db_execute(self.db, 'SELECT logChannelID FROM emotelog WHERE guildID=?', ctx.guild.id))[0]
        if logChID:
            await db_execute(self.db, 'UPDATE emotelog SET logChannelID=? WHERE guildID=?', 0, ctx.guild.id, exec_type='update')
            await ctx.send(f"Emote logging has been disabled. To re-enable, use `{prefix}emote log <#channel>`")
        else:
            await ctx.send("Emote logging is already disabled")


    @emotelog.command(
        name='clear',
        brief='clear the awaiting log update'
    )
    @commands.has_permissions(manage_expressions=True, create_expressions=True, manage_channels=True, manage_messages=True)
    async def emotelog_clear(self, ctx):
        """
        Command: **emote log clear**

        Clear the awaiting log update.

        __Usage:__
        `{prefix}emote log clear

        Permissions:
        manage_expressions
        create_expressions
        manage_channels
        manage_messages
        """

        await self._reset(ctx.guild.id)
        await ctx.send('The update log has been cleared')


    async def _reset(self, guild_id):
        """Resets message data"""
        await db_execute(self.db, 'UPDATE emotelog SET updateMessage=?, updateMessageStickers=?, messageColumnCount=?, messageRowCount=? WHERE guildID=?', "", "", 0, 0, guild_id, exec_type='update')
            
    
    async def _send_update(self, guild_id, header=''):
        """Update the emote log"""

        logChID, updateMsg, updateMsgStick, autopublish = await db_execute(self.db, 'SELECT logChannelID, updateMessage, updateMessageStickers, autopublish FROM emotelog WHERE guildID=?', guild_id)

        if logChID:
            guild = self.bot.get_guild(guild_id)
            channel = discord.utils.get(guild.channels, id=logChID)
            hdr = f'**{header}**' if header else '**Added:**'
            msg1 = await channel.send(hdr)
            if updateMsg:
                msg2 = await channel.send(updateMsg)
                if (autopublish) and (channel.type == discord.ChannelType.news):
                    await msg1.publish()
                    await asyncio.sleep(5)
                    await msg2.publish()

            # handle stickers
            if updateMsgStick:
                stickers = []
                stickerCount = 0
                for stickerID in updateMsgStick.split(' '):
                    sticker = self.bot.get_sticker(int(stickerID))
                    stickers.append(sticker)
                    stickerCount += 1
                    if stickerCount >= 3:
                        await channel.send(stickers=stickers)
                        stickers = []
                        stickerCount = 0
                if stickers:
                    await channel.send(stickers=stickers)

            await self._reset(guild_id)


    # -------------------------------------------------
    # -- DISPLAY --------------------------------------
    # -------------------------------------------------


    @emote.group(
            name='display',
            invoke_without_command=True
    )
    async def emotedisplay(self, ctx, *args):
        """
        Command: **emote display**

        Post a set of messages that display a gallery of this server's emotes, or of another server if given.
        Haerin Bot must be in the server! Currently, discord does not allow stickers to be sent via bot outside of their server.
        
        __Usage:__
        `{prefix}emote display (<server ID>) [(static) (animated) (sticker) | (all)]`
        ↳ Post a display gallery of the emotes in this server, or a given server. Default displays static and animated only. Sent via DM if user does not have manage_expressions permission.
        Select which emote types are displayed by providing their name, or 'all' to display all types.
        `{prefix}emote display channel <#channel>`
        ↳ Set a channel for which the emote display is created and updated when emotes are added/removed. Does not display stickers.
        `{prefix}emote display disable`
        ↳ Delete the display in the display channel and cease display updates.
        `{prefix}emote display [col | row] <number>`
        ↳ Set the display max columns and rows per message. Note: Setting a total of more than 30 emotes per message may shrink the emotes.
        """
        
        await self._emotedisplay(ctx, *args)


    async def _emotedisplay(self, ctx, *args):
        """Produces a gallery for the emotes in this server"""

        prefix = (await db_execute(self.db, 'SELECT prefix FROM config WHERE guildID = ?', ctx.guild.id))[0]

        emoteBools = {'static':True, 'animated':True, 'sticker':False, 'stickers':False} # redundancy on "sticker(s)"
        emoteSelection = ['static', 'animated', 'sticker', 'stickers', 'all']

        # if we have input, change the default
        if args:

            # if first arg is a guild, get it
            try:
                guild = self.bot.get_guild(int(args[0]))
                if guild is None:
                    # args[0] was an int, but did not correspond to a guild with the bot
                    raise ValueError(f'Haerin Bot is not in server with server ID "{args[0].lower()}"')
                    return
                # if there's more inputs, continue, but ignore the guild input
                if len(args) > 1:
                    selectionArgs = args[1:]
                else:
                    selectionArgs = None
            except ValueError:
                # args[0] was not an int
                if args[0].lower() in emoteSelection:
                    # if it's an emote type, then continue
                    guild = ctx.guild
                    selectionArgs = args
                    pass
                else:
                    # args[0] is not an int for a guild, nor an emote type
                    await ctx.send(f'Invalid input. Use `{prefix}emote display (<server id>) [(static) (animated) (sticker) | (all)]`')
                    return
            
            # parse through selection args
            if selectionArgs:
                # selecting a subset, so first set all false
                for emoteBool in emoteBools:
                    emoteBools[emoteBool] = False
                
                # now set each selection true
                for arg in selectionArgs:
                    if arg.lower() in emoteSelection:
                        if arg.lower() == 'all':
                            # set all true and move on
                            for emoteBool in emoteBools:
                                emoteBools[emoteBool] = True
                            break
                        else:
                            # set individual selection true
                            emoteBools[arg.lower()] = True
                    else:
                        # arg was not a valid emote type
                        raise ValueError(f'Did not understand emote type input "{arg}". Use `{prefix}emote display (<server id>) [(static) (animated) (sticker) | (all)]`')
                        return
        else:
            guild = ctx.guild

        # now post selected emotes
        emotes = []
        aemotes = []
        stickers = []
        for emoji in guild.emojis:
            if emoji.animated:
                aemotes.append("<a:{0}:{1}>".format(emoji.name, emoji.id))
            else:
                emotes.append("<:{0}:{1}>".format(emoji.name, emoji.id))
        for sticker in guild.stickers:
            stickers.append(sticker)

        # confirm continue in case of many emotes
        if (ctx.invoked_with == 'channel') or (ctx.invoked_with == 'autoupdate'):
            pass
        else:
            totEmotes = 0
            if emoteBools['static']:
                totEmotes += len(emotes)
            if emoteBools['animated']:
                totEmotes += len(aemotes)
            if (emoteBools['sticker']) or (emoteBools['stickers']):
                totEmotes += len(stickers)
            if totEmotes > 100:
                confirmation_message = await ctx.reply(f"There are {totEmotes} emotes/stickers to display. Continue?", delete_after=65)
                await confirmation_message.add_reaction('<a:ahaerinnodders:1147403485722193920>')
                await confirmation_message.add_reaction('<a:ahaerinnopers:1147403691977080845>')
                def check(reaction, user):
                    return user == ctx.author and str(reaction.emoji) in ['<a:ahaerinnodders:1147403485722193920>', '<a:ahaerinnopers:1147403691977080845>']
                try:
                    reaction, user = await self.bot.wait_for("reaction_add", timeout=60, check=check)
                    if str(reaction.emoji) == '<a:ahaerinnodders:1147403485722193920>':
                        await confirmation_message.delete()
                    elif str(reaction.emoji) == '<a:ahaerinnopers:1147403691977080845>':
                        await confirmation_message.delete()
                        await ctx.reply('Display was cancelled', delete_after=10)
                        return
                except asyncio.TimeoutError:
                    return
        
        # formatting control
        maxCol, maxRow = await db_execute(self.db, 'SELECT maxCol, maxRow FROM emotedisplay WHERE guildID = ?', ctx.guild.id)
        column_counter = 0
        row_counter = 0
        this_message = ""
        totalMessageCount = 0

        async def checked_send(ctx, message=None, stickers=None):
            if ctx.author.guild_permissions.manage_expressions:
                if message:
                    await ctx.send(message)
                elif stickers:
                    await ctx.send(stickers=stickers)
            else:
                if message:
                    await ctx.author.send(message)
                elif stickers:
                    await ctx.author.send('Discord has not allowed bots to send stickers outside of the server yet...', delete_after=20)

        # display static emotes
        if emoteBools['static']:
            for emoji in emotes:
                
                this_message += emoji
                column_counter += 1
                
                if column_counter >= maxCol:
                    column_counter = 0
                    row_counter += 1
                    this_message += '\n'
                
                if row_counter >= maxRow:
                    row_counter = 0
                    await checked_send(ctx, this_message)
                    totalMessageCount += 1
                    this_message = ""

            await checked_send(ctx, this_message)
            column_counter = 0
            row_counter = 0
            this_message = ""
            totalMessageCount += 1

        # display animated emotes
        if emoteBools['animated']:
            if emoteBools['static']:
                await checked_send(ctx, "<:blank:1144405351333113886>")
                totalMessageCount += 1
            for emoji in aemotes:
                
                this_message += emoji
                column_counter += 1

                if column_counter >= maxCol:
                    column_counter = 0
                    row_counter += 1
                    this_message += '\n'
                
                if row_counter >= maxRow:
                    row_counter = 0
                    await checked_send(ctx, this_message)
                    totalMessageCount += 1
                    this_message = ""

            await checked_send(ctx, this_message)
            totalMessageCount += 1
            this_message = ""

        # display stickers
        if emoteBools['sticker'] or emoteBools['stickers']:
            if guild.id != ctx.guild.id:
                await ctx.reply('Discord has not allowed bots to send external stickers yet...', delete_after=20)
            else:
                if (emoteBools['static']) or (emoteBools['animated']):
                    await checked_send(ctx, "<:blank:1144405351333113886>")
                stickerPost = []
                stickerCount = 0
                stickerLimit = 3
                for sticker in stickers:
                    stickerPost.append(sticker)
                    stickerCount += 1
                    if stickerCount >= stickerLimit:
                        await checked_send(ctx, stickers=stickerPost)
                        if not ctx.author.guild_permissions.manage_expressions:
                            return
                        stickerPost = []
                        stickerCount = 0
                if stickerPost:
                    await checked_send(ctx, stickers=stickerPost)
        
        # update count for display channel
        if (ctx.invoked_with == 'channel') or (ctx.invoked_with == 'autoupdate'):
            await db_execute(self.db, 'UPDATE emotedisplay SET messageCount=? WHERE guildID=?', totalMessageCount, ctx.guild.id, exec_type='update')

    
    @emotedisplay.command(
        name='channel'
    )
    @commands.has_permissions(manage_expressions=True, create_expressions=True, manage_channels=True, manage_messages=True)
    async def emotedisplay_channel(self, ctx, channel=''):
        """
        Command: **emote display channel**

        Set a channel for which the emote display is created and updated when emotes are added/removed. Does not display stickers.
        Updating will work best if the display is the only content in the channel.

        __Usage:__
        `{prefix}emote display <#channel>`

        Permissions:
        manage_expressions
        create_expressions
        manage_channels
        manage_messages
        """
        prefix = (await db_execute(self.db, 'SELECT prefix FROM config WHERE guildID = ?', ctx.guild.id))[0]
        currentDisplayChannelID = (await db_execute(self.db, 'SELECT displayChannelID FROM emotedisplay WHERE guildID=?',ctx.guild.id))[0]
        
        # handle empty
        if channel == '':
            if currentDisplayChannelID:
                try:
                    disCh = discord.utils.get(ctx.guild.channels, id=int(currentDisplayChannelID))
                    if disCh:
                        await ctx.send(f"Display channel is currently enabled at {disCh.mention}")
                        return
                except:
                    pass
            await ctx.send(f"Display channel is currently disabled")
            return
        
        # check valid channel
        channelID = channel[2:-1]
        try:
            disCh = discord.utils.get(ctx.guild.channels, id=int(channelID))
            if disCh is None:
                raise ValueError
        except:
            raise ValueError('Invalid channel.')
            return
        
        # set channel
        await db_execute(self.db, 'UPDATE emotedisplay SET displayChannelID=? WHERE guildID=?', disCh.id, ctx.guild.id, exec_type='update')

        # display
        new_ctx = await self.bot.get_context(ctx.message, cls=commands.Context)
        new_ctx.channel = disCh
        new_ctx.invoked_with = 'channel'
        await new_ctx.invoke(self.emotedisplay)

        await ctx.send(f'Emote display and auto updates are now enabled in {disCh.mention}')


    @emotedisplay.command(
            name='disable'
    )
    @commands.has_permissions(manage_expressions=True, create_expressions=True, manage_channels=True, manage_messages=True)
    async def emotedisplay_disable(self, ctx):
        """
        Command: **emote display disable**

        Disable updates to display in given display channel.

        __Usage:__
        `{prefix}emote display disable`

        Permissions:
        manage_expressions
        create_expressions
        manage_channels
        manage_messages
        """

        currentDisChID, msgCount = await db_execute(self.db, 'SELECT displayChannelID, messageCount FROM emotedisplay WHERE guildID=?', ctx.guild.id)

        if currentDisChID:
            disCh = discord.utils.get(ctx.guild.channels, id=int(currentDisChID))
            await disCh.purge(limit=msgCount, check=self.is_bot)
            await db_execute(self.db, 'UPDATE emotedisplay SET displayChannelID=? WHERE guildID=?', 0, ctx.guild.id, exec_type='update')
            await ctx.send(f'Emote display updating is now disabled, the gallery has been removed in {disCh.mention}')
        else:
            await ctx.send('Emote display updating is already disabled')

    
    @emotedisplay.command(
            name='row'
    )
    @commands.has_permissions(manage_expressions=True, create_expressions=True, manage_channels=True, manage_messages=True)
    async def emotedisplay_row(self, ctx, number : int):
        """
        Command: **emote display row**

        Set the display max rows per message. Note: Setting a total of more than 30 emotes per message (row * column) may shrink the emotes.

        __Usage:__
        `{prefix}emote display row <number>`

        Permissions:
        manage_expressions
        create_expressions
        manage_channels
        manage_messages
        """
        await db_execute(self.db, 'UPDATE emotedisplay SET maxRow=? WHERE guildID=?', number, ctx.guild.id, exec_type='update')
        await ctx.send(f'The max rows for emote displaying is now set to {number}')


    @emotedisplay.command(
            name='col'
    )
    @commands.has_permissions(manage_expressions=True, create_expressions=True, manage_channels=True, manage_messages=True)
    async def emotedisplay_col(self, ctx, number : int):
        """
        Command: **emote display col**

        Set the display max columns per message. Note: Setting a total of more than 30 emotes per message (row * column) may shrink the emotes.

        __Usage:__
        `{prefix}emote display col <number>`

        Permissions:
        manage_expressions
        create_expressions
        manage_channels
        manage_messages
        """
        await db_execute(self.db, 'UPDATE emotedisplay SET maxCol=? WHERE guildID=?', number, ctx.guild.id, exec_type='update')
        await ctx.send(f'The max columns for emote displaying is now set to {number}')
    
    async def _display_update(self, guild):
        """Update the display"""

        await asyncio.sleep(5)
        disChID, msgCount = await db_execute(self.db, 'SELECT displayChannelID, messageCount FROM emotedisplay WHERE guildID=?', guild.id)

        if disChID:
            disCh = discord.utils.get(guild.channels, id=int(disChID))
            
            async for msg in disCh.history(limit=100):
                if msg.author == self.bot.user:
                    lastMsg = msg
                    break
            else:
                return
            
            new_ctx = await self.bot.get_context(lastMsg, cls=commands.Context)
            await disCh.purge(limit=msgCount, check=self.is_bot)

            new_ctx.channel = disCh
            new_ctx.invoked_with = 'autoupdate'
            await new_ctx.invoke(self.emotedisplay)


    # -------------------------------------------------
    # -- UPDATE EVENTS --------------------------------
    # -------------------------------------------------


    @commands.Cog.listener()
    async def on_guild_emojis_update(self, guild, before, after):
        """Records added emotes for the emote log"""

        updateMsg, msgCol, msgRow, maxCol, maxRow = await db_execute(self.db, 'SELECT updateMessage, messageColumnCount, messageRowCount, maxCol, maxRow FROM emotelog WHERE guildID=?', guild.id)

        # handle added emote
        added = len(after) > len(before)
        removed = len(after) < len(before)
        if added:
            added_emote = after[-1]
            newMsg = str(updateMsg) + str(added_emote)
            newCol = msgCol + 1

            await db_execute(self.db, 'UPDATE emotelog SET updateMessage=?, messageColumnCount=? WHERE guildID=?', newMsg, newCol, guild.id, exec_type='update')

            # formatting of emote log display
            if newCol >= maxCol:
                newMsg += "\n"
                newCol = 0
                newRow = msgRow + 1
                await db_execute(self.db, 'UPDATE emotelog SET updateMessage=?, messageColumnCount=?, messageRowCount=? WHERE guildID=?', newMsg, newCol, newRow, guild.id, exec_type='update')

                # if reached emote display limit, update now
                if newRow >= maxRow:
                    newRow = 0
                    await db_execute(self.db, 'UPDATE emotelog SET messageRowCount=? WHERE guildID=?', newRow, guild.id, exec_type='update')
                    await self._send_update(guild.id)
    
        # if emote is removed, take it out of the update message
        elif removed:
            beforeSet = set(before)
            afterSet = set(after)
            removed_emote = list(beforeSet - afterSet)[0]
            newMsg = str(updateMsg).replace(str(removed_emote),'')
            if newMsg == updateMsg: # removed emote was not in log
                return
            else: # remove the emote from the log update message
                if msgCol == 0:
                    if msgRow == 0:
                        newRow = msgRow
                        newCol = msgCol
                    else:
                        newRow = msgRow - 1
                        newCol = maxCol - 1
                else:
                    if msgRow == 0:
                        newRow = msgRow
                        newCol = msgCol - 1
                    else:
                        newRow = msgRow
                        newCol = msgCol - 1
                await db_execute(self.db, 'UPDATE emotelog SET updateMessage=?, messageColumnCount=?, messageRowCount=? WHERE guildID=?', newMsg, newCol, newRow, guild.id, exec_type='update')

        # emote display
        await self._display_update(guild)


    @commands.Cog.listener()
    async def on_guild_stickers_update(self, guild, before, after):
        """Add/remove stickers to log update"""

        updateMsgSt = (await db_execute(self.db, 'SELECT updateMessageStickers FROM emotelog WHERE guildID=?', guild.id))[0]

        # handle added sticker
        added = len(after) > len(before)
        removed = len(after) < len(before)
        if added:
            added_sticker = after[-1]
            stickerID = added_sticker.id
            updateList = str(updateMsgSt) + ' ' + str(stickerID) if updateMsgSt else str(stickerID)
            await db_execute(self.db, 'UPDATE emotelog SET updateMessageStickers=? WHERE guildID=?', updateList, guild.id, exec_type='update')
        
        # if sticker is removed, take it out of the update message
        elif removed:
            beforeSet = set([sticker.id for sticker in before])
            afterSet = set([sticker.id for sticker in after])
            removed_sticker = list(beforeSet - afterSet)[0]
            newUpdateList = str(updateMsgSt).replace(str(removed_sticker),'').replace('  ', ' ')
            await db_execute(self.db, 'UPDATE emotelog SET updateMessageStickers=? WHERE guildID=?', newUpdateList, guild.id, exec_type='update')


    # timed log update posts
    @tasks.loop(minutes=30)
    async def _timed_update(self):
        """Update log every 30mins max"""
        guildIDs = (await db_execute(self.db, 'SELECT guildID FROM emotelog WHERE updateMessage != ?',"", fetch='all'))
        for guild_id in guildIDs:
            await self._send_update(guild_id[0])


    # -------------------------------------------------
    # -- TUTORIAL -------------------------------------
    # -------------------------------------------------

    @emote.command(
        name='tutorial',
        brief='Show emote command guide'
    )
    async def emote_tutorial(self, ctx):
        """
        Command: **emote tutorial**

        Show a guide for using Haerin Bot's emote commands.

        __Usage:__
        `{prefix}emote tutorial`
        """

        # ends other instances
        not_timed_out = False

        prefix = (await db_execute(self.db, 'SELECT prefix FROM config WHERE guildID = ?', ctx.guild.id))[0]
        version = configData['VERSION']
        owner = configData['AUTHOR']
        try:
            owner = ctx.guild.get_member(int(owner)).mention
        except AttributeError as e:
            owner = owner

        emb0 = discord.Embed(
            title='Tutorial - Using Emote Commands',
            description="This is a brief guide on getting started with Haerin Bot's emote commands.\n\n"+
            "There are three main components\n- **Adding/Removing**\n- **Logging**\n- **Displaying**",
            color=discord.Color.from_str('#2fcc70')
        )
        # emb0.set_thumbnail(url='https://cdn.discordapp.com/attachments/831785115465285633/1148429759198535740/image_1.png')
        emb0.set_footer(text=f"(1/6) Haerin Bot v{version} by {owner}")
        emb1 = discord.Embed(
            title='Tutorial - Adding/Removing',
            description=f"You can add and remove emotes using \n`{prefix}emote add` and `{prefix}emote remove`.\n\n"+
            "**Adding**\nYou can provide names and then 'http' links, or uploads to add emotes with the given names and sources.\n"+
            "Ex:\n"+
            f"`{prefix}emote add https://sourcelink.com/filename.png`\n↳ adds `:filename:` emote\n"+
            f"`{prefix}emote add thisname https://sourcelink.com/filename.png`\n↳ adds `:thisname:` emote, same source\n"+
            f"`{prefix}emote add (upload 2 files)`\n↳ adds the 2 files with their filenames as the emote names\n"+
            f"`{prefix}emote add thisname1 thisname2 (upload 2 files)`\n↳ adds `:thisname1:`, `:thisname2:` emote with uploaded sources\n\n"+
            f"**Removing**\nYou can remove multiple emotes by providing them with\n"+
            f"`{prefix}emote remove :emote1: :emote2: ...`\n↳ removes all emotes given.\n\n"+
            "Using these commands allows you to take advantage of all commands in **emote logging** -->",
            color=discord.Color.from_str('#2fcc70')
        )
        emb1.set_footer(text=f"(2/6) Haerin Bot v{version} by {owner}")
        emb2 = discord.Embed(
            title='Tutorial - Logging (1/2)',
            description=f"Haerin Bot can keep track of all emote and sticker updates and report them in a dedicated channel.\n\n"+
            f"To set the log channel for emote updates, use \n`{prefix}emote log <#channel>`\n\n"+
            f"**Updates**\nWhenever an emote/sticker is added, a batch update of the added emotes and stickers from the last 30mins will be posted.\n"+
            f"Emote removals can also be logged, as long as they are removed via \n`{prefix}emote remove`\n\n"+
            f"**Publishing**\nIf the logging channel is a news/announcement channel, you can set the updates for added emotes to publish automatically using \n`{prefix}emote log autopublish [on | off]`\n"+
            f"Emote removal updates do not get published.\n\n"
            f"**Source Logging**\nIf you want a channel to log the sources used to create the emotes, select a source logging channel with \n`{prefix}emote log source <#channel>`\n"+
            f"This will log sources when the emotes are added via \n`{prefix}emote add`"+
            f"\n\nFor more detailed information on logging, use \n`{prefix}help emote log`",
            color=discord.Color.from_str('#2fcc70')
        )
        emb2.set_footer(text=f"(3/6) Haerin Bot v{version} by {owner}")
        emb3 = discord.Embed(
            title='Tutorial - Logging, Custom Headers (2/2)',
            description=f'By default, updates will be done with the headers "**Added:**" and "**Removed:**".\n'+
            f'This can be changed to generally cover special cases. Here are some example cases:\n\n'+
            f"**Transferred/Promoted Emotes**\nIf an emote is removed on the case that it was moved to a different server, "+
            f'this can be reflected in the `emote remove` command:\n'+
            f'`{prefix}emote remove Transferred (to Main Server): :emote1: :emote2:`\n↳ The log update will show\n'
            f'> **Transferred (to Main Server):**\n> :emote1:\n> :emote2:\n\n'+
            f"**Crediting Users**\nIf an emote/sticker is added upon someone's suggestion or creation, and you would like to give credit in the log, "+
            f"you can do so using\n`emote log update Added (cr:@user):`\n↳ The log update will show\n"+
            f'> **Added (cr:@user):**\n> :emote1: :emote2: :emote3: ...\n'+
            f'Every emote in the current update batch will be under this new header. Therefore, if you have current updates to have posted '+
            f'normally, you should run `{prefix}emote log update` first and then add the emotes and update with the custom header.'+
            f'\n\nThe custom headers can be mostly anything. As long as its in the correct spot in the command, it should work as expected.'+
            f"\n\nAnd there's likely many more special cases. Use these custom header options as needed."+
            f"\n\nFor more detailed information on logging, use \n`{prefix}help emote log`",
            color=discord.Color.from_str('#2fcc70')
        )
        emb3.set_footer(text=f"(4/6) Haerin Bot v{version} by {owner}")
        emb4 = discord.Embed(
            title='Tutorial - Displaying',
            description=f"You can display all emotes/stickers in a given server using \n`{prefix}emote display`\n\n"+
            f"You can set a channel dedicated to an emote display gallery via \n`{prefix}emote display channel <#channel>`\n"+
            f"The display will automatically be reposted every time an emote is added/removed. Stickers are not included in the display."+
            f"\n\nFor more detailed information on displaying, use \n`{prefix}help emote display`",
            color=discord.Color.from_str('#2fcc70')
        )
        emb4.set_footer(text=f"(5/6) Haerin Bot v{version} by {owner}")
        emb5 = discord.Embed(
            title='Tutorial - Kang Kitty Cord',
            url='https://discord.gg/DZdAeBZeGJ',
            description=f"Examples of emote logging and displaying can be found in Kang Kitty Cord, an emote server made by {owner} dedicated to emotes for NewJeans Kang Haerin",
            color=discord.Color.from_str('#2fcc70')
        )
        emb5.set_image(url='https://cdn.discordapp.com/attachments/1061803536679194704/1148072103384465530/kangkittycordwelcomeimage3.gif')
        emb5.set_footer(text=f"(6/6) Haerin Bot v{version} by {owner}")

        embed_pages = {
            0 : emb0,
            1 : emb1,
            2 : emb2,
            3 : emb3,
            4 : emb4,
            5 : emb5,
        }

        page = 0
        message = await ctx.send(embed=embed_pages[page])

        # Define reaction emojis
        turn_emotes = ['⬅', '➡']

        # Add reactions to navigate pages
        for turn_emote in turn_emotes:
            await message.add_reaction(turn_emote)

        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in turn_emotes

        not_timed_out = True
        while not_timed_out:
            try:
                reaction, user = await self.bot.wait_for('reaction_add', timeout=120, check=check)

                if str(reaction.emoji) == turn_emotes[1] and page < len(embed_pages) - 1:
                    page += 1
                elif str(reaction.emoji) == turn_emotes[0] and page > 0:
                    page -= 1

                await message.edit(embed=embed_pages[page])
                await message.remove_reaction(reaction, user)

            except:
                await message.clear_reactions()
                not_timed_out = False
                pass


async def setup(bot):
    await bot.add_cog(Emote(bot))