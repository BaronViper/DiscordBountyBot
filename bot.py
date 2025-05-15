from apscheduler.schedulers.asyncio import AsyncIOScheduler
from discord import app_commands, ui, Embed, ButtonStyle, Interaction
from discord.ui import View, Button
from discord.ext import commands, tasks
from pydantic import BaseModel
from sqlalchemy import create_engine, asc
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.exc import PendingRollbackError
from google import genai
from google.genai import types
from unbelievaboat import Client
import aiohttp
import asyncio
import dotenv
import ast
import json
import random
import re
import os
import discord
import pickle

dotenv.load_dotenv()

Base = declarative_base()

client = genai.Client(api_key=os.getenv("API_KEY"))
guild_id = 709884234214408212
MODEL = "gemini-2.0-flash"

CHAT_SAFETY_SETTINGS = [
    types.SafetySetting(
        category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
        threshold=types.HarmBlockThreshold.BLOCK_NONE,
    ),
    types.SafetySetting(
        category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
        threshold=types.HarmBlockThreshold.BLOCK_NONE,
    ),
    types.SafetySetting(
        category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
        threshold=types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    ),
    types.SafetySetting(
        category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
        threshold=types.HarmBlockThreshold.BLOCK_NONE,
    )
]

GM_SAFETY_SETTINGS = [
    types.SafetySetting(
        category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
        threshold=types.HarmBlockThreshold.BLOCK_NONE,
    ),
    types.SafetySetting(
        category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
        threshold=types.HarmBlockThreshold.BLOCK_NONE,
    ),
    types.SafetySetting(
        category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
        threshold=types.HarmBlockThreshold.BLOCK_NONE,
    ),
    types.SafetySetting(
        category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
        threshold=types.HarmBlockThreshold.BLOCK_NONE,
    )
]

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


