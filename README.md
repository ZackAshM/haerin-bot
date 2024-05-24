# haerin-bot
This project is a personal discord bot made for managing emotes and stickers. In its development, I added commands related to moderation and chatting. While its main purpose is emote management, it serves as a project for me to learn about project structuring, SQL databases, using APIs (discord), and UI interfacing.

**Lasted Updated**: Ver. 0.9, 2023 Sep 24

## Commands
1. **Config**
  - Owner commands
    - **reload**: Reloads bot cogs/extensions live.
    - **run_command**: Runs a backend command from discord interface.
    - **invite_url**: Create and send an invite for the bot with the appropriate permissions.
  - User commands
    - **set_prefix**: Sets a new prefix for the bot commands in the specific guild.
2. **message**
  - User commands
    - **say**: Posts a message from the bot to a channel.
    - **welcome**: Various commands to enable and set a welcome message for members as they join the guild.
3. **help**
  - User commands
    - **help**: Produces a help message for specified commands.
4. **emote**
  - User commands
    - **add**/**remove**/**rename**: Add, remove, or rename specified emotes.
    - **source**: Return the emote source file.
    - **log**: Various commands for logging emote changes in a specified channel.
    - **display**: Create a display for all emotes.
    - **tutorial**: Showcase a tutorial for using the bot.
