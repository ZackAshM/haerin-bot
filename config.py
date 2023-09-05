"""Initialize config data, store global vars in config.json"""

import os
HERE = os.path.dirname(os.path.abspath(__file__))

import json
import logging
from logging.config import dictConfig

from dotenv import load_dotenv
load_dotenv()

# set config parameters
VERSION = 0.9
AUTHOR = "487358061585891328"
USERNAME = "zack"
TOKEN = os.getenv("DISCORD_API_TOKEN")
DEFAULT_PREFIX = "^^"
PERMISSIONS_INT = "9332763524304"
INVITE_URL = f"https://discord.com/api/oauth2/authorize?client_id=1144064286445019207&permissions={PERMISSIONS_INT}&scope=bot"
CONFIG_PATH = os.path.join(HERE, 'config.json')
DATABASE_PATH = os.path.join(HERE, 'data/haerin.db')
_COGS_PATH = os.path.join(HERE, 'cogs')
_COG_FILES = set(os.listdir(_COGS_PATH)) - {'__init__.py', '.hide', '__pycache__', '.DS_Store'}
COGS = [f"cogs.{cog[:-3]}" for cog in _COG_FILES]
DATABASE_TABLES = {
    "config" : {
        "guildID INTEGER PRIMARY KEY" : -1,
        "prefix TEXT" : f"'{DEFAULT_PREFIX}'",
    },
    "emotelog" : {
        "guildID INTEGER PRIMARY KEY" : -1,
        "logChannelID INTEGER" : 0,
        "updateMessage TEXT" : "''",
        "updateMessageStickers TEXT" : "''",
        "messageColumnCount INTEGER" : 0,
        "messageRowCount INTEGER" : 0,
        "maxCol INTEGER" : 6,
        "maxRow INTEGER" : 5,
        "autopublish INTEGER" : 0,
        "sourceChannelID INTEGER" : 0,
    },
    "emotedisplay" : {
        "guildID INTEGER PRIMARY KEY" : -1,
        "displayChannelID INTEGER" : 0,
        "message TEXT" : "''",
        "maxCol INTEGER" : 6,
        "maxRow INTEGER" : 5,
        "messageCount INTEGER" : 0,
    },
    "message" : {
        "guildID INTEGER PRIMARY KEY" : -1,
        "welcomeChannelID INTEGER" : 0,
        "welcomeMessage TEXT" : "''",
        "embedBool INTEGER" : 0,
        "embedTitle TEXT" : "''",
        "embedColor TEXT" : "'#2fcc70'",
        "embedFooter TEXT" : "''",
        "embedImage TEXT" : "''",
        "embedThumbnail TEXT" : "''",
    }
}
_LOGCONFIG = {
    "version": 1,
    "disabled_existing_loggers": False,
    "formatters":{
        "verbose":{
            "format": "%(levelname)-10s - %(asctime)s - %(module)-15s : %(message)s",
        },
        "standard":{
            "format": "%(levelname)-10s - %(name)-15s : %(message)s",
        },
    },
    "handlers":{
        "console": {
            'level': "DEBUG",
            'class': "logging.StreamHandler",
            'formatter': "standard",
        },
        "console2": {
            'level': "WARNING",
            'class': "logging.StreamHandler",
            'formatter': "standard",
        },
        "file": {
            'level': "INFO",
            'class': "logging.FileHandler",
            'filename': "logs/infos.log",
            'mode': "w",
            'formatter': "verbose",
        },
    },
    "loggers":{
        "bot": {
            'handlers': ['console'],
            "level": "INFO",
            "propagate": False,
        },
        "discord": {
            'handlers': ['console2', "file"],
            "level": "INFO",
            "propagate": False,
        },
    },
}


# initialize configuration
UPDATE_CONFIG = False
with open(CONFIG_PATH, 'r') as file:
    CONFIG = json.load(file)

if ("VERSION" not in CONFIG) or (CONFIG["VERSION"] != VERSION):
    CONFIG["VERSION"] = VERSION
    UPDATE_CONFIG = True

if ("AUTHOR" not in CONFIG) or (CONFIG["AUTHOR"] != AUTHOR):
    CONFIG["AUTHOR"] = AUTHOR
    UPDATE_CONFIG = True

if ("USERNAME" not in CONFIG) or (CONFIG["USERNAME"] != USERNAME):
    CONFIG["USERNAME"] = USERNAME
    UPDATE_CONFIG = True

if ("TOKEN" not in CONFIG) or (CONFIG["TOKEN"] != TOKEN):
    CONFIG["TOKEN"] = TOKEN
    UPDATE_CONFIG = True

if ("PERMISSIONS_INT" not in CONFIG) or (CONFIG["PERMISSIONS_INT"] != PERMISSIONS_INT):
    CONFIG["PERMISSIONS_INT"] = PERMISSIONS_INT
    UPDATE_CONFIG = True

if ("INVITE_URL" not in CONFIG) or (CONFIG["INVITE_URL"] != INVITE_URL):
    CONFIG["INVITE_URL"] = INVITE_URL
    UPDATE_CONFIG = True

if ("DEFAULT_PREFIX" not in CONFIG) or (CONFIG["DEFAULT_PREFIX"] != DEFAULT_PREFIX):
    CONFIG["DEFAULT_PREFIX"] = DEFAULT_PREFIX
    UPDATE_CONFIG = True

if ("DATABASE" not in CONFIG) or (CONFIG["DATABASE"] != DATABASE_PATH):
    CONFIG["DATABASE"] = DATABASE_PATH
    UPDATE_CONFIG = True

if ("COGS" not in CONFIG) or (CONFIG["COGS"] != COGS):
    CONFIG["COGS"] = COGS
    UPDATE_CONFIG = True

if ("DATABASE_TABLES" not in CONFIG) or (CONFIG["DATABASE_TABLES"] != DATABASE_TABLES):
    CONFIG["DATABASE_TABLES"] = DATABASE_TABLES
    UPDATE_CONFIG = True

if UPDATE_CONFIG:
    with open(CONFIG_PATH, 'w') as file:
        json.dump(CONFIG, file)

dictConfig(_LOGCONFIG)