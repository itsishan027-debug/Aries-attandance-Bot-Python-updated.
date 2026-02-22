import discord
from discord.ext import commands
import random
from datetime import datetime, timezone
import os
import psutil
from flask import Flask
from threading import Thread

# --- RENDER KEEP-ALIVE (Crash Proofing) ---
app = Flask('')
@app.route('/')
def home():
    return "Aries Bot: Titan System Online 🛡️"

def run_flask():
    try: app.run(host='0.0.0.0', port=8080)
    except Exception as e: print(f"Flask Error: {e}")

def keep_alive():
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()

# --- BOT CONFIGURATION ---
TOKEN = os.getenv("DISCORD_TOKEN") 
APP_ID = os.getenv("APPLICATION_ID")
TARGET_SERVER_ID = 770004215678369883
TARGET_CHANNEL_ID = 1426247870495068343
LEADER_ROLE_ID = 1412430417578954983 

class AriesBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True 
        super().__init__(
            command_prefix="!", 
            intents=intents, 
            application_id=APP_ID,
            reconnect=True
        )
        self.active_sessions = {}
        self.start_time = datetime.now(timezone.utc)

bot = AriesBot()

# --- DIAGNOSTICS HELPER ---
def get_bot_uptime():
    delta = datetime.now(timezone.utc) - bot.start_time
    hours, remainder = divmod(int(delta.total_seconds()), 3600)
    minutes, _ = divmod(remainder, 60)
    return f"{hours}h {minutes}m"

# --- COMMANDS ---
@bot.command()
@commands.has_permissions(administrator=True)
async def status(ctx):
    latency = round(bot.latency * 1000)
    try:
        memory = psutil.Process(os.getpid()).memory_info().rss / 1024**2
    except:
        memory = 0.0
    
    embed = discord.Embed(title="⚙️ Aries Self-Diagnostic", color=0x3498db)
    embed.add_field(name="📡 Latency", value=f"`{latency}ms`", inline=True)
    embed.add_field(name="⏳ Uptime", value=f"`{get_bot_uptime()}`", inline=True)
    embed.add_field(name="💾 RAM", value=f"`{memory:.1f}MB`", inline=True)
    embed.add_field(name="🛡️ Protection", value="`MAX (Auto-Heal Enabled)`", inline=False)
    await ctx.send(embed=embed)

# --- MAIN ENGINE (Attendance + Greetings) ---
@bot.event
async def on_message(message):
    try:
        if message.author == bot.user: return
        # Command processing sabse pehle taaki status command chal sake
        await bot.process_commands(message)
        
        # Core Attendance Logic
        if message.guild is None or message.guild.id != TARGET_SERVER_ID: return
        if message.channel.id != TARGET_CHANNEL_ID: return

        content = message.content.lower().strip()
        user = message.author
        now = datetime.now(timezone.utc)
        timestamp = int(now.timestamp())
        is_leader = any(role.id == LEADER_ROLE_ID for role in user.roles)

        # --- ONLINE ---
        if content == "online":
            try: await message.delete()
            except: pass

            if user.id not in bot.active_sessions:
                bot.active_sessions[user.id] = now
                
                if is_leader:
                    greeting = f"🛡️ **Order is restored. Leader {user.display_name} is watching.**"
                    msg_color = 0xf1c40f
                else:
                    greeting = f"✅ **{user.display_name}** has started their session."
                    msg_color = 0x2ecc71

                embed = discord.Embed(title="Status: ONLINE", description=greeting, color=msg_color)
                # Avatar check to avoid crash if user has no avatar
                if user.display_avatar:
                    embed.set_author(name=user.display_name, icon_url=user.display_avatar.url)
                    embed.set_thumbnail(url=user.display_avatar.url)
                
                embed.add_field(name="Arrival", value=f"🕒 <t:{timestamp}:t>")
                await message.channel.send(embed=embed)
            else:
                await message.channel.send(f"⚠️ {user.mention}, already online!", delete_after=3)

        # --- OFFLINE ---
        elif content == "offline":
            try: await message.delete()
            except: pass

            if user.id in bot.active_sessions:
                start_time = bot.active_sessions[user.id]
                duration = now - start_time
                
                # --- LEADER CUSTOM MESSAGE ---
                if is_leader:
                    status_msg = f"Leader **{user.display_name}** is offline — <@&1018171797126004827> take charge, **ARIES Citizen** stay active, track the leaderboard, and hold our clan position."
                    msg_color = 0x2f3136
                else:
                    status_msg = f"🔴 **{user.display_name}** session ended."
                    msg_color = 0xe74c3c

                hours, remainder = divmod(int(duration.total_seconds()), 3600)
                minutes, _ = divmod(remainder, 60)
                duration_str = f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"

                embed = discord.Embed(title="Status: OFFLINE", description=status_msg, color=msg_color)
                if user.display_avatar:
                    embed.set_author(name=user.display_name, icon_url=user.display_avatar.url)
                
                embed.add_field(name="Logged In", value=f"🕒 <t:{int(start_time.timestamp())}:t>", inline=True)
                embed.add_field(name="Logged Out", value=f"🕒 <t:{timestamp}:t>", inline=True)
                embed.add_field(name="Total Session", value=f"⏳ `{duration_str}`", inline=False)
                
                await message.channel.send(embed=embed)
                del bot.active_sessions[user.id]
            else:
                await message.channel.send(f"❓ {user.mention}, you were not marked online.", delete_after=3)

    except Exception as e:
        print(f"Max Protection Log Error: {e}")

@bot.event
async def on_ready():
    print(f'✅ {bot.user} Deployment Successful!')

if __name__ == "__main__":
    keep_alive()
    if TOKEN:
        bot.run(TOKEN)
            
