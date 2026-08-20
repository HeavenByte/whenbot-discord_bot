import discord
from discord.ext import commands
import time

class PingCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="ping")
    async def ping(self, ctx):
        api_latency = round(self.bot.latency * 1000)

        start_time = time.time()
        message = await ctx.send("Menghitung latensi...")
        end_time = time.time()
        bot_latency = round((end_time - start_time) * 1000)
        await message.delete()

        embed = discord.Embed(
            title="🏓 Pong!",
            description="Status koneksi dan latensi bot saat ini.",
            color=discord.Color.green() 
        )
        
        embed.add_field(name="Bot Latency", value=f"🟢 `{bot_latency}ms`", inline=True)
        embed.add_field(name="API Latency", value=f"🔵 `{api_latency}ms`", inline=True)
        
        embed.set_footer(text=f"Diminta oleh {ctx.author.name}", icon_url=ctx.author.display_avatar.url)

        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(PingCog(bot))
