# This code ಠ_ಠ fml
import re
from datetime import datetime, timedelta
import datetime
from nptime import nptime
from discord.ext import tasks
from discord.ext import commands
import os
from dotenv import load_dotenv
load_dotenv()

from dbscript import Connection
connection = Connection()

from timezones import get_time, utc_to_local

#connection.new_record("769598266173030470", 0, datetime.time(5,0), "bst")

bot = commands.Bot(command_prefix="$")
cooldown = []

def timenow(timezone):
    return utc_to_local(datetime.datetime.utcnow().time(), timezone)

def timenowutc():
    return datetime.datetime.utcnow().time()

def dtstring(time):
    newtime = str(time).split(":")
    return newtime[0]+":"+newtime[1]

def strdatetime(time):
    newtime = time.split(":")
    return datetime.time(int(newtime[0]),int(newtime[1]))

#Tasks
@tasks.loop(hours=1)
async def get_active_times():
    channel = bot.get_channel(int(os.getenv("CHANNELID")))
    active_list = connection.get_active_users()
    for user in active_list:
        date_time_obj = datetime.datetime.strptime(user[1], '%Y-%m-%d %H:%M:%S.%f')
        if date_time_obj + timedelta(days=1) < datetime.datetime.now():
            await channel.send(f"<@{user[0]}> You have ran out of time to wake up, reseting streak.")
            connection.remove_active(user[0])
            connection.reset_streak(user[0])

@tasks.loop(hours=12)
async def cooldown_loop():
    cooldown = []

#Commands
@bot.command()
async def up(ctx):
    global cooldown
    if ctx.channel.id != int(os.getenv('CHANNELID')):
        return
    strid = str(ctx.message.author.id)
    if strid not in connection.get_ids():
        await ctx.channel.send(f"{ctx.message.author.mention} You have not set a time, to do so, please say $setup <time>")
        return
    if strid in cooldown:
        await ctx.channel.send(f"{ctx.message.author.mention} You have already woken up today!")
        return
    cooldown.append(strid)
    user = connection.get_user(strid)
    goal = utc_to_local(user[3], user[2])
    current = utc_to_local(user[4], user[2])
    if strid in connection.get_active_ids():
        connection.update_active(strid, datetime.datetime.now())
    else:
        connection.add_to_active(strid, datetime.datetime.now())

    if nptime.from_time(timenow(user[2])) - timedelta(minutes=15) <= goal and nptime.from_time(timenow(user[2])) + timedelta(minutes=15) >= goal:
        await ctx.channel.send(f"{ctx.message.author.mention} Congrats, you have kept your time goal for {user[1]} days!")
        connection.update_current(strid, get_time(goal, user[2]))
        connection.increment_streak(strid)
        return
    if timenow(user[2]) <= current and timenow(user[2]) > goal:
        new_current = nptime.from_time(timenow(user[2])) - timedelta(minutes=15)
        await ctx.channel.send(f"{ctx.message.author.mention} Congrats, you beat your target time of {dtstring(current)}, your new target is {dtstring(new_current)}")
        connection.update_current(strid, get_time(new_current, user[2]))
    elif timenow(user[2]) > current:
        await ctx.channel.send(f"{ctx.message.author.mention} Your missed your target of {dtstring(current)}, your new target is {dtstring(timenow(user[2]))}")
        connection.update_current(strid, timenowutc())
    else:
        await ctx.channel.send(f"You have woken up for your target goal of {dtstring(goal)} too early. Either that or the bot is bugged idk.")
    connection.reset_streak(strid)
    return

@bot.command()
async def setup(ctx, goal=None, timezone=None):
    if ctx.channel.id != int(os.getenv('CHANNELID')):
        return
    if str(ctx.message.author.id) in connection.get_ids():
        await ctx.channel.send(f"{ctx.message.author.mention} You have already setup your sleeping. To reset, use $reset (this will reset your streak as well).")
    elif goal == None or timezone == None:
        await ctx.channel.send(f"{ctx.message.author.mention} Please input parameters, the command should look like this $setup <timegoal HH:MM> <timezone (relative to UTC) [+-]HH:MM>")
    elif not re.match(r"[0-9][0-9]:[0-9][0-9]", goal):
        await ctx.channel.send(f"{ctx.message.author.mention} Time format does not match, please use HH:MM (for example 05:00 is 5am)")
    elif isinstance(timezone, str):
        if not re.match(r"[+-][0-9][0-9]:[0-9][0-9]", timezone):
            await ctx.channel.send(f"{ctx.message.author.mention} Your timezone is not valid, please use the timezone format (relative to UTC) [+-]HH:MM")
            return
        sign = timezone[0]
        timezone = int(timezone[1:3]) + (int(timezone[4:6])/60)
        if sign == "-":
            timezone = 24 - timezone
        format_time = get_time(goal, timezone)
        connection.new_record(str(ctx.message.author.id), 0, format_time, timezone)
        await ctx.channel.send(f"{ctx.message.author.mention} Your time has been set!")
    return

@bot.command()
async def reset(ctx):
    if ctx.channel.id != int(os.getenv('CHANNELID')):
        return
    if str(ctx.message.author.id) not in connection.get_ids():
        await ctx.channel.send(f"{ctx.message.author.mention} You are not found in the database, to setup please say $setup <timegoal> <timezone>")
        return
    connection.delete_user(str(ctx.message.author.id))
    await ctx.channel.send(f"{ctx.message.author.mention} Reset user, please now use $setup")

@bot.command()
async def leaderboard(ctx):
    if ctx.channel.id != int(os.getenv('CHANNELID')):
        return
    text = f"{ctx.message.author.mention} Top active streaks:\n"
    leaderboard = connection.get_leaderboard()
    for user in leaderboard:
        username = await bot.fetch_user(int(user[0]))
        text += f"{username}: {user[1]} days\n"
    await ctx.channel.send(f"{text}")

@bot.command()
async def mystats(ctx):
    if ctx.channel.id != int(os.getenv('CHANNELID')):
        return
    if str(ctx.message.author.id) not in connection.get_ids():
        await ctx.channel.send(f"{ctx.message.author.mention} You are not found in the database, to setup please say $setup <timegoal> <timezone>")
        return
    user = connection.get_user(str(ctx.message.author.id))
    goal = utc_to_local(user[3], user[2])
    current = utc_to_local(user[4], user[2])
    text = f"{ctx.message.author.mention} Goal: {dtstring(goal)}, current wake up time: {dtstring(current)}, current streak: {user[1]} (timezone: {user[2]})"
    await ctx.channel.send(text)

#Tests
# @bot.command()
# async def whattime(ctx, time, timezone):
#     await ctx.channel.send(utc_to_local(time, timezone.upper()))

@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user.name}')
    get_active_times.start()

# @tasks.loop(seconds=60)
# async def is_awake():
#     global awake
#     global streak

#     channel = client.get_channel(int(os.getenv('CHANNELID')))  # notification channel
#     time_now = datetime.datetime.now().time()
#     if time_now > datetime.time(4,25) and time_now < datetime.time(4,35):
#         await channel.send(f'It is 5:30am in the UK, and <@{os.getenv("USERID")}> has 15 minutes to wake up.')
#         await asyncio.sleep(900)
#         if not awake:
#             await channel.send(f'<@{os.getenv("USERID")}> Michael did not wake up, streak restarting')
#             streak = 0
#         else:
#             streak += 1
#             await channel.send(f'<@{os.getenv("USERID")}> has woke up at 5am for {streak} days in a row! Jeez what a pro')
#     time_now = datetime.datetime.now().time()
#     awake = False
#     return

bot.run(os.getenv('TOKEN'))

