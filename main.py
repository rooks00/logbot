import os
import discord
import asyncio
import cryptography
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from sqlalchemy import create_engine
from urllib.parse import quote_plus
from dotenv import load_dotenv
from discord.ext import commands
from aiomysql import create_pool

# Load .env file
load_dotenv()

# MySQL Setup
mysql_pool = None

# Discord Bot Setup
intents = discord.Intents.all()
discord_bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# Create a new MongoDB client and connect to the server
mongo_client = MongoClient(os.getenv("MONGODB_URI"), server_api=ServerApi("1"))

user = quote_plus(os.getenv("MYSQL_USER"))
password = quote_plus(os.getenv("MYSQL_PASSWORD"))
mysql_db = create_engine(
    f"mysql+pymysql://{os.getenv('MYSQL_USER')}:{password}@{os.getenv('MYSQL_HOST')}:{os.getenv('MYSQL_PORT')}/{os.getenv('MYSQL_DATABASE')}",
    echo=False,
    pool_pre_ping=True,
)

mongo_db_name = os.getenv("MONGO_DATABASE")
mongo_db = mongo_client[mongo_db_name]
mongo_collection_name = "logbot_config"
mongo_collection = mongo_db[mongo_collection_name]


async def new_logbot_config(name, action_words, channel_id, last_posted_log_id=0):
    if last_posted_log_id == 0:
        last_posted_log_id = await get_max_id()

    new_document = {
        "name": name,
        "action_words": action_words,
        "channel_id": channel_id,
        "last_posted_log_id": last_posted_log_id,
    }

    # Insert the document into the new collection
    result = mongo_collection.insert_one(new_document)

    print(f"[+] Created a new record with _id: {result.inserted_id}")


def get_logbot_config(name):
    result = mongo_collection.find_one({"name": name})
    return result


def get_all_logbot_config():
    result = mongo_collection.find({})
    return result


async def update_logbot_config(name, action_words, channel_id):
    last_posted_log_id = await get_max_id()
    result = mongo_collection.update_one(
        {"name": name},
        {
            "$set": {
                "action_words": action_words,
                "channel_id": channel_id,
                "last_posted_log_id": last_posted_log_id,
            }
        },
    )
    return result


async def update_last_posted_log_id(name, last_posted_log_id):
    result = mongo_collection.update_one(
        {"name": name}, {"$set": {"last_posted_log_id": last_posted_log_id}}
    )
    print(result)


def delete_logbot_config(name):
    result = mongo_collection.delete_one({"name": name})
    print(result)


async def post_embed(embed, channel_id):
    discord_bot.channel = discord_bot.get_channel(int(channel_id))

    if discord_bot.channel is None:
        print(f"Channel with ID {channel_id} not found.")
        return

    await discord_bot.channel.send(embed=embed)


async def post_to_discord(data, channel_id, config_name):
    chunk_size = 5
    # Do custom chunk size with config name
    """
    if (config_name == "Item_Moved"):
        data = results[0]
    """

    embed_title = f"{config_name}"
    embed = discord.Embed(title=f"{embed_title}")

    # Split data in chunks to stay under discord limits
    i = 1
    for log in data:
        # Do custom parsing based on action
        """
        if (log[2] == "Item Moved"):
            log_details = f"```License: {log[1]}\nAction: {log[2]}\nDetails: {log[3]}\nMetadata: {log[4]}\nTimestamp: {log[5]}```\n"
            message += log_details
        """
        if i % (chunk_size + 1) == 0:
            await post_embed(embed, channel_id)
            embed = discord.Embed(title=f"{embed_title}")
            i = 1

        log_details = f"```License: {log[1]}\nAction: {log[2]}\nDetails: {log[3]}\nMetadata: {log[4]}\nTimestamp: {log[5]}```\n"
        embed.add_field(name="Log", value=log_details, inline=False)
        i += 1


