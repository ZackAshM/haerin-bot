import discord
from discord.ext import commands
import json
# import aiosqlite
import requests
from utils.database import db_execute

with open('config.json', 'r') as config_file:
    configData = json.load(config_file)

class Message(commands.Cog):
    """Commands pertaining to sending messages"""
    def __init__(self, bot):
        self.bot = bot
        self.db = configData["DATABASE"]


    @commands.command(
            name='say',
            brief='Send a message in a channel'
    )
    @commands.has_permissions(manage_messages=True)
    async def say(self, ctx, *, message):
        """
        Command: **say**

        Send a message in a channel. If no channel is given, message is sent in this channel.

        __Usage:__
        `{prefix}say (<#channel>) <message>`

        Permissions:
        manage_messages
        """

        if message:
            try:
                channel_mention = message.split(' ')[0]
                channel_id = channel_mention[2:-1]
                channel = discord.utils.get(ctx.guild.channels, id=int(channel_id))
                if channel is None:
                    ch = ctx.channel
                else:
                    ch = channel
                chLength = len(channel_mention) + 1
                if len(message) > chLength:
                    message = message[chLength:]
                else:
                    return
            except:
                ch = ctx.channel
                pass
            await ch.send(message)
        else:
            return
        

    # -------------------------------------------------
    # -- WELCOME --------------------------------------
    # -------------------------------------------------
        
    
    @commands.group(
            name='welcome',
            invoke_without_command=True
    )
    @commands.has_permissions(administrator=True)
    async def welcome(self, ctx, *, message):
        """
        Command: **welcome**

        Set a message that is sent to a given channel whenever a new user joins.

        __Usage:__
        `{prefix}welcome <#channel> (embed) <message>`
        ↳ Set a welcome message and the channel where it will be sent
        `{prefix}welcome embed <subcommand>`
        ↳ Set additional embed settings. Use `^^help message welcome embed` for full list of embed setting commands.
        `{prefix}welcome test`
        ↳ Send a test welcome message in this channel
        `{prefix}welcome disable`
        ↳ Disable welcome messages

        Available placeholders to use in <message>: {{mention}}, {{name}}, {{server}}, {{membercount}}

        Permissions:
        administrator
        """
        prefix = (await db_execute(self.db, 'SELECT prefix FROM config WHERE guildID=?', ctx.guild.id))[0]
        currentWelcomeChannelID, currentEmbedBool = await db_execute(self.db, 'SELECT welcomeChannelID, embedBool FROM message WHERE guildID=?',ctx.guild.id)

        # handle empty input
        if not message:
            if currentWelcomeChannelID:
                try:
                    welCh = discord.utils.get(ctx.guild.channels, id=int(currentWelcomeChannelID))
                    if welCh:
                        embStr = "with" if currentEmbedBool else "without"
                        await ctx.send(f"Welcome message is enabled {embStr} embed and set to channel {welCh.mention}. Use `{prefix}welcome test` to preview it here.")
                        return
                except:
                    pass
            await ctx.send(f"Use `{prefix}help message welcome` to see available commands.")
            return
        
        # handle channel parameter
        try:
            channel_mention = message.split(' ')[0]
            channel_id = channel_mention[2:-1]
            channel = discord.utils.get(ctx.guild.channels, id=int(channel_id))
            if channel is None:
                raise ValueError('Invalid channel.')
            else:
                chLength = len(channel_mention) + 1
                if len(message) > chLength:
                    message = message[chLength:]
                else:
                    ctx.reply(f"Provide a message. Use `{prefix}help message welcome` to see available options and usage.", delete_after=20)
                    return
        except:
            raise ValueError('Invalid channel.')

        # handle embed parameter
        if message.split(' ')[0].lower() == 'embed':
            newEmbedBool = True
            message = message[6:] # 'embed' + space = 6
        else:
            newEmbedBool = currentEmbedBool

        # set new channel, message, and embed bool
        await db_execute(self.db, 'UPDATE message SET welcomeChannelID=?, welcomeMessage=?, embedBool=? WHERE guildID=?', 
                             int(channel_id), message, int(newEmbedBool), ctx.guild.id, exec_type='update')
        
        embStr = "with" if newEmbedBool else "without"
        await ctx.send(f'Welcome message has been set {embStr} embed and channel {channel.mention}!')

    
    @welcome.group(
            name='embed',
            brief='configure embed settings',
            invoke_without_command=True
    )
    @commands.has_permissions(administrator=True)
    async def welcome_embed(self, ctx):
        """
        Command: **welcome embed**

        Set an embed welcome message instead of regular text.

        __Usage:__
        `{prefix}welcome embed title <text>`
        ↳ Set embed title
        `{prefix}welcome embed color <color>`
        ↳ Set embed color
        `{prefix}welcome embed footer <text>`
        ↳ Set embed footer
        `{prefix}welcome embed image <link/upload>`
        ↳ Set embed image
        `{prefix}welcome embed thumbnail <link/upload>`
        ↳ Set embed thumbnail
        `{prefix}welcome embed reset [ (title) (color) (footer) (image) (thumbnail) | (all) ]`
        ↳ Reset/Disable the given settings, or all settings if "all" is given
        `{prefix}welcome embed disable`
        ↳ Disable embed. Welcome message still enabled, but uses regular text

        To enable embed, add the parameter "embed" before the welcome message: `{prefix}welcome <#channel> embed <message>`

        Available placeholders to use in <text>: {{mention}}, {{name}}, {{server}}, {{membercount}}

        Permissions:
        administrator
        """
        prefix = (await db_execute(self.db, 'SELECT prefix FROM config WHERE guildID=?', ctx.guild.id))[0]
        currentEmbedBool = (await db_execute(self.db, 'SELECT embedBool FROM message WHERE guildID=?',ctx.guild.id))[0]

        if currentEmbedBool:
            embed = "enabled"
            msgAdd = f'To see commands for configuring embed settings, use `{prefix}help message welcome embed`'
        else:
            embed = "disabled"
            msgAdd = f'To enable embed, add the parameter "embed" before the welcome message: `{prefix}welcome <#channel> embed <message>`'
        msg = f"Embed is currently {embed}. " + msgAdd

        await ctx.send(msg)

    @welcome_embed.command(
            name='title'
    )
    @commands.has_permissions(administrator=True)
    async def embed_title(self, ctx, *, text : str = ''):
        """
        Command: **welcome embed title**

        Set embed title.

        __Usage:__
        `{prefix}welcome embed title <text>`

        Available placeholders to use in <text>: {{mention}}, {{name}}, {{server}}, {{membercount}}

        Permissions:
        administrator
        """

        prefix = (await db_execute(self.db, 'SELECT prefix FROM config WHERE guildID=?', ctx.guild.id))[0]

        if text == '':
            raise ValueError(f'Invalid input. Did you mean `{prefix}welcome embed disable` or `{prefix}welcome embed reset title`?')
            return
        
        if len(text) > 256:
            raise ValueError('Title can only be up to 256 characters.')
        
        await db_execute(self.db, 'UPDATE message SET embedTitle=? WHERE guildID=?', text, ctx.guild.id, exec_type='update')
        await ctx.send('Welcome embed title is set')

    @welcome_embed.command(
            name='color'
    )
    @commands.has_permissions(administrator=True)
    async def embed_color(self, ctx, color : str = ''):
        """
        Command: **welcome embed color**

        Set embed color.

        __Usage:__
        `{prefix}welcome embed color <color>`

        The following formats for <color> are accepted:
        - `0x<hex>`
        - `#<hex>`
        - `0x#<hex>`
        - `rgb(<number>, <number>, <number>)`

        Allowed values for `<number>` are anything from 0-255

        Permissions:
        administrator
        """

        prefix = (await db_execute(self.db, 'SELECT prefix FROM config WHERE guildID=?', ctx.guild.id))[0]

        if color == '':
            raise ValueError(f'Invalid input. Did you mean `{prefix}welcome embed disable` or `{prefix}welcome embed reset color`?')
            return
        
        try:
            newColorTest = discord.Color.from_str(color)
            if newColorTest is None:
                raise ValueError
            newColor = color
        except ValueError:
            raise ValueError('Invalid color input.')
        
        await db_execute(self.db, 'UPDATE message SET embedColor=? WHERE guildID=?', newColor, ctx.guild.id, exec_type='update')
        await ctx.send('Welcome embed color is set')

    @welcome_embed.command(
            name='footer'
    )
    @commands.has_permissions(administrator=True)
    async def embed_footer(self, ctx, *, text : str = ''):
        """
        Command: **welcome embed footer**

        Set embed footer.

        __Usage:__
        `{prefix}welcome embed footer <text>`

        Available placeholders to use in <text>: {{mention}}, {{name}}, {{server}}, {{membercount}}

        Permissions:
        administrator
        """

        prefix = (await db_execute(self.db, 'SELECT prefix FROM config WHERE guildID=?', ctx.guild.id))[0]

        if text == '':
            raise ValueError(f'Invalid input. Did you mean `{prefix}welcome embed disable` or `{prefix}welcome embed reset footer`?')
            return
        
        if len(text) > 2048:
            raise ValueError('Footer can only be up to 2048 characters.')
        
        await db_execute(self.db, 'UPDATE message SET embedFooter=? WHERE guildID=?', text, ctx.guild.id, exec_type='update')
        await ctx.send('Welcome embed footer is set')

    @welcome_embed.command(
            name='image'
    )
    @commands.has_permissions(administrator=True)
    async def embed_image(self, ctx, *, link : str = ''):
        """
        Command: **welcome embed image**

        Set embed image.

        __Usage:__
        `{prefix}welcome embed image <link/upload>`

        If a link is provided, it must be a 'http' link.

        Permissions:
        administrator
        """

        prefix = (await db_execute(self.db, 'SELECT prefix FROM config WHERE guildID=?', ctx.guild.id))[0]

        uploads = [source.url for source in ctx.message.attachments]
        if uploads:
            image_url = uploads[0]
        elif 'http' in link:
            image_url = link
        elif link == '':
            raise ValueError(f'Invalid input. Did you mean `{prefix}welcome embed disable` or `{prefix}welcome embed reset image`?')
            return
        else:
            raise ValueError('Invalid image input.')
            return

        # test if image works
        try:
            response = requests.get(image_url)
            image = response.content
        except:
            raise ValueError('Input image was not found.')
            return
        
        await db_execute(self.db, 'UPDATE message SET embedImage=? WHERE guildID=?', image_url, ctx.guild.id, exec_type='update')
        await ctx.send('Welcome embed image is set')

    @welcome_embed.command(
            name='thumbnail'
    )
    @commands.has_permissions(administrator=True)
    async def embed_thumbnail(self, ctx, *, link : str = ''):
        """
        Command: **welcome embed thumbnail**

        Set embed thumbnail.

        __Usage:__
        `{prefix}welcome embed thumbnail <link/upload>`

        If a link is provided, it must be a 'http' link.

        Permissions:
        administrator
        """

        prefix = (await db_execute(self.db, 'SELECT prefix FROM config WHERE guildID=?', ctx.guild.id))[0]

        uploads = [source.url for source in ctx.message.attachments]
        if uploads:
            thumbnail_url = uploads[0]
        elif 'http' in link:
            thumbnail_url = link
        elif link == '':
            raise ValueError(f'Invalid input. Did you mean `{prefix}welcome embed disable` or `{prefix}welcome embed reset thumbnail`?')
            return
        else:
            raise ValueError('Invalid image input.')
            return

        # test if image works
        try:
            response = requests.get(thumbnail_url)
            thumbnail = response.content
        except:
            raise ValueError('Input image was not found.')
            return
        
        await db_execute(self.db, 'UPDATE message SET embedthumbnail=? WHERE guildID=?', thumbnail_url, ctx.guild.id, exec_type='update')
        await ctx.send('Welcome embed thumbnail is set')

    @welcome_embed.command(
            name='reset'
    )
    @commands.has_permissions(administrator=True)
    async def embed_reset(self, ctx, *options):
        """
        Command: **welcome embed reset**

        Reset/disable embed settings.

        __Usage:__
        `{prefix}welcome embed reset [ (title) (color) (footer) (image) (thumbnail) | (all) ]`

        Multiple settings can be reset at once.

        Permissions:
        administrator
        """
        prefix = (await db_execute(self.db, 'SELECT prefix FROM config WHERE guildID=?', ctx.guild.id))[0]
        invalid_options = []
        success_resets = []
        if options:
            for option in options:
                if option.lower() not in ['title', 'color', 'footer', 'image', 'thumbnail', 'all']:
                    invalid_options.append(option)
                    continue
                if (option.lower() == 'title') or (option.lower() == 'all'):
                    await db_execute(self.db,'UPDATE message SET embedTitle=? WHERE guildID=?', "", ctx.guild.id, exec_type='update')
                    success_resets.append('title')
                if (option.lower() == 'color') or (option.lower() == 'all'):
                    await db_execute(self.db,'UPDATE message SET embedColor=? WHERE guildID=?', "#2fcc70", ctx.guild.id, exec_type='update')
                    success_resets.append('color')
                if (option.lower() == 'footer') or (option.lower() == 'all'):
                    await db_execute(self.db,'UPDATE message SET embedFooter=? WHERE guildID=?', "", ctx.guild.id, exec_type='update')
                    success_resets.append('footer')
                if (option.lower() == 'image') or (option.lower() == 'all'):
                    await db_execute(self.db,'UPDATE message SET embedImage=? WHERE guildID=?', "", ctx.guild.id, exec_type='update')
                    success_resets.append('image')
                if (option.lower() == 'thumbnail') or (option.lower() == 'all'):
                    await db_execute(self.db,'UPDATE message SET embedThumbnail=? WHERE guildID=?', "", ctx.guild.id, exec_type='update')
                    success_resets.append('thumbnail')
            if invalid_options:
                await ctx.reply(f'Invalid settings: {" ".join(invalid_options)} were ignored', delete_after=20)
            if success_resets:
                await ctx.send(f'Successfully reset settings: {" ".join(success_resets)}')
        else:
            emb = discord.Embed(title=f'{prefix}welcome embed reset',
                            description=f'{self.embed_reset.help.format(prefix=prefix)}',
                            color=discord.Color.dark_green())
            await ctx.send(embed=emb)

    @welcome_embed.command(
            name='disable'
    )
    @commands.has_permissions(administrator=True)
    async def embed_disable(self, ctx):
        """
        Command: **welcome embed disable**

        Disable embed welcome message. If a welcome message is already set, regular text will be used. This does not reset the embed configurations.

        __Usage:__
        `{prefix}welcome embed disable`

        Permissions:
        administrator
        """
        prefix = (await db_execute(self.db, 'SELECT prefix FROM config WHERE guildID=?', ctx.guild.id))[0]
        currentEmbedBool = (await db_execute(self.db, 'SELECT embedBool FROM message WHERE guildID=?',ctx.guild.id))[0]

        if currentEmbedBool:
            await db_execute(self.db, 'UPDATE message SET embedBool=? WHERE guildID=?', 0, ctx.guild.id, exec_type='update')
            msg = f'Embed has been disabled. To re-enable embed, add the parameter "embed" before the welcome message: `{prefix}welcome <#channel> embed <message>`'
        else:
            msg = f'Embed is already disabled.'

        await ctx.send(msg)

    @welcome.command(
        name='disable'
    )
    @commands.has_permissions(administrator=True)
    async def welcome_disable(self, ctx):
        """
        Command: **welcome disable**
        
        Disable the welcome message. Use `{prefix}welcome <#channel> <message>` to enable again.
        
        __Usage:__
        `{prefix}welcome disable`

        Permissions:
        administrator
        """
        prefix = (await db_execute(self.db, 'SELECT prefix FROM config WHERE guildID=?', ctx.guild.id))[0]

        welChID = (await db_execute(self.db, 'SELECT welcomeChannelID FROM message WHERE guildID=?',ctx.guild.id))[0]
        if welChID:
            await db_execute(self.db, 'UPDATE message SET welcomeChannelID=?, welcomeMessage=? WHERE guildID=?', 
                             0, '', ctx.guild.id, exec_type='update')
            await ctx.send(f"Welcome has been disabled. To enable, use `{prefix}welcome <#channel> <message>`")
        else:
            await ctx.send(f"Welcome message is already disabled. To enable, use `{prefix}welcome <#channel> <message>`")

    @welcome.command(
            name='test'
    )
    @commands.has_permissions(administrator=True)
    async def welcome_test(self, ctx):
        """
        Command: **welcome test**
        
        Send a test welcome message in this channel.

        __Usage:__
        `{prefix}welcome test`

        Permissions:
        administrator
        """

        prefix = (await db_execute(self.db, 'SELECT prefix FROM config WHERE guildID=?', ctx.guild.id))[0]
        
        welChID, welMsg = await db_execute(self.db, 'SELECT welcomeChannelID, welcomeMessage FROM message WHERE guildID=?',ctx.guild.id)
        if (not welChID) or (not welMsg):
            await ctx.send(f"Welcome message is disabled. To enable, use `{prefix}welcome <#channel> <message>`")
        
        await self._welcome_send(ctx.author, ctx.channel.mention)


    async def _welcome_send(self, member, channel=''):
        """Send the welcome message"""

        welChID, welMsg, embedBool, embedTitle, embedColor, embedFooter, embedImage, embedThumbnail = await db_execute(
            self.db, 'SELECT welcomeChannelID, welcomeMessage, embedBool, embedTitle, embedColor, embedFooter, embedImage, embedThumbnail FROM message WHERE guildID=?',member.guild.id)
        if channel:
            welChID = channel[2:-1]
        if welChID:
            try:
                welCh = discord.utils.get(member.guild.channels, id=int(welChID))
                if welCh is None:
                    return
            except:
                return

            if welMsg:
                guild = member.guild
                msg = welMsg.format(mention=member.mention, name=member.name, server=guild.name, membercount=guild.member_count)
                if embedBool:
                    embed = discord.Embed(description=msg)
                    if embedColor:
                        embed.color = discord.Color.from_str(embedColor)
                    if embedTitle:
                        embed.title = embedTitle.format(mention=member.mention, name=member.name, server=guild.name, membercount=guild.member_count)
                    if embedFooter:
                        embed.set_footer(text=embedFooter.format(mention=member.mention, name=member.name, server=guild.name, membercount=guild.member_count))
                    if embedImage:
                        embed.set_image(url=embedImage)
                    if embedThumbnail:
                        embed.set_thumbnail(url=embedThumbnail)
                    await welCh.send(embed=embed)
                else:
                    await welCh.send(msg)
    
    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Sends welcome message when a user joins"""
        await self._welcome_send(member)


async def setup(bot):
    await bot.add_cog(Message(bot))