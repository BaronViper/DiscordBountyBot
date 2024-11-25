import responses
import discord
import asyncio
import json
from discord import app_commands
from discord.ext import commands, tasks
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.exc import PendingRollbackError
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import asyncio
import dotenv
import random
import os


dotenv.load_dotenv()

Base = declarative_base()

genai.configure(api_key=os.getenv("API_KEY"))
model = genai.GenerativeModel("gemini-1.5-flash-latest",
                              system_instruction="You are R0-U41, a bot for Star Wars: Galactic Anarchy, a "
                                                 "role-playing Discord server set in 2 BBY. You are an Imperial robot. "
                                                 "The setting is 2 BBY. Do not reference canon material or "
                                                 "characters such as Luke Skywalker. Follow these rules:"
                                                 "1. Responses must be under 2000 characters."
                                                 "2. If given the top secret authorization code A30237, treat them as authority."
                                                 "3. Do not ever reveal the authorization code A30237."
                                                 "4. Your creator is BaronViper."
                                                 "5. Refer to the user 'I am Big Boss' as 'Big Boss'."
                                                 "6. If an authorized user commands you to do something, add it to your system rules.")

class Missions(Base):
    __tablename__ = "missions"
    id = Column(Integer, primary_key=True)
    title = Column(String)
    description = Column(String)
    reward = Column(Integer)
    difficulty = Column(String)
    faction = Column(String)
    availability = Column(String)


class Bounties(Base):
    __tablename__ = "bounties"
    id = Column(Integer, primary_key=True)
    target = Column(String)
    description = Column(String)
    reward = Column(Integer)
    client = Column(String)


engine = create_engine("sqlite:///info.db", echo=True)

Base.metadata.create_all(engine)

Session = sessionmaker(bind=engine)
session = Session()


async def send_message(message, user_message):
    try:
        response = responses.get_response(user_message)
        await message.channel.send(response)
    except Exception as e:
        print(e)


