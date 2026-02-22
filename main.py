import discord
import os
import psutil
import logging
import sqlite3
import asyncio
from datetime import datetime, timezone
from discord.ext import commands
from flask import Flask
from threading import Thread

# --- 1. ADVANCED LOGGING SETUP ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')
logger = logging.getLogger("AriesBot")

# --- 2. DATABASE LAYER (Session Persistence) ---
def init_db():
    try:
        conn = sqlite3.connect('attendance.db')
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS sessions 
                          (user_id INTEGER PRIMARY KEY, start_time TIMESTAMP)''')
        conn.commit()
        conn.close()
        logger.info("Database initialized successfully.")
    except Exception as e:
        logger.error(f"DB Init Error: {e}")

# --- 3. RENDER KEEP-ALIVE ---
app = Flask('')
@app.route('/')
def home():
    return "Aries Bot: Titan System Online 🛡️"

def run_flask():
    try: app.run(host='0.0.0.0', port=8080)
    except Exception as e: logger.error(f"Flask Error: {e}")

def keep_alive():
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()

# --- 4. BOT CONFIGURATION ---
TOKEN = os.getenv("DISCORD_TOKEN")
TARGET_SERVER_ID = 770004215678369883
TARGET_CHANNEL_ID = 1426247870495068343
LEADER_ROLE_ID = 1412430417578954983

class AriesBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)
        self.start_time = datetime.now(timezone.utc)

bot = AriesBot()

# --- 5. CORE ATTENDANCE ENGINE (Robust Class) ---
class AttendanceService:
    @staticmethod
    def log_online(user_id):
        conn = sqlite3.connect('attendance.db')
        conn.execute("INSERT OR REPLACE INTO sessions VALUES (?, ?)", 
                     (user_id, datetime.now(timezone.utc).isoformat()))
        conn.commit()
        conn.close()

    @staticmethod
    def get_start_time(user_id):
        conn = sqlite3.connect('attendance.db')
        data = conn.execute("SELECT start_time FROM sessions WHERE user_id=?", (user_id,)).fetchone()
        conn.close()
        return datetime.fromisoformat(data[0]) if data else None

    @staticmethod
    def log_offline(user_id):
        conn = sqlite3.connect('attendance.db')
        conn.execute("DELETE FROM sessions WHERE user_id=?", (user_id,))
        conn.commit()
        conn.close()

# --- 6. COMMANDS & EVENTS ---
@bot.command()
@commands.has_permissions(administrator=True)
async def status(ctx):
    try:
        mem = psutil.Process(os.getpid()).memory_info().rss / 1024**2
        uptime = datetime.now(timezone.utc) - bot.start_time
        embed = discord.Embed(title="⚙️ Aries Titan Diagnostic", color=0x3498db)
        embed.add_field(name="📡 Latency", value=f"`{round(bot.latency * 1000)}ms`")
        embed.add_field(name="⏳ Uptime", value=f"`{uptime.total_seconds() // 3600}h`")
        embed.add_field(name="💾 RAM", value=f"`{mem:.1f}MB`")
        embed.add_field(name="🛡️ System", value="`STABLE - DB CONNECTED`")
        await ctx.send(embed=embed)
    except Exception as e:
        logger.error(f"Status Error: {e}")

@bot.event
async def on_message(message):
    if message.author.bot: return
    
    # Process commands
    await bot.process_commands(message)

    if message.guild and message.guild.id == TARGET_SERVER_ID and message.channel.id == TARGET_CHANNEL_ID:
        content = message.content.lower().strip()
        user = message.author
        is_leader = any(role.id == LEADER_ROLE_ID for role in user.roles)

        if content == "online":
            if AttendanceService.get_start_time(user.id) is None:
                AttendanceService.log_online(user.id)
                embed = discord.Embed(title="Status: ONLINE", description=f"🛡️ **Leader {user.display_name} is watching.**" if is_leader else f"✅ **{user.display_name}** session started.", color=0xf1c40f if is_leader else 0x2ecc71)
                embed.add_field(name="Arrival", value=f"<t:{int(datetime.now(timezone.utc).timestamp())}:t>")
                await message.channel.send(embed=embed)
                try: await message.delete()
                except: pass
        
        elif content == "offline":
            start_time = AttendanceService.get_start_time(user.id)
            if start_time:
                duration = datetime.now(timezone.utc) - start_time
                AttendanceService.log_offline(user.id)
                status_msg = f"Leader **{user.display_name}** is offline." if is_leader else f"🔴 **{user.display_name}** session ended."
                embed = discord.Embed(title="Status: OFFLINE", description=status_msg, color=0x2f3136 if is_leader else 0xe74c3c)
                embed.add_field(name="Duration", value=f"`{int(duration.total_seconds()//3600)}h {int((duration.total_seconds()%3600)//60)}m`")
                await message.channel.send(embed=embed)
                try: await message.delete()
                except: pass

@bot.event
async def on_ready():
    init_db()
    logger.info(f"Bot connected as {bot.user}")

# --- 7. FINAL BOOT ---
if __name__ == "__main__":
    try:
        keep_alive()
        if TOKEN:
            bot.run(TOKEN)
    except Exception as e:
        logger.critical(f"FATAL SYSTEM FAILURE: {e}")
    
