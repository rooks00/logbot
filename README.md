# Legacy LogBot

## How to use?
1. Clone this repository
```shell
git clone git@github.com:rooks00/logbot.git
```
2. Copy `.env.example` to `.env` .
3. Place required values inside `.env`
4. Create a virtual environment for running the bot and install required packages
```shell
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```
5. Run the bot
```shell
python3 main.py
```

## .env values required
```bash
DISCORD_TOKEN=""
MONGODB_URI=""
MONGO_DATABASE="logbot"
MYSQL_HOST=""
MYSQL_PORT=3306
MYSQL_USER=""
MYSQL_PASSWORD=""
MYSQL_DATABASE=""
```
where,
```
DISCORD_TOKEN: bot token to be used
MONGODB_URI: mongodb atlas connection URI (this stores bot configuration)
MONGO_DATABASE: database name used for storing bot config

MYSQL Details
MYSQL_HOST: host of the mysql DB (main db from where we query logs)
MYSQL_PORT: port for mysql (default is 3306)
MYSQL_USER: user to use for logging in
MYSQL_PASSWORD: password for the user
MYSQL_DATABASE: database in which user_logs table is present
```

## Bot Config explainer
We store configuration for this bot in a mongoDB Atlas database. \
It has the following fields
```shell
1. _id: generated by default
2. action_words: list of action words to search for in logs
3. channel_id: discord channel ID where messages are sent
4. last_posted_log_id: id of the last log that was posted to discord (by default, we take the MAX value of id when new config is added)
5. name: this name is used to track various configuration. Make sure to keep this unique from config to config
```

## Bot Commands
Default Prefix: `!`

### !pinghaha
**Parameter count = 0** \
Returns `Pong!` if bot is up and reachable.

### !logbot_config_list
**Parameter count = 0** \
Lists all the configs present inside mongoDB Atlas \
**Usage:** `!logbot_config_list`

### !logbot_config_details
**Parameter count = 1** \
Retrieves all details for a config (Action Words, Channel_ID, and Last posted log ID) \
**Usage:** `!logbot_config_details <Name>` \
**Example:** `!logbot_config_details Temp`

### !logbot_config_add
**Parameter count >= 3** \
Creates a new config for querying and posting logs. `Name`, `Channel_ID`, and at least one action_word is required to create a config.\
**Usage:** `!logbot_config_add <Name> <Channel_ID> <action_word_1> <action_word_2> ...` \
**Example:** `!logbot_config_add Temp 811104892306718740 Rooks Test` \
This will create a new config with following details
```shell
{
    "action_words": ["Rooks", "Test"],
    "channel_id": "811104892306718740",
    "last_posted_log_id": 116306, (or whatever the highest value present at the time)
    "name": "Temp"
}
```

### !logbot_config_delete
**Parameter count = 1** \
Deletes a config based on it's `Name` \
**Usage:** `!logbot_config_delete <Name>` \
**Example:** `!logbot_config_delete Temp`

### !logbot_config_update
**Parameter count >= 3** \
Updates a config based on it's `Name` \
**Usage:** `!logbot_config_update <Name> <New_Channel_ID> <action_word_1> <action_word_2> ...` \
**Example:** `!logbot_config_update Temp 811104892306918740 Rooks Test`


## Note
1. Bot restart is not required when configs are modified (unless the bot errored out).
2. Bot must have permission to send messages in the channel IDs specified in the config.