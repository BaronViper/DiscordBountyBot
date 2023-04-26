import responses
import discord
import asyncio
from discord import app_commands
from discord.ext import commands, tasks
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String
import dotenv
import os

dotenv.load_dotenv()

Base = declarative_base()


class Missions(Base):
    __tablename__ = "missions"
    id = Column(Integer, primary_key=True)
    title = Column(String)
    description = Column(String)
    reward = Column(Integer)
    difficulty = Column(String)


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
        await bot.tree.sync()
        await change_status()
        print(f"{bot.user} online")

    @bot.hybrid_command(name="help", description="Shows R0-U41's help menu")
    async def help(ctx):
        embed = discord.Embed(
            colour=discord.Colour.from_rgb(0, 0, 0),
            title="Help Menu"
        )
        embed.add_field(name="Add mission",
                        value="`Only available to @Game Master`\n Run /add_mission (preferred) or >add_mission to add a new mission. If running >add_mission, the command takes in four inputs separated by spaces (title, description, reward, difficulty- Very Easy, Easy, Medium, Hard, Very Hard, Expert).\n\n Example Command: >add_mission 'Destroy Rebel Base' 'A big rebel base on Kuwait' '200' 'Easy'\n")
        embed.add_field(name="Add bounty",
                        value="Run /add_bounty (preferred) or >add_bounty to add a new bounty. If running >add_mission, the command takes in four inputs separated by spaces (title, description, reward.\n\n Example Command: >add_bounty 'Jabba' 'I don't like him. I heard he's chilling in his palace on Tatooine.' '300'\n")
        embed.add_field(name="Delete mission",
                        value="`Only available to @Game Master`\n Run /delete_mission (preferred) or >delete_mission to delete a mission. If running >delete_mission, the command takes in one input (mission_id).\n\n Example Command: >delete_mission 2\n")
        embed.add_field(name="Delete bounty",
                        value="`Only available to @Game Master`\n Run /delete_bounty (preferred) or >delete_bounty to delete a bounty. If running >delete_bounty, the command takes in one input (bounty_id).\n\n Example Command: >delete_bounty 2\n")
        embed.add_field(name="Show missions",
                        value="Run /all_missions (preferred) or >all_missions to show available missions.\n")
        embed.add_field(name="Show bounties",
                        value="Run /all_bounties (preferred) or >all_bounties to show available bounties.")
        embed.set_footer(text="Built by BaronViper#8694")

        await ctx.send(embed=embed)

    @bot.hybrid_command(name="add_mission", description='Adds a new mission')
    @commands.has_role("Game Master")
    @app_commands.describe(title="Title of mission", description="Job description",
                           reward="How much is earned upon completion?",
                           difficulty="Choose: Very Easy, Easy, Medium, Hard, Very Hard, Expert.")
    async def add_mission(ctx, title: str, description: str, reward: int, difficulty: str):
        embed = discord.Embed(colour=discord.Colour.from_rgb(0, 0, 0),
                              title=f"Confirm Mission Details",
                              description=f"**Title:** {title.title()}\n\n **Difficulty:** {difficulty.title()}\n\n **Reward:** <:credits:1099938341467738122>{reward:,}\n\n **Description:** {description}")
        embed.set_footer(text="✅ to confirm, or ❌ to cancel.")

        bot_response = await ctx.send(embed=embed)

        await bot_response.add_reaction("✅")
        await bot_response.add_reaction("❌")

        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in ["✅", "❌"] and reaction.message == bot_response

        try:
            reaction, user = await bot.wait_for('reaction_add', timeout=60.0, check=check)
            if str(reaction.emoji) == "✅":
                if len(session.query(Missions).all()) == 10:
                    await ctx.send("Error. Too many missions already listed. Maximum of 10 only.")
                else:
                    new_mission = Missions(
                        title=title.title(),
                        description=description,
                        reward=reward,
                        difficulty=difficulty.title()
                    )
                    session.add(new_mission)
                    session.commit()
                    await ctx.send("Confirmed! Mission added.")

            elif str(reaction.emoji) == "❌":
                await ctx.send("Canceled request.")

        except asyncio.TimeoutError:
            await ctx.send("Confirmation timed out.")

    @bot.hybrid_command(name="add_bounty", description='Adds a new bounty')
    @commands.has_role("Member")
    @app_commands.describe(target="Who does the bounty target?", description="Bounty description or additional notes?",
                           reward="How much will you pay upon completion?")
    async def add_bounty(ctx, target: str, description: str, reward: int):
        embed = discord.Embed(
            colour=discord.Colour.from_rgb(0, 0, 0),
            title="Confirm Bounty Details",
            description=f"**Target:** {target}\n\n **Reward:** <:credits:1099938341467738122>{reward:,}\n\n **Client:** {ctx.author}\n\n **Description:** {description}"
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

    @bot.hybrid_command(name="all_missions", description="Shows all available missions.")
    async def all_missions(ctx):
        missions = session.query(Missions).all()
        embed_description = ""
        for mission in missions:
            embed_description += f"\n\n**<:credits:1099938341467738122>{mission.reward:,} - ID: {missions.index(mission) + 1} - {mission.title} - {mission.difficulty}**\n {mission.description}"
        embed = discord.Embed(
            colour=discord.Colour.from_rgb(0, 0, 0),
            title="=== Mission Board ===",
            description=embed_description
        )
        await ctx.send(embed=embed)

    @bot.hybrid_command(name="all_bounties", description="Shows all available bounties.")
    async def all_bounties(ctx):
        bounties = session.query(Bounties).all()
        embed_description = ""
        for bounty in bounties:
            embed_description += f"\n\n**<:credits:1099938341467738122>{bounty.reward:,} - ID: {bounties.index(bounty) + 1} - {bounty.target}**\n `From {bounty.client}`\n {bounty.description}"
        embed = discord.Embed(
            colour=discord.Colour.from_rgb(0, 0, 0),
            title="=== Bounty Board ===",
            description=embed_description
        )
        await ctx.send(embed=embed)

    @bot.hybrid_command(name="mission_info", description="Show info for specified mission ID (1-10).")
    @app_commands.describe(m_id="ID of mission")
    async def mission_info(ctx, m_id: int):
        if m_id not in range(1, 11):
            await ctx.send("Invalid mission ID. Enter an ID number from 1-10")
        else:
            mission = session.query(Missions).all()[m_id - 1]
            embed = discord.Embed(
                colour=discord.Colour.from_rgb(0, 0, 0),
                title=f"=== Mission Info - ID: {m_id} ===",
                description=f"**<:credits:1099938341467738122>{mission.reward:,} - {mission.title} - {mission.difficulty}**\n {mission.description}"
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
                description=f"**<:credits:1099938341467738122>{bounty.reward:,} - {bounty.target}**\n `From {bounty.client}`\n {bounty.description}"
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
                description=f"**<:credits:1099938341467738122>{bounty.reward:,} - {bounty.target}**\n `From {bounty.client}`\n {bounty.description}"
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
    @app_commands.describe(m_id="ID of mission")
    async def delete_mission(ctx, m_id: int):
        if m_id not in range(1, 11):
            await ctx.send("Invalid mission ID. Enter an ID number from 1-10")
        else:
            mission = session.query(Missions).all()[m_id - 1]
            embed = discord.Embed(
                colour=discord.Colour.from_rgb(0, 0, 0),
                title=f"=== Delete Mission - ID: {m_id} ===",
                description=f"**<:credits:1099938341467738122>{mission.reward:,} - {mission.title} - {mission.difficulty}**\n {mission.description}"
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

    bot.run(os.getenv('TOKEN'))