async def query_and_post_logs():
    all_configs = get_all_logbot_config()
    for config in all_configs:
        # print(f"[+] Config Detail Format: Name - Action Words - Channel ID")
        print(
            f"[+] Loaded config: {config['name']} - {config['action_words']} - {config['channel_id']}"
        )

        async with mysql_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                actions_list = ", ".join(
                    f"'{action}'" for action in config["action_words"]
                )
                sql_query = f"""
                    SELECT id, identifier, action, details, metadata, timestamp 
                    FROM user_logs 
                    WHERE 
                        id > %s AND 
                        action IN ({actions_list}) 
                    ORDER BY id ASC
                """
                await cursor.execute(sql_query, (config["last_posted_log_id"],))

                result = await cursor.fetchall()

                if len(result) == 0:
                    print(f"[-] No logs found for config: {config['name']}")
                    continue
                await post_to_discord(result, config["channel_id"], config["name"])
                await update_last_posted_log_id(config["name"], result[-1][0])


async def get_max_id():
    async with mysql_pool.acquire() as conn:
        async with conn.cursor() as cursor:
            sql_query = f"""
                SELECT MAX(id) as max_id
                FROM user_logs
            """
            await cursor.execute(sql_query)

            result = await cursor.fetchall()
            return result[0][0]


async def process_logs():
    while True:
        # 60m:3600 , 30m:1800 , 15m:900 , 10m:600 , 5m:300 , 1m:60
        await query_and_post_logs()
        await asyncio.sleep(300)


@discord_bot.command(name="pinghaha")
async def ping(ctx):
    await ctx.send("Pong!")


@discord_bot.command(name="logbot_config_add")
async def logbot_config_add(ctx, *, items: str):
    arg_list = [item.strip() for item in items.split(" ")]
    name = arg_list[0]
    channel_id = arg_list[1]
    action_words = arg_list[2:]

    await new_logbot_config(name, action_words, channel_id)
    await ctx.send("Config added!")


@discord_bot.command(name="logbot_config_delete")
async def logbot_config_delete(ctx, name):
    delete_logbot_config(name)
    await ctx.send("Config deleted!")


@discord_bot.command(name="logbot_config_update")
async def logbot_config_update(ctx, *, items: str):
    arg_list = [item.strip() for item in items.split(" ")]
    name = arg_list[0]
    channel_id = arg_list[1]
    action_words = arg_list[2:]

    await update_logbot_config(name, action_words, channel_id)
    await ctx.send("Config updated!")


@discord_bot.command(name="logbot_config_list")
async def logbot_config_list(ctx):
    all_configs = get_all_logbot_config()
    names = [config["name"] for config in all_configs]
    numbered_list = "\n".join([f"{i + 1}. {item}" for i, item in enumerate(names)])
    await ctx.send(numbered_list)


@discord_bot.command(name="logbot_config_details")
async def logbot_config_details(ctx, name):
    config = get_logbot_config(name)
    if config is None:
        await ctx.send("Config not found.")
    else:
        await ctx.send(
            f"```Name: {config['name']}\nAction Words: {config['action_words']}\nChannel ID: {config['channel_id']}\nLast Posted Log ID: {config['last_posted_log_id']}```"
        )


@discord_bot.event
async def on_ready():
    global mysql_pool
    mysql_pool = await create_pool(
        host=os.getenv("MYSQL_HOST"),
        port=int(os.getenv("MYSQL_PORT", 3306)),
        user=os.getenv("MYSQL_USER"),
        password=os.getenv("MYSQL_PASSWORD"),
        db=os.getenv("MYSQL_DATABASE"),
        autocommit=True,
    )
    print(f"Logged in as {discord_bot.user}")

    await discord_bot.loop.create_task(process_logs())


@discord_bot.event
async def on_message(message):
    if message.author == discord_bot.user:
        return

    content = message.content.lower()
    if content.startswith(discord_bot.command_prefix):
        # Check if the command is a valid bot command
        if content[len(discord_bot.command_prefix) :].split()[0].lower() not in [
            command.name.lower() for command in discord_bot.commands
        ]:
            return

        ctx = await discord_bot.get_context(message)
        invoked_with = content[len(discord_bot.command_prefix) :].split()[0].lower()
        command = discord_bot.get_command(invoked_with)
        if command:
            ctx.invoked_with = invoked_with
            ctx.command = command
            await discord_bot.invoke(ctx)


discord_bot.run(os.getenv("DISCORD_TOKEN"))