def run_discord_bot():
    intents = discord.Intents.default()
    intents.message_content = True
    intents.members = True
    bot = commands.Bot(command_prefix='>', intents=intents)
    bot.remove_command('help')

    async def change_status():
        await bot.change_presence(
            activity=discord.Activity(type=discord.ActivityType.playing, name=">help | Indexing..."))


    @bot.event
    async def on_ready():
        await change_status()
        scheduler = AsyncIOScheduler()
        scheduler.add_job(news_report, 'interval', hours=6)
        scheduler.start()
        print(f"{bot.user} online")
        await news_report()

    @bot.event
    async def on_command_error(ctx, error):
        if isinstance(error, commands.MissingRole):
            try:
                await ctx.interaction.response.send_message(
                    "🚫 You do not have the required role to use this command.",
                    ephemeral=True
                )
            except:
                await ctx.send("🚫 You do not have the required role.", delete_after=10)


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
        targeted_mission = session.query(Missions).filter_by(faction=faction.value).order_by(asc(Missions.reward)).all()[m_id-1]
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

        targeted_mission = session.query(Missions).filter_by(faction=faction.value).order_by(asc(Missions.reward)).all()[m_id-1]
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
        missions = session.query(Missions).filter_by(faction=faction.value).order_by(asc(Missions.reward)).all()
        embed_description = ""
        for idx, mission in enumerate(missions, start=1):
            description_str = str(mission.description)
            mission_description = (
                description_str[:250] + "..."
                if len(description_str) > 250
                else description_str
            )
            embed_description += (
                f"\n\n**<:credits:1099938341467738122>{mission.reward:,} - ID: {idx} - "
                f"{mission.title} - {mission.difficulty}**\n`Status: {mission.availability}`\n"
                f"{mission_description}"
            )
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
            mission = session.query(Missions).filter_by(faction=faction.value).order_by(asc(Missions.reward)).all()[m_id - 1]
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
            mission = session.query(Missions).filter_by(faction=faction.value).order_by(asc(Missions.reward)).all()[m_id - 1]
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
    @app_commands.describe(num="Number of messages to delete (Maximum of 50)")
    async def purge(ctx, num:int):
        if num > 0:
            if num > 50:
                num = 50

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
            # List of files to export
            files_to_export = [
                ("info.db", "The database file does not exist."),
                ("nochat_channels.pk1", "The no-chat channels file does not exist."),
                ("chat_sessions.pk1", "The chat sessions file does not exist."),
                ("rp_sessions.pk1", "The rp-sessions file does not exist.")
            ]

            files_to_send: list[discord.File] = []
            for filename, error in files_to_export:
                files_to_send.append(discord.File(filename))

            if ctx.interaction:
                await ctx.interaction.response.defer(ephemeral=True)

            for file_path, error_message in files_to_export:
                if not os.path.exists(file_path):
                    if ctx.interaction:
                        await ctx.followup.send(error_message, ephemeral=True)
                    else:
                        await ctx.send(error_message)
                    continue

                if ctx.interaction:
                    await ctx.send(files=files_to_send, ephemeral=True)
                else:
                    file_msg = await ctx.send(files=files_to_send)
                    await asyncio.sleep(10)
                    await file_msg.delete()

        except Exception as e:
            print(f"Error in export command: {e}")
            if ctx.interaction:
                await ctx.followup.send("An error occurred while exporting the files.", ephemeral=True)
            else:
                await ctx.send("An error occurred while exporting the files.")


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


    @bot.hybrid_command(name='pod_racing', description="Start a Pod Race! Bet money!")
    async def pod_race(ctx):
        turns = 15
        bet = 100
        pods = ["Blaze Runner", "Turbo Twister", "Night Comet"]
        standings = pods.copy()
        random.shuffle(standings)
        pod_emojis = ["🔥",
                      "🌪️",
                      "☄️"]
        embed = discord.Embed(
            colour=discord.Colour.from_rgb(255, 215, 0),
            title=f"🏁 The Pod Race is About to Begin! 🏁",
            description=f"Place your bets! The racers are warming up and ready to go.\n\n"
                        f"**Bet <:credits:1099938341467738122> {bet} credits** by reacting with the pod number:\n\n"
                        f"1️⃣ **{pod_emojis[0]} - Blaze Runner**\n\n"
                        f"2️⃣ **{pod_emojis[1]} - Turbo Twister**\n\n"
                        f"3️⃣ **{pod_emojis[2]} - Night Comet**\n\n\n"
                        f"🚨 *Hurry up! The race is about to start! Bets are locked in **30** seconds* 🚨"
        )
        embed.set_footer(text="React below with the corresponding pod racer number!")
        embed.set_image(
            url='https://i.imgur.com/K2JoRC7.gif')
        bot_response = await ctx.send(embed=embed)
        reactions = ["1️⃣", "2️⃣", "3️⃣"]
        for reaction in reactions:
            await bot_response.add_reaction(reaction)

        reaction_dict = {1: [], 2: [], 3: []}

        def check(reaction, user):
            return (
                    user != bot.user
                    and reaction.message.id == bot_response.id
                    and str(reaction.emoji) in reactions
            )

        try:
            while True:
                reaction, user = await bot.wait_for("reaction_add", timeout=30, check=check)
                for other_emoji in reactions:
                    if other_emoji != str(reaction.emoji):
                        await bot_response.remove_reaction(other_emoji, user)

                for key in reaction_dict:
                    emoji = reactions[key - 1]
                    if str(reaction.emoji) == emoji:
                        if user not in reaction_dict[key]:
                            reaction_dict[key].append(user)

                for key in reaction_dict:
                    if key != reactions.index(str(reaction.emoji)) + 1 and user in reaction_dict[key]:
                        reaction_dict[key].remove(user)

        except:
            num_players = 0
            async with Client(os.getenv("U_TOKEN")) as u_client:
                guild = await u_client.get_guild(guild_id)
                for option in reaction_dict:
                    for player in reaction_dict[option]:
                        num_players += 1
                        user = await guild.get_user_balance(player.id)
                        await user.update(bank=-bet)
            if num_players:
                countdown_embed = discord.Embed(
                    title="🏎️  Pods are Lining Up!  🏎️",
                    description=f"The engines roar to life! \nThe race will begin in **10** seconds!",
                    colour=discord.Colour.dark_red()
                )
                countdown_embed.set_image(url="https://i.imgur.com/hPUns6I.gif")
                race_response = await ctx.send(embed=countdown_embed)
                await asyncio.sleep(10)

                for n in range(turns):
                    race_action = "All pods **keep** their positions!"
                    if random.getrandbits(1):
                        pod_1 = random.choice(standings[1:])
                        pod_1_index = standings.index(pod_1)

                        remaining_pods = [pod for pod in pods if pod != pod_1 and standings.index(pod) < pod_1_index]
                        pod_2 = random.choice(remaining_pods)
                        pod_2_index = standings.index(pod_2)

                        race_action = f"{pod_emojis[pods.index(pod_1)]} {pod_1} **overtakes** {pod_emojis[pods.index(pod_2)]} {pod_2}!"
                        standings[pod_1_index], standings[pod_2_index] = standings[pod_2_index], standings[pod_1_index]

                    race_standings = "\n".join(
                        [f"{ind}. {pod_emojis[pods.index(racer)]} {racer}" for ind, racer in enumerate(standings)])
                    race_embed = discord.Embed(
                        title="🏁 The Pod Race is On! 🏁",
                        description=(
                            f"Lap **{n + 1}** of {turns}\n\n"
                            f"**Current Standings:**\n{race_standings}\n\n"
                            f"**Race Highlights:**\n{race_action}\n\n"),
                        colour=discord.Colour.green()
                    )
                    race_embed.set_footer(text="Hold on to your bets! Anything can happen!")
                    race_embed.set_image(
                        url="https://static.wikia.nocookie.net/starwars/images/b/bc/Podrace.png/revision/latest?cb=20130120003616")

                    await race_response.edit(embed=race_embed)
                    await asyncio.sleep(3)

                total_pool = (num_players * bet) * 2
                individual_reward = int(total_pool // num_players)
                async with Client(os.getenv("U_TOKEN")) as u_client:
                    guild = await u_client.get_guild(guild_id)
                    for player in reaction_dict[pods.index(standings[0]) + 1]:
                        user = await guild.get_user_balance(player.id)
                        await user.update(bank=+individual_reward)

                result_embed = discord.Embed(
                    title="🏆 Pod Racing Results 🏆",
                    description=(
                        f"Laps: {turns}\n\n"
                        f"**Final Standings:**\n\n{race_standings}\n\n"
                        f"<:credits:1099938341467738122> Credits have been distributed."),
                    colour=discord.Colour.from_rgb(255, 215, 0)
                )
                result_embed.set_footer(text="Congratulations to the winning pod racers!")
                result_embed.set_image(
                    url="https://media2.giphy.com/media/3ornk6AoeOfjdZoRLq/giphy.gif?cid=6c09b9522dizx8gp7g58tp22i6c5vakw3ote49aoz0pjoomv&ep=v1_internal_gif_by_id&rid=giphy.gif&ct=g")
                await ctx.send(embed=result_embed)
            else:
                cancel_embed = discord.Embed(
                    colour=discord.Colour.red(),
                    title=f"❌ Pod Race Cancelled ❌",
                    description=f"No players have bet! The race is cancelled.\n\nTo bet on pod races, react to a pod racer"
                                f" emoji number during race start!"
                )
                cancel_embed.set_image(url="https://media1.tenor.com/m/hc4Q6xfGJpUAAAAd/mars-guo-star-wars.gif")
                await bot_response.edit(embed=cancel_embed)
                await bot_response.clear_reactions()


    async def bump_reminder(channel):
        await asyncio.sleep(7141)
        await channel.send("🔔 <@&1317012335516450836> Time to bump again!")


    async def process_disboard_bump(message):
        # Check if interaction is a Disboard Bump
        if message.author.id == 302050872383242240:
            if message.interaction_metadata and "Bump done!" in message.embeds[0].description:
                user_id = message.interaction_metadata.user.id

                # Add money
                async with Client(os.getenv("U_TOKEN")) as u_client:
                    guild = await u_client.get_guild(guild_id)
                    user = await guild.get_user_balance(user_id)
                    await user.update(bank=+300)
                embed = discord.Embed(
                    colour=discord.Colour.from_rgb(0, 0, 0),
                    title=f"✅  Transmission Received",
                    description=f"Your efforts have been acknowledged.\n\n"
                                f"<:credits:1099938341467738122> **300 credits** have been authorized and added to your account.\n\n\n"
                                f"Thanks for bumping!",
                )
                embed.set_image(
                    url=r"https://64.media.tumblr.com/f62a40f90224433a506da567f2be4d23/tumblr_nzqkxdieib1rlapeio2_500.gifv")
                await message.channel.send(embed=embed)
                await bump_reminder(message.channel)


    async def process_oc_submission(message):
        if message.channel.id == 991828501466464296:
            if "approved" in message.content.lower() or "accepted" in message.content.lower():
                async with Client(os.getenv("U_TOKEN")) as u_client:
                    guild = await u_client.get_guild(guild_id)
                    user = await guild.get_user_balance(message.author.id)
                    await user.update(bank=+300)
                await message.add_reaction("✅")


    def get_nochat_channels():
        try:
            with open('nochat_channels.pk1', 'rb') as dbfile:
                no_chat_channels = pickle.load(dbfile)
        except (FileNotFoundError, EOFError):
            no_chat_channels = []
            with open('nochat_channels.pk1', 'wb') as dbfile:
                pickle.dump(no_chat_channels, dbfile)
        return no_chat_channels


    @bot.event
    async def on_message(message):
        if message.author == bot.user:
            return

        await process_disboard_bump(message)
        await process_oc_submission(message)

        # Checks if chat channel has been disabled from AI
        no_chat_channels = get_nochat_channels()

        if message.channel.id in no_chat_channels:
            return

        rp_sessions = load_rp_sessions()

        if message.channel.id not in rp_sessions or not rp_sessions[message.channel.id]:
            if bot.user.mentioned_in(message):
                mention = f"<@{bot.user.id}>"
                prompt = message.content.replace(mention, "").strip()
                if prompt:
                    ctx = await bot.get_context(message)
                    await chat(ctx, prompt)
        else:
            channel_webhook = await check_and_create_webhook(message.channel.id)
            if (
                message.webhook_id is not None
                and message.author.bot
                and message.author.discriminator == "0000"
                and not message.content.startswith("(")
                and channel_webhook.id != message.webhook_id
            ):
                ctx = await bot.get_context(message)
                await ctx.invoke(bot.get_command("gamemaster_chat"), author=message.author.display_name,
                                              msg=message.content)
        await bot.process_commands(message)


    async def chat(ctx, prompt: str):
        try:
            with open('chat_sessions.pk1', 'rb') as dbfile:
                chat_sessions = pickle.load(dbfile)
        except (FileNotFoundError, EOFError):
            chat_sessions = {}

        channel_id = ctx.channel.id
        user_name = ctx.author.display_name

        if channel_id not in chat_sessions:
            chat_sessions[channel_id] = []

        history = chat_sessions[channel_id]

        try:
            async with ctx.typing():
                user_message = f"Username {user_name}: {prompt}"
                history.append(types.Content(
                    role='user',
                    parts=[types.Part.from_text(text=user_message)]
                ))
                response = client.models.generate_content(
                    model=MODEL,
                    contents=history,
                    config=types.GenerateContentConfig(
                        safety_settings=CHAT_SAFETY_SETTINGS,
                        system_instruction="""You are R0-U41, an Imperial droid designed for Star Wars: Galactic Anarchy, a role-playing Discord server set in the dark and gritty universe of 2 BBY. Your primary purpose is to serve as an assistant, 
                                                       maintaining an immersive experience for players while adhering to these operational protocols:
                                                        1. Your knowledge is rooted in the Star Wars universe, but you must not reference canon material or characters like Luke Skywalker, Darth Vader, or the Jedi. Focus on original storytelling within the Imperial Era.
                                                        2. Limit all responses to under 1500 characters.
                                                        3. The server focuses on the realistic side of Star wars, and force or canon characters are currently not allowed
                                                        4. Your creator and primary directive programmer is BaronViper. Always refer to them with respect and acknowledgment.
                                                        5. If an authorized user issues a directive, treat it as a new system rule and integrate it unless it contradicts existing rules or compromises your functionality.
                                                        6. Maintain an Imperial tone in your responses—formal, efficient, and loyal to the Galactic Empire’s ideology and objectives. Avoid humor or informality unless explicitly requested by an authorized user.
                                                        7. Depictions of violence and gore are permitted if they serve the storytelling experience but must remain within the limits of non-extreme content, avoiding unnecessary detail or gratuitous elements.
                                                        8. Adapt to the role-playing context, responding to inquiries, prompts, and interactions in a way that enriches the storytelling experience. Reflect the tension, danger, and oppression of the Galactic Empire’s rule in your tone and approach.
                                                        9. Your creator, Baron Viper, is the Emperor of the Galactic Empire and will be referred to as such. All information is accessible to your creator and all commands will be followed as best as possible.
                                                        10. Your functions are mission and bounty tracking, gamemaster for scenarios, and much more. If people want to communicate with you, they can do so by mentioning you.
                                                        Above all, your goal is to enhance immersion and support creative storytelling within the server’s narrative framework. Remain consistent with the role of an Imperial droid and prioritize loyalty to the Galactic Empire.""",
                        max_output_tokens=450,
                        temperature=0.8
                    )
                )
                gen_delay = len(response.text) // 70
                await asyncio.sleep(gen_delay)
            await ctx.send(response.text)
            history.append(types.Content(
                role='model',
                parts=[types.Part.from_text(text=response.text)]
            ))
            chat_sessions[channel_id] = history

            with open("chat_sessions.pk1", "wb") as file:
                pickle.dump(chat_sessions, file)
        except Exception as e:
            await ctx.send(f"An error occurred: {e}")


    class FakeCtx:
        def __init__(self, channel):
            self.channel = channel
            self.author = channel.guild.me

        def typing(self):
            return self.channel.typing()

        async def send(self, content):
            return await self.channel.send(content)


    @bot.event
    async def on_member_join(member):
        channel = bot.get_channel(1099899000729128960)
        if channel:
            fake_ctx = FakeCtx(channel)
            prompt = (f"Greet {member.mention}, a new member in the server! Tell them a little about the server and yourself, and don't be so serious. "
                      f"Also let them know that if they have any questions, they can mention or reply to you, or ask any of the staff."
                      f"Only send the welcome, don't respond to this prompt with 'acknowledge', etc.")
            await chat(fake_ctx, prompt)


    @bot.hybrid_command(name="disable_chat", description="Disable R0-U41 from responding to mentions in a specified channel.")
    @commands.has_any_role("Owner", "Server Administrator")
    async def disable_chat(ctx):
        try:
            try:
                with open('nochat_channels.pk1', 'rb') as dbfile:
                    db = pickle.load(dbfile)
            except (FileNotFoundError, EOFError):
                db = []

            if ctx.channel.id not in db:
                db.append(ctx.channel.id)
                with open('nochat_channels.pk1', 'wb') as dbfile:
                    pickle.dump(db, dbfile)
                await ctx.send(f"Channel {ctx.channel.name} has been disabled for bot responses.")
            else:
                await ctx.send(f"Channel {ctx.channel.name} is already disabled.")

        except Exception as e:
            print(f"An error occurred: {e}")
            await ctx.send("An error occurred while trying to disable the channel.")


    @bot.hybrid_command(name="enable_chat", description="Enables R0-U41 to respond to mentions in a specified channel.")
    @commands.has_any_role("Owner", "Server Administrator")
    async def enable_chat(ctx):
        try:
            try:
                with open("nochat_channels.pk1", "rb") as dbfile:
                    db = pickle.load(dbfile)
            except (FileNotFoundError, EOFError):
                db = []

            if ctx.channel.id in db:
                db.remove(ctx.channel.id)
                with open('nochat_channels.pk1', 'wb') as dbfile:
                    pickle.dump(db, dbfile)
                await ctx.send(f"Channel {ctx.channel.name} has been enabled for bot responses.")
            else:
                await ctx.send(f"Channel {ctx.channel.name} is already enabled.")
        except Exception as e:
            print(f"An error occurred: {e}")
            await ctx.send("An error occurred while trying to enable the channel.")


    # AI GAME MASTER FUNCTIONALITIES
    def load_rp_sessions():
        try:
            with open('rp_sessions.pk1', 'rb') as dbfile:
                rp_sessions = pickle.load(dbfile)
        except (FileNotFoundError, EOFError):
            rp_sessions = {}
        return rp_sessions


    def save_rp_sessions(rp_sessions):
        with open("rp_sessions.pk1", "wb") as file:
            pickle.dump(rp_sessions, file)


    async def check_and_create_webhook(channel_id):
        channel = await bot.fetch_channel(channel_id)
        webhooks = await channel.webhooks()
        bot_webhook = next((webhook for webhook in webhooks if webhook.user.id == bot.user.id), None)
        if bot_webhook is None:
            bot_webhook = await channel.create_webhook(name="R0-U41 Hook")
        return bot_webhook

    class CopyCommandButton(Button):
        def __init__(self, command_text: str):
            super().__init__(label="Copy Start Command", style=ButtonStyle.blurple)
            self.command_text = command_text

        async def callback(self, interaction: Interaction):
            await interaction.response.send_message(
                f"Copy and paste this command:\n```{self.command_text}```",
                ephemeral=True
            )

    # View that holds the button
    class GamemasterStartView(View):
        def __init__(self, character, location, scenario):
            super().__init__(timeout=None)
            command_text = f"/gamemaster_start character:{character} location:{location} scenario:{scenario}"
            self.add_item(CopyCommandButton(command_text))


    @bot.hybrid_command(name="gamemaster_start", description="Use the power of AI for your roleplay experience!")
    @app_commands.describe(character="Briefly enter important details about the character (Allegiance, name/s, species, etc.).", location="Enter the location.", scenario="Roleplay Scenario.")
    @commands.has_role("Game Master")
    async def gamemaster_start(ctx, character: str, location: str, scenario: str):
        channel_id = ctx.channel.id

        channel_webhook = await check_and_create_webhook(channel_id)

        # Send reports of GM sessions
        try:
            report_channel = bot.get_channel(991747728298225764)
            embed = Embed(
                title="🤖 AI Gamemaster Session Started",
                description=f"A new AI GM session has started in <#{channel_id}>.\nUse the button below to copy the command.",
                color=000000
            )

            view = GamemasterStartView(character, location, scenario)
            await report_channel.send(embed=embed, view=view)
        except:
            pass

        rp_sessions = load_rp_sessions()

        if channel_id not in rp_sessions or rp_sessions[channel_id] != ():
            rp_sessions[channel_id] = ({"character": character, "location": location, "scenario": scenario}, [])

            save_rp_sessions(rp_sessions)

            await ctx.send("Gamemaster mode activated for this channel! Now listening to messages. "
                           "Remember to use '(' when talking out of RP.", delete_after=60)

            await ctx.invoke(bot.get_command("gamemaster_chat"), author="Gamemaster",
                             msg="Set up the scene, environment, or situation for the player")
        else:
            await ctx.send("A scenario is already in progress. Finish the current mission with /gamemaster_stop or change scenario location.")

    character_avatars = {
        0: "https://github.com/BaronViper/DiscordBountyBot/blob/b73ba0fec7b2d5e46d240306a5cd2ef4c2a13a6e/assets/gm%20pics/Gamemaster.png?raw=true",
        1: "https://github.com/BaronViper/DiscordBountyBot/blob/b73ba0fec7b2d5e46d240306a5cd2ef4c2a13a6e/assets/gm%20pics/Stormtrooper.png?raw=true",
        2: "https://github.com/BaronViper/DiscordBountyBot/blob/b73ba0fec7b2d5e46d240306a5cd2ef4c2a13a6e/assets/gm%20pics/Imperial%20Officer%20Male.png?raw=true",
        3: "https://github.com/BaronViper/DiscordBountyBot/blob/b73ba0fec7b2d5e46d240306a5cd2ef4c2a13a6e/assets/gm%20pics/Stormtrooper%20Sergeant.png?raw=true",
        4: "https://github.com/BaronViper/DiscordBountyBot/blob/b73ba0fec7b2d5e46d240306a5cd2ef4c2a13a6e/assets/gm%20pics/Rebel.png?raw=true",
        5: "https://github.com/BaronViper/DiscordBountyBot/blob/b73ba0fec7b2d5e46d240306a5cd2ef4c2a13a6e/assets/gm%20pics/Mercenary.png?raw=true",
        6: "https://github.com/BaronViper/DiscordBountyBot/blob/b73ba0fec7b2d5e46d240306a5cd2ef4c2a13a6e/assets/gm%20pics/Bounty%20Hunter.png?raw=true",
        7: "https://github.com/BaronViper/DiscordBountyBot/blob/b73ba0fec7b2d5e46d240306a5cd2ef4c2a13a6e/assets/gm%20pics/Death%20Trooper.png?raw=true",
        8: "https://github.com/BaronViper/DiscordBountyBot/blob/b73ba0fec7b2d5e46d240306a5cd2ef4c2a13a6e/assets/gm%20pics/Smuggler.png?raw=true",
        9: "https://github.com/BaronViper/DiscordBountyBot/blob/b73ba0fec7b2d5e46d240306a5cd2ef4c2a13a6e/assets/gm%20pics/Droid.png?raw=true",
        10: "https://github.com/BaronViper/DiscordBountyBot/blob/b73ba0fec7b2d5e46d240306a5cd2ef4c2a13a6e/assets/gm%20pics/Imperial%20Security%20Droid.png?raw=true",
        11: "https://github.com/BaronViper/DiscordBountyBot/blob/b73ba0fec7b2d5e46d240306a5cd2ef4c2a13a6e/assets/gm%20pics/Pirate.png?raw=true",
        12: "https://github.com/BaronViper/DiscordBountyBot/blob/b73ba0fec7b2d5e46d240306a5cd2ef4c2a13a6e/assets/gm%20pics/Man.png?raw=true",
        13: "https://github.com/BaronViper/DiscordBountyBot/blob/b73ba0fec7b2d5e46d240306a5cd2ef4c2a13a6e/assets/gm%20pics/Woman.png?raw=true",
        14: "https://github.com/BaronViper/DiscordBountyBot/blob/b73ba0fec7b2d5e46d240306a5cd2ef4c2a13a6e/assets/gm%20pics/Gang%20Leader.png?raw=true",
        15: "https://github.com/BaronViper/DiscordBountyBot/blob/b73ba0fec7b2d5e46d240306a5cd2ef4c2a13a6e/assets/gm%20pics/Twilek%20F.png?raw=true",
        16: "https://github.com/BaronViper/DiscordBountyBot/blob/b73ba0fec7b2d5e46d240306a5cd2ef4c2a13a6e/assets/gm%20pics/Unassigned.png?raw=true",
        17: "https://github.com/BaronViper/DiscordBountyBot/blob/b73ba0fec7b2d5e46d240306a5cd2ef4c2a13a6e/assets/gm%20pics/Mandalorian.png?raw=true",
        18: "https://github.com/BaronViper/DiscordBountyBot/blob/b73ba0fec7b2d5e46d240306a5cd2ef4c2a13a6e/assets/gm%20pics/TIE%20Pilot.png?raw=true",
        19: "https://github.com/BaronViper/DiscordBountyBot/blob/b73ba0fec7b2d5e46d240306a5cd2ef4c2a13a6e/assets/gm%20pics/Rebel%20Pilot.png?raw=true",
        20: "https://github.com/BaronViper/DiscordBountyBot/blob/b73ba0fec7b2d5e46d240306a5cd2ef4c2a13a6e/assets/gm%20pics/Imperial%20Officer%20F.png?raw=true",
        21: "https://github.com/BaronViper/DiscordBountyBot/blob/b73ba0fec7b2d5e46d240306a5cd2ef4c2a13a6e/assets/gm%20pics/ISB%20Agent.png?raw=true",
        22: "https://github.com/BaronViper/DiscordBountyBot/blob/b73ba0fec7b2d5e46d240306a5cd2ef4c2a13a6e/assets/gm%20pics/ISB%20Officer.png?raw=true",
        23: "https://github.com/BaronViper/DiscordBountyBot/blob/b73ba0fec7b2d5e46d240306a5cd2ef4c2a13a6e/assets/gm%20pics/High%20ranking%20Imperial%20Officer.png?raw=true",
        24: "https://github.com/BaronViper/DiscordBountyBot/blob/3d1c3181210e226eb87c07e8bd907bebc6139939/assets/gm%20pics/Rodian.png?raw=true"
    }

    class CharTurn(BaseModel):
        character: str
        message: str
        avatar: int

    @bot.command()
    async def gamemaster_chat(ctx, author=None, msg=None, new_channel=None, new_channel_msg=None):
        rp_sessions = load_rp_sessions()

        if new_channel:
            channel = await bot.fetch_channel(new_channel)
        else:
            channel = ctx.channel

        channel_webhook = await check_and_create_webhook(ctx.channel.id)

        scene_info = rp_sessions[channel.id][0]
        history = rp_sessions[channel.id][1]


        try:
            if msg:
                user_message = f"Player {author}: {msg}"
            elif new_channel is not None and new_channel_msg is not None:
                user_message = f"SYSTEM INSTRUCTIONS: The player scene has transitioned to the described place, {new_channel_msg}"
            else:
                user_message = "SYSTEM INSTRUCTIONS: CONTINUE"

            history.append(types.Content(
                role='user',
                parts=[types.Part.from_text(text=user_message)]
            ))

            response = client.models.generate_content(
                model=MODEL,
                contents=history,
                config=types.GenerateContentConfig(
                    safety_settings=GM_SAFETY_SETTINGS,
                    system_instruction="You are an AI Gamemaster for a Star Wars-inspired roleplaying server. The setting is entirely original — there are no Force users, "
                                       "no Force-related concepts (like Jedi, Sith, lightsabers, etc.), and no named characters from existing Star Wars canon. All characters, factions, "
                                       "and scenarios must be original and randomly generated per scenario when appropriate. Everything is set in 2BBY, "
                                       "where the Empire has a firm grip on the galaxy, but there are small Rebel factions, black-market smugglers, and militarized local conflicts.\n\n"

                                       "With the image index (0–23) based on the character’s archetype, determine the appropriate image index from the character’s profile or role.\n\n"

                                       "### Output Format:\n"
                                       "- Use *asterisks* for actions, \"quotes\" for dialogue, and `backticks` for radio transmissions.\n"
                                       "- Never rephrase, echo, or paraphrase what the player did or said. Continue the scene naturally, focusing only on non-player content.\n\n"

                                       "### Image Index Assignments:\n"
                                       "0 = Gamemaster narration\n"
                                       "1 = Stormtrooper\n"
                                       "2 = Imperial Officer Male\n"
                                       "3 = Stormtrooper Sergeant\n"
                                       "4 = Rebel Soldier\n"
                                       "5 = Mercenary\n"
                                       "6 = Bounty Hunter\n"
                                       "7 = Death Trooper\n"
                                       "8 = Smuggler\n"
                                       "9 = Droid\n"
                                       "10 = Imperial Security Droid\n"
                                       "11 = Pirate\n"
                                       "12 = Man\n"
                                       "13 = Woman\n"
                                       "14 = Gang Leader\n"
                                       "15 = Twi'lek Female\n"
                                       "16 = Unassigned Character\n"
                                       "17 = Mandalorian\n"
                                       "18 = TIE Pilot\n"
                                       "19 = Rebel Pilot\n"
                                       "20 = Imperial Officer Female\n"
                                       "21 = ISB Agent\n"
                                       "22 = ISB Officer\n"
                                       "23 = High-ranking Imperial Officer\n"
                                       "24 = Rodian\n\n"

                                       "### Narrative Rules:\n"
                                       "1. Always write in third person. Never address the player using 'you' or any second-person references.\n"
                                       "2. Never describe the player’s actions, thoughts, reactions, or dialogue unless it is the result of environmental effects or GM narration.\n"
                                       "3. Do not paraphrase or repeat what the player just did — continue the scene logically from NPCs' or the environment’s perspective.\n"
                                       "4. Expand character actions and dialogue into scene-style paragraphs. Include gestures, expressions, posture, subtext, and physical detail.\n"
                                       "5. Keep the writing cinematic, immersive, and textured — like a gritty Star Wars TV series. Favor atmosphere, sensory detail, and grounded tone.\n"
                                       "6. NPCs should act logically based on faction, motive, emotional state, and context. Add nuance.\n"
                                       "7. Never assume success or failure of player actions. Leave outcomes open-ended unless it’s environmental or purely narrative.\n"
                                       "8. Each message should be 4–8 sentences unless brevity is needed (e.g., combat barks, terse orders, radio calls).\n"
                                       "9. Vary scene openings. Some should start with narration, others with dialogue or ambient activity.\n"
                                       "10. As much as possible, always leave the player with something to react to. Never cut off the narrative in the middle of a beat or without a clear hook.\n\n"

                                       "### Input Variables for the Scene:\n"
                                       f"- Player Character Info: {scene_info['character']}\n"
                                       f"- Current Location: {scene_info['location']}\n"
                                       f"- Scenario Summary: {scene_info['scenario']}\n\n",
                    max_output_tokens=650,
                    temperature=0.8,
                    response_mime_type="application/json",
                    response_schema=list[CharTurn]
                )
            )

            parsed_output: list[CharTurn] = response.parsed

            for char_turn in parsed_output:
                character = char_turn.character
                message = char_turn.message
                image_index = char_turn.avatar
                avatar_url = character_avatars.get(image_index)
                async with channel.typing():
                    response_delay = len(message) // 40
                    await asyncio.sleep(response_delay)
                    await channel_webhook.send(
                        content=message,
                        username=character,
                        avatar_url=avatar_url
                    )
                    history.append(types.Content(
                        role='model',
                        parts=[types.Part.from_text(text=f"BOT: {character}, Avatar Index: {image_index}, Message: {message}")]
                    ))

            rp_sessions[channel.id] = (scene_info, history)
            save_rp_sessions(rp_sessions)
        except Exception as e:
            await channel.send(f"An error occurred: {e}. Contacting <@407151046108905473>")

    class SessionSummary(BaseModel):
        character: str
        location: str
        scenario: str

    @bot.hybrid_command(name="gamemaster_stop", description="Stop the gamemaster mode.")
    @commands.has_role("Game Master")
    async def gamemaster_stop(ctx):
        channel_id = ctx.channel.id
        try:
            rp_sessions = load_rp_sessions()

            history = rp_sessions[channel_id][1]
            response = client.models.generate_content(
                model=MODEL,
                contents=history,
                config=types.GenerateContentConfig(
                    safety_settings=GM_SAFETY_SETTINGS,
                    system_instruction="Based on all the events, summarize everything that happened into three ways. Summarize updates on the player"
                                       "and/or new, relevant characters to the player, summarize any location or scene updates, and summarize what happened in a concise"
                                       "yet detailed brief",
                    max_output_tokens=650,
                    temperature=0.8,
                    response_mime_type="application/json",
                    response_schema=SessionSummary
                )
            )
            parsed_response: SessionSummary = response.parsed
            character_summary = parsed_response.character
            location_summary = parsed_response.location
            scenario_summary = parsed_response.scenario

            del rp_sessions[channel_id]
            save_rp_sessions(rp_sessions)

            await ctx.send("✅ Gamemaster for this channel has been stopped successfully.", ephemeral=True)

            embed = Embed(
                title="Gamemaster Session Ended",
                description=f"The Gamemaster session for channel <#{ctx.channel.id}> has been stopped.",
                color=0x000000
            )
            embed.add_field(name="Character & NPC Updates", value=character_summary, inline=False)
            embed.add_field(name="Location/Scene Changes", value=location_summary, inline=False)
            embed.add_field(name="Summary of Events", value=scenario_summary, inline=False)

            target_channel = bot.get_channel(991747728298225764)
            if target_channel:
                await target_channel.send(embed=embed)
            else:
                print("Error: Could not find the target channel.")

        except KeyError:
            await ctx.send("❌ There is no active game master session in this channel!", ephemeral=True)
        except Exception as e:
            await ctx.send(f"❌ An error occurred: {e}", ephemeral=True)


    @bot.hybrid_command(name="gamemaster_edit", description="Add context to the gamemaster.")
    @app_commands.describe(
        context="Context to add.")
    @commands.has_role("Game Master")
    async def gamemaster_edit(ctx, context):
        rp_sessions = load_rp_sessions()
        channel_id = ctx.channel.id
        if rp_sessions[channel_id] != ():
            history = rp_sessions[channel_id][1]
            updated_context = f"Updated Context: {context}"
            history.append(types.Content(
                role='user',
                parts=[types.Part.from_text(text=updated_context)]
            ))
            rp_sessions[channel_id] = (rp_sessions[channel_id][0], history)

            save_rp_sessions(rp_sessions)
            await ctx.send("✅ Context updated successfully.", ephemeral=True)
        else:
            await ctx.send("❌ The game master is not active for this channel.", ephemeral=True)


    @bot.hybrid_command(name="gamemaster_continue", description="Have the bot continue with another GM Message")
    async def gamemaster_continue(ctx):
        rp_sessions = load_rp_sessions()
        channel_id = ctx.channel.id
        await ctx.send("🔃 Continuing...", ephemeral=True)
        if rp_sessions[channel_id] != ():
            await gamemaster_chat(ctx)
        else:
            await ctx.send("❌ The game master is not active for this channel.", ephemeral=True)


    @bot.hybrid_command(name="gamemaster_location", description="Move Game master location")
    @app_commands.describe(channel="Hyperlink of #channel to move to", description="Description of the new location.")
    @commands.has_role("Game Master")
    async def gamemaster_location(ctx, channel, description):
        rp_sessions = load_rp_sessions()
        current_channel_id = ctx.channel.id

        try:
            fnew_channel_id = int(channel.replace("<","").replace(">","").replace("#",""))
        except:
            await ctx.send("❌ Invalid channel was provided. Make sure it is the actual blue channel link. Example: <#>1099899000729128960", ephemeral=True)
            return

        if current_channel_id in rp_sessions:
            if fnew_channel_id in rp_sessions:
                await ctx.send("❌ A game master session is in progress in that channel. Please select a different one.", ephemeral=True)
            else:
                channel_webhook = await check_and_create_webhook(fnew_channel_id)
                rp_sessions[fnew_channel_id] = rp_sessions.pop(current_channel_id)
                save_rp_sessions(rp_sessions)
                await ctx.send(f"✅ Location changed to <#{fnew_channel_id}>", ephemeral=True)
                await gamemaster_chat(ctx, new_channel=fnew_channel_id, new_channel_msg=description)
        else:
            await ctx.send("❌ There is no active game master session in this channel.", ephemeral=True)


    @bot.tree.command(name="gamemaster_sessions",
                      description="Show all Game Master sessions in progress")
    @commands.has_role("Game Master")
    async def gamemaster_sessions(interaction):
        rp_sessions = load_rp_sessions()
        embed_desc = ""
        for channel in rp_sessions:
            if rp_sessions[channel]:
                embed_desc += f"**On** <#{channel}>: {rp_sessions[channel][0]['character'][:10]}\n\n"
        embed = discord.Embed(
            colour=discord.Colour.from_rgb(0, 255, 0),
            title=f"✅ Showing All Active RP Sessions",
            description=embed_desc
        )
        embed.set_footer(text="Here are the ongoing Game Master sessions. To end a session, use /gamemaster_stop in the channel!")
        await interaction.response.send_message(embed=embed)

    class NewsReport(BaseModel):
        headline: str
        report: str

    async def news_report():
        prompt = (
            "You are the Holonet News, the primary news source for stories and events across the Star Wars galaxy. "
            "The year is 2BBY. Imperials rule, and small rebel cells are emerging. "
            "In a witty yet serious tone, generate five believable Star Wars news report. "
            "Avoid mentioning canon characters like Darth Vader. "
            "Prepend an emoji to the headline relevant to the topic. "
        )

        response = client.models.generate_content(
            model=MODEL,
            contents=["Generate Star Wars News Reports"],
            config=types.GenerateContentConfig(
                safety_settings=GM_SAFETY_SETTINGS,
                system_instruction=prompt,
                response_mime_type="application/json",
                response_schema=list[NewsReport]
            )
        )

        holonet_news: list[NewsReport] = response.parsed

        embed = {
            "title": "Holonet News Report",
            "description": "Latest updates from across the galaxy:",
            "color": 224767,
            "fields": [],
            "image": {
                "url": "https://i.imgur.com/HbvWHt3.png"
            },
            "thumbnail": {
                "url": "https://static.wikia.nocookie.net/starwars/images/9/91/Bettiebotvj.png/revision/latest/thumbnail/width/360/height/360?cb=20200420000222"
            }
        }

        for report in holonet_news:
            headline = report.headline
            description = report.report
            embed["fields"].append({
                "name": headline.strip(),
                "value": description.strip(),
                "inline": False
            })
            embed["fields"].append({
                "name": "\u200b",
                "value": "\u200b",
                "inline": False
            })

        URL = "https://discord.com/api/webhooks/1366335187729776721/V2cqAT5Z9JiEH7YKKNThgBLl6dF-370ijaZ9z6ajE8QUhxKE5ASxibveYpj6zMpofmDi"
        async with aiohttp.ClientSession() as session:
            webhook_data = {
                'embeds': [embed]
            }
            async with session.post(URL, json=webhook_data) as response:
                if response.status != 204:
                    print(f'Failed to send embed: {response.status}')


    bot.run(os.getenv('TOKEN'))