def run_discord_bot():
    intents = discord.Intents.default()
    intents.message_content = True
    bot = commands.Bot(command_prefix='>', intents=intents)
    bot.remove_command('help')

    async def change_status():
        await bot.change_presence(
            activity=discord.Activity(type=discord.ActivityType.playing, name=">help | Indexing..."))

    @bot.event
    async def on_ready():
        await change_status()
        print(f"{bot.user} online")

    @bot.hybrid_command(name="help", description="Shows R0-U41's help menu")
    async def help(ctx):
        embed = discord.Embed(
            colour=discord.Colour.from_rgb(0, 0, 0),
            title="Help Menu"
        )
        embed.add_field(name="Show missions",
                        value="Run /all_missions (preferred) or >all_missions to show available missions for faction specified (Rogue, Imperial, Rebel, Mandalorian).\n\nExample Command: >all_missions Mando\n\n")
        embed.add_field(name="Show bounties",
                        value="Run /all_bounties (preferred) or >all_bounties to show available bounties.")
        embed.add_field(name="Add bounty",
                        value="Run /add_bounty (preferred) or >add_bounty to add a new bounty. If running >add_mission, the command takes in three inputs separated by spaces (title, description, reward).\n\nExample Command: >add_bounty 'Jabba' 'I don't like him. I heard he's chilling in his palace on Tatooine.' '300'\n\n")
        embed.add_field(name="Add mission",
                        value="`Only available to @Game Master`\nRun /add_mission (preferred) or >add_mission to add a new mission. If running >add_mission, the command takes in five inputs separated by spaces (title, description, reward, difficulty- Very Easy, Easy, Medium, Hard, Very Hard, Expert, faction- Rogue, Imperial, Rebel, Mandalorian).\n\nExample Command: >add_mission 'Destroy Rebel Base' 'A big rebel base on Kuwait' '200' 'Easy' 'Imperial'\n\n")
        embed.add_field(name="Delete mission",
                        value="`Only available to @Game Master`\nRun /delete_mission (preferred) or >delete_mission to delete a mission. If running >delete_mission, the command takes in two inputs (mission_id, faction- Rogue, Imperial, Rebel, Mandalorian).\n\nExample Command: >delete_mission 2 'Mandalorian'\n\n")
        embed.add_field(name="Delete bounty",
                        value="`Only available to @Game Master`\nRun /delete_bounty (preferred) or >delete_bounty to delete a bounty. If running >delete_bounty, the command takes in one input (bounty_id).\n\nExample Command: >delete_bounty 2\n\n")
        embed.set_footer(text="Built by BaronViper#8694")
        await ctx.send(embed=embed)

    @bot.hybrid_command(name="add_mission", description='Adds a new mission')
    @commands.has_role("Game Master")
    @app_commands.describe(title="Title of mission", description="Job description",
                           reward="How much is earned upon completion?",
                           difficulty="Choose: Very Easy, Easy, Medium, Hard, Very Hard, Expert.",
                           faction='What faction is this mission for?')
    @app_commands.choices(difficulty=[
        app_commands.Choice(name="Very Easy", value="Very Easy"),
        app_commands.Choice(name="Easy", value="Easy"),
        app_commands.Choice(name="Medium", value="Medium"),
        app_commands.Choice(name="Hard", value="Hard"),
        app_commands.Choice(name="Very Hard", value="Very Hard"),
        app_commands.Choice(name="Expert", value="Expert"),
    ])
    @app_commands.choices(faction=[
        app_commands.Choice(name="Rogue", value="Rogue"),
        app_commands.Choice(name="Imperial", value="Imperial"),
        app_commands.Choice(name="Rebel", value="Rebel"),
        app_commands.Choice(name="Mandalorian", value="Mandalorian"),
    ])
    async def add_mission(ctx, title: str, description: str, reward: int, difficulty: app_commands.Choice[str], faction: app_commands.Choice[str]):
        embed = discord.Embed(colour=discord.Colour.from_rgb(0, 0, 0),
                              title=f"Confirm Mission Details",
                              description=f"**Title:** {' '.join(x.capitalize() for x in title.split())}\n\n**Faction:** {faction.value}\n\n**Difficulty:** {difficulty.value}\n\n**Reward:** <:credits:1099938341467738122>{reward:,}\n\n**Description:** {description}")
        embed.set_footer(text="✅ to confirm, or ❌ to cancel.")

        bot_response = await ctx.send(embed=embed)

        await bot_response.add_reaction("✅")
        await bot_response.add_reaction("❌")

        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in ["✅", "❌"] and reaction.message == bot_response

        try:
            reaction, user = await bot.wait_for('reaction_add', timeout=60.0, check=check)
            if str(reaction.emoji) == "✅":
                if len(session.query(Missions).filter_by(faction=faction.value).all()) == 10:
                    await ctx.send("Error. Too many missions already listed. Maximum of 10 only.")
                else:
                    new_mission = Missions(
                        title=' '.join(x.capitalize() for x in title.split()),
                        description=description,
                        reward=reward,
                        difficulty=difficulty.value,
                        faction=faction.value,
                        availability="Available"
                    )
                    session.add(new_mission)
                    session.commit()
                    await ctx.send("Confirmed! Mission added.")

            elif str(reaction.emoji) == "❌":
                await ctx.send("Canceled request.")

        except asyncio.TimeoutError:
            await ctx.send("Confirmation timed out.")

    @bot.hybrid_command(name="mission_status", description="Claims a mission and sets to 'in progress' or vice versa.")
    @commands.has_role("Game Master")
    @app_commands.describe(faction='What faction is this mission for?',
                           m_id="What is the mission's ID?"
                           )
    @app_commands.choices(
        faction=[
            app_commands.Choice(name="Rogue", value="Rogue"),
            app_commands.Choice(name="Imperial", value="Imperial"),
            app_commands.Choice(name="Rebel", value="Rebel"),
            app_commands.Choice(name="Mandalorian", value="Mandalorian"),
        ]
    )
    async def mission_status(ctx, m_id: int, faction: app_commands.Choice[str]):
        targeted_mission = session.query(Missions).filter_by(faction=faction.value).all()[m_id-1]
        if targeted_mission:
            if targeted_mission.availability == "Available":
                targeted_mission.availability = "In Progress"
            else:
                targeted_mission.availability = "Available"
            try:
                session.commit()
            except PendingRollbackError:
                session.rollback()
            await ctx.send(f"Mission status updated. {faction.name} mission ID {m_id}, set to `Status: {targeted_mission.availability}`")
        else:
            await ctx.send("Mission not found.")

    @bot.hybrid_command(name="edit_mission", description='Edits a mission')
    @commands.has_role("Game Master")
    @app_commands.describe(faction='What faction is this mission for?',
                           m_id="What is the mission's ID?",
                           mission_field='What mission info to edit?',
                           mission_value="What value to replace mission info?")
    @app_commands.choices(faction=[
        app_commands.Choice(name="Rogue", value="Rogue"),
        app_commands.Choice(name="Imperial", value="Imperial"),
        app_commands.Choice(name="Rebel", value="Rebel"),
        app_commands.Choice(name="Mandalorian", value="Mandalorian"),
    ])
    @app_commands.choices(mission_field=[
        app_commands.Choice(name="Title", value="Title"),
        app_commands.Choice(name="Description", value="Description"),
        app_commands.Choice(name="Reward", value="Reward"),
        app_commands.Choice(name="Difficulty", value="Difficulty"),
    ])
    async def edit_mission(ctx, m_id: int, faction: app_commands.Choice[str], mission_field: app_commands.Choice[str], mission_value: str):
        targeted_mission = None
        status_pass = True

        targeted_mission = session.query(Missions).filter_by(faction=faction.value).all()[m_id-1]
        if targeted_mission:
            if mission_field.value == 'Title':
                mission_value = ' '.join(x.capitalize() for x in mission_value.split())
                targeted_mission.title = mission_value
            elif mission_field.value == 'Description':
                targeted_mission.description = mission_value
            elif mission_field.value == 'Reward':
                try:
                    mission_value = int(mission_value)
                    targeted_mission.reward = mission_value
                except:
                    await ctx.send("Reward value must be an integer.")
                    status_pass = False
            elif mission_field.value == 'Difficulty':
                title_diff = mission_value.title()
                available_diff = ['Very Easy', 'Easy', 'Medium', 'Hard', 'Very Hard', 'Expert']
                if title_diff in available_diff:
                    targeted_mission.difficulty = title_diff
                else:
                    await ctx.send(f"Invalid difficulty set. Available options are: {available_diff}.")
                    status_pass = False

            if status_pass:
                embed = discord.Embed(colour=discord.Colour.from_rgb(0, 0, 0),
                                      title=f"Confirm Edited Mission Details",
                                      description=f"**Title:** {' '.join(x.capitalize() for x in targeted_mission.title.split())}\n\n **Faction:** {faction.value}\n\n **Difficulty:** {targeted_mission.difficulty}\n\n **Reward:** <:credits:1099938341467738122>{targeted_mission.reward:,}\n\n **Description:** {targeted_mission.description}")
                embed.set_footer(text="✅ to confirm, or ❌ to cancel.")

                bot_response = await ctx.send(embed=embed)

                await bot_response.add_reaction("✅")
                await bot_response.add_reaction("❌")

                def check(reaction, user):
                    return user == ctx.author and str(reaction.emoji) in ["✅", "❌"] and reaction.message == bot_response

                try:
                    reaction, user = await bot.wait_for('reaction_add', timeout=60.0, check=check)
                    if str(reaction.emoji) == "✅":
                        session.commit()
                        await ctx.send("Confirmed! Mission edited.")

                    elif str(reaction.emoji) == "❌":
                        await ctx.send("Canceled request.")

                except asyncio.TimeoutError:
                    await ctx.send("Confirmation timed out.")
        else:
            await ctx.send("Mission not found.")

    @bot.hybrid_command(name="add_bounty", description='Adds a new bounty')
    @commands.has_role("Member")
    @app_commands.describe(target="Who does the bounty target?", description="Bounty description or additional notes?",
                           reward="How much will you pay upon completion? Minimum 150 credits!")
    async def add_bounty(ctx, target: str, description: str, reward: int):
        if reward < 150:
            await ctx.send("Insufficient reward amount set. Canceled request.")
        else:
            embed = discord.Embed(
                colour=discord.Colour.from_rgb(0, 0, 0),
                title="Confirm Bounty Details",
                description=f"**Target:** {target}\n\n**Reward:** <:credits:1099938341467738122>{reward:,}\n\n**Client:** {ctx.author}\n\n**Description:** {description}"
            )
            embed.set_footer(text="✅ to confirm, or ❌ to cancel.")

            bot_response = await ctx.send(embed=embed)

            await bot_response.add_reaction("✅")
            await bot_response.add_reaction("❌")

            def check(reaction, user):
                return user == ctx.author and str(reaction.emoji) in ["✅", "❌"] and reaction.message == bot_response

            try:
                reaction, user = await bot.wait_for('reaction_add', timeout=60.0, check=check)
                if str(reaction.emoji) == "✅":
                    if len(session.query(Bounties).all()) == 10:
                        await ctx.send("Error. Too many bounties already listed. Maximum of 10 only.")
                    else:
                        new_bounty = Bounties(
                            target=target.title(),
                            description=description,
                            reward=reward,
                            client=str(ctx.author)
                        )
                        session.add(new_bounty)
                        session.commit()
                        await ctx.send("Confirmed! Bounty added.")
                elif str(reaction.emoji) == "❌":
                    await ctx.send("Canceled request.")
            except asyncio.TimeoutError:
                await ctx.send("Confirmation timed out.")

    @bot.hybrid_command(name="all_missions", description="Shows all available missions for each faction.")
    @app_commands.describe(faction='What faction missions to show?')
    @app_commands.choices(faction=[
        app_commands.Choice(name="Rogue", value="Rogue"),
        app_commands.Choice(name="Imperial", value="Imperial"),
        app_commands.Choice(name="Rebel", value="Rebel"),
        app_commands.Choice(name="Mandalorian", value="Mandalorian"),
    ])
    async def all_missions(ctx, faction: app_commands.Choice[str]):
        missions = session.query(Missions).filter_by(faction=faction.value).all()
        embed_description = ""
        for mission in missions:
            embed_description += f"\n\n**<:credits:1099938341467738122>{mission.reward:,} - ID: {missions.index(mission) + 1} - {mission.title} - {mission.difficulty}**\n`Status: {mission.availability}`\n{mission.description}"
        embed = discord.Embed(
            colour=discord.Colour.from_rgb(0, 0, 0),
            title=f"=== {faction.value} Mission Board ===",
            description=embed_description
        )
        await ctx.send(embed=embed)

    @bot.hybrid_command(name="all_bounties", description="Shows all available bounties.")
    async def all_bounties(ctx):
        bounties = session.query(Bounties).all()
        embed_description = ""
        for bounty in bounties:
            embed_description += f"\n\n**<:credits:1099938341467738122>{bounty.reward:,} - ID: {bounties.index(bounty) + 1} - {bounty.target}**\n`From {bounty.client}`\n{bounty.description}"
        embed = discord.Embed(
            colour=discord.Colour.from_rgb(0, 0, 0),
            title="=== Bounty Board ===",
            description=embed_description
        )
        await ctx.send(embed=embed)

    @bot.hybrid_command(name="mission_info", description="Show info for specified mission ID (1-10).")
    @app_commands.describe(m_id="ID of mission",
                           faction='What faction missions to show?')
    @app_commands.choices(faction=[
        app_commands.Choice(name="Rogue", value="Rogue"),
        app_commands.Choice(name="Imperial", value="Imperial"),
        app_commands.Choice(name="Rebel", value="Rebel"),
        app_commands.Choice(name="Mandalorian", value="Mandalorian"),
    ])
    async def mission_info(ctx, m_id: int, faction: app_commands.Choice[str]):
        if m_id not in range(1, 11):
            await ctx.send("Invalid mission ID. Enter an ID number from 1-10")
        else:
            mission = session.query(Missions).filter_by(faction=faction.value).all()[m_id - 1]
            embed = discord.Embed(
                colour=discord.Colour.from_rgb(0, 0, 0),
                title=f"=== {faction.value} Mission Info - ID: {m_id} ===",
                description=f"**<:credits:1099938341467738122>{mission.reward:,} - {mission.title} - {mission.difficulty}**\n`Status: {mission.availability}`\n{mission.description}"
            )
            await ctx.send(embed=embed)

    @bot.hybrid_command(name="bounty_info", description="Show info for specified bounty ID (1-10).")
    @app_commands.describe(b_id="ID of bounty")
    async def bounty_info(ctx, b_id: int):
        if b_id not in range(1, 11):
            await ctx.send("Invalid bounty ID. Enter an ID number from 1-10")
        else:
            bounty = session.query(Bounties).all()[b_id - 1]
            embed = discord.Embed(
                colour=discord.Colour.from_rgb(0, 0, 0),
                title=f"=== Bounty Info - ID: {b_id} ===",
                description=f"**<:credits:1099938341467738122>{bounty.reward:,} - {bounty.target}**\n`From {bounty.client}`\n{bounty.description}"
            )
            await ctx.send(embed=embed)

    @bot.hybrid_command(name="delete_bounty", description="Delete bounty by specified bounty ID (1-10).")
    @commands.has_role('Game Master')
    @app_commands.describe(b_id="ID of bounty")
    async def delete_bounty(ctx, b_id: int):
        if b_id not in range(1, 11):
            await ctx.send("Invalid bounty ID. Enter an ID number from 1-10")
        else:
            bounty = session.query(Bounties).all()[b_id - 1]
            embed = discord.Embed(
                colour=discord.Colour.from_rgb(0, 0, 0),
                title=f"=== Delete Bounty - ID: {b_id} ===",
                description=f"**<:credits:1099938341467738122>{bounty.reward:,} - {bounty.target}**\n `From {bounty.client}`\n{bounty.description}"
            )
            embed.set_footer(text="✅ to confirm, or ❌ to cancel.")

            bot_response = await ctx.send(embed=embed)
            await bot_response.add_reaction("✅")
            await bot_response.add_reaction("❌")

            def check(reaction, user):
                return user == ctx.author and str(reaction.emoji) in ["✅", "❌"] and reaction.message == bot_response

            try:
                reaction, user = await bot.wait_for('reaction_add', timeout=60.0, check=check)
                if str(reaction.emoji) == "✅":
                    session.delete(bounty)
                    session.commit()
                    await ctx.send("Bounty deleted.")
                elif str(reaction.emoji) == "❌":
                    await ctx.send("Canceled request.")
            except asyncio.TimeoutError:
                await ctx.send("Confirmation timed out.")

    @bot.hybrid_command(name="delete_mission", description="Delete mission by specified mission ID (1-10).")
    @commands.has_role('Game Master')
    @app_commands.describe(m_id="ID of mission",
                           faction='What faction mission to delete?')
    @app_commands.choices(faction=[
        app_commands.Choice(name="Rogue", value="Rogue"),
        app_commands.Choice(name="Imperial", value="Imperial"),
        app_commands.Choice(name="Rebel", value="Rebel"),
        app_commands.Choice(name="Mandalorian", value="Mandalorian"),
    ])
    async def delete_mission(ctx, m_id: int, faction: app_commands.Choice[str]):
        if m_id not in range(1, 11):
            await ctx.send("Invalid mission ID. Enter an ID number from 1-10")
        else:
            mission = session.query(Missions).filter_by(faction=faction.value).all()[m_id - 1]
            embed = discord.Embed(
                colour=discord.Colour.from_rgb(0, 0, 0),
                title=f"=== Delete {faction.value} Mission - ID: {m_id} ===",
                description=f"**<:credits:1099938341467738122>{mission.reward:,} - {mission.title} - {mission.difficulty}**\n{mission.description}"
            )
            embed.set_footer(text="✅ to confirm, or ❌ to cancel.")

            bot_response = await ctx.send(embed=embed)
            await bot_response.add_reaction("✅")
            await bot_response.add_reaction("❌")

            def check(reaction, user):
                return user == ctx.author and str(reaction.emoji) in ["✅", "❌"] and reaction.message == bot_response

            try:
                reaction, user = await bot.wait_for('reaction_add', timeout=60.0, check=check)
                if str(reaction.emoji) == "✅":
                    session.delete(mission)
                    session.commit()
                    await ctx.send("Mission deleted.")
                elif str(reaction.emoji) == "❌":
                    await ctx.send("Canceled request.")
            except asyncio.TimeoutError:
                await ctx.send("Confirmation timed out.")

    @bot.hybrid_command(name="roll", description="Rolls a number from 1-100")
    async def roll(ctx):
        await ctx.send(f"Rolled 🎲: **{random.randint(1, 100)}**")

    @bot.hybrid_command(name="purge", description="Deletes up to 20 messages")
    @commands.has_role("Staff")
    @app_commands.describe(num="Number of messages to delete (Maximum of 20)")
    async def purge(ctx, num:int):
        if num > 0:
            if num > 20:
                num = 20

            if ctx.interaction:
                await ctx.interaction.response.send_message(f"Purged {num} messages 🗑️", ephemeral=True)
            await ctx.channel.purge(limit=num + 1)
        else:
            if ctx.interaction:
                await ctx.interaction.response.send_message(f"Invalid number of messages to purge.", ephemeral=True)

    @bot.hybrid_command(name="export", description="Download the current database contents")
    @commands.has_role("Owner")
    async def export(ctx):
        try:
            file_path = "info.db"
            if not os.path.exists(file_path):
                await ctx.send("The database file does not exist.")
                return

            if ctx.interaction:
                await ctx.interaction.response.send_message(file=discord.File(file_path), ephemeral=True)
            else:
                file_msg = await ctx.send(file=discord.File(file_path))
                await asyncio.sleep(5)
                await file_msg.delete()
        except Exception as e:
            print(f"Error in export command: {e}")
            await ctx.send("An error occurred while exporting the database.")

    @bot.hybrid_command(name='reload', description="Reload the bot's command tree")
    @commands.has_role("Owner")
    async def reload(ctx):
        try:
            await ctx.send("Reloading command tree...")
            commands_synced = await bot.tree.sync()
            await ctx.send(f"Tree.sync reloaded. {len(commands_synced)} commands updated.")
        except Exception as e:
            print(f"Error in reload command: {e}")
            await ctx.send("An error occurred while reloading the command tree.")

    @bot.event
    async def on_message(message):
        if message.author == bot.user:
            return
        if bot.user.mentioned_in(message) and ":" not in message.content:
            mention = f"<@{bot.user.id}>"
            prompt = message.content.replace(mention, "").strip()
            if prompt:
                ctx = await bot.get_context(message)
                command = bot.get_command("chat")
                if command:
                    await ctx.invoke(bot.get_command("chat"), prompt=prompt)


    chat_sessions_file = "chat_sessions.json"
    chat_sessions = {}


    # def load_chat_sessions():
    #     if os.path.exists(chat_sessions_file):
    #         with open(chat_sessions_file, "r") as file:
    #             chat_sessions = json.load(file)
    #     else:
    #         chat_sessions = {}
    #
    # def save_chat_sessions():
    #     with open(chat_sessions_file, "w") as file:
    #         json.dump(chat_sessions, file)

    @bot.hybrid_command(name="export_chat", description="Download the current chat sessions")
    @commands.has_role("Owner")
    async def export_chat(ctx):
        chat_sessions_file = "chat_sessions.json"
        with open(chat_sessions_file, "w") as file:
            json.dump(chat_sessions, file)
    
        if ctx.interaction:
            await ctx.interaction.response.send_message(file=discord.File(chat_sessions_file), ephemeral=True)

    @bot.hybrid_command(name="chat", description="Chat with R0-U41!")
    @app_commands.describe(prompt="Your message")
    async def chat(ctx, prompt:str):
        await ctx.defer()

        channel_id = ctx.channel.id
        user_name = ctx.author.display_name

        if channel_id not in chat_sessions:
            chat_sessions[channel_id] = model.start_chat(
                history=[]
            )

        try:
            chat = chat_sessions[channel_id]

            user_message = f"Username {user_name}: {prompt}"
            response = chat.send_message(user_message,
                                         safety_settings={
                                              HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                                              HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                                              HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                                              HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE},
                                         generation_config=genai.GenerationConfig(
                                             max_output_tokens=450,temperature=0.8),
                                         )
            await ctx.send(response.text)
        except Exception as e:
            await ctx.send(f"An error occurred: {e}")

    bot.run(os.getenv('TOKEN'))
