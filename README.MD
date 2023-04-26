# Discord Bounty Bot
This is a Discord bot designed to manage job postings and bounties for a gaming or rpg community. More features to come!

## Installation
1. Clone the repository
2. Create a virtual environment with Python 3.8 or higher
3. Install the required dependencies with pip install -r requirements.txt
4. Create a .env file and set your DISCORD_TOKEN found in Discord's Developer Application portal.
5. Run the bot with python main.py

## Dependencies
* discord.py
* SQLAlchemy
* python-dotenv

## Commands
Note: Slash commands are supported! Just enter "/" in Discord's chat box and select the desired command options for the bot.
* \>add_mission: Adds a new mission. Only accessible by users with the "Game Master" role.
* \>add_bounty: Adds a new bounty. Only accessible by users with the "Member" role.
* \>all_missions: Shows all available missions.
* \>all_bounties: Shows all available bounties.
* \>delete_bounty: Deletes a bounty specified by bounty ID.
* \>delete_mission: Deletes a mission specified by mission ID.

## Usage
Once the bot is running and connected to your Discord server, users with the appropriate roles ("@Game Master", "@Member") can use the commands to add new job postings or view available missions.

#### Add a mission (@Game Master)
Use the >add_mission command to add a new mission. The bot will prompt you to confirm the details before adding it to the database. The mission details include the title, difficulty, reward, and description.

#### Add a bounty (@Member)
Use the >add_bounty command to add a new bounty. The bot will prompt you to confirm the details before adding it to the database. The bounty details include the target, reward, and description.

#### Delete a mission (@Game Master)
Use the >delete_mission command to delete a mission. The bot will prompt you to confirm the details before deleting it from the database.

#### Delete a bounty (@Game Master)
Use the >delete_bounty command to delete a bounty. The bot will prompt you to confirm the details before deleting it from the database.

#### View available missions
Use the >all_missions command to view all available missions. The bot will display a list of all missions currently in the database.

#### View available bounties
Use the >all_bounties command to view all available bounties. The bot will display a list of all bounties currently in the database.
