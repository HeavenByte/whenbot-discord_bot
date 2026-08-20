import discord
from discord.ext import commands
from utils.database import BotDatabase
import os
from dotenv import load_dotenv
load_dotenv()
TOKEN = os.getenv("TOKEN_CUY")

class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix=os.getenv("PREFIX"), intents=intents)
        self.db = BotDatabase()
    async def setup_hook(self):
         for root, dirs, files in os.walk("./cogs"):
              for filename in files:
                 if filename.endswith(".py"):
                    relative_path = os.path.relpath(os.path.join(root, filename))
                    cog_path = relative_path.replace(os.sep, ".").removesuffix(".py")  
                    await self.load_extension(cog_path)
                    print(f"✅ Berhasil memuat command: {cog_path}")
    async def on_ready(self):
        print(f'We have logged in as {bot.user}')

bot = MyBot()
bot.run(TOKEN)