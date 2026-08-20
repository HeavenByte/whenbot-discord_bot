import discord
from discord.ext import commands
import random
import asyncio
from datetime import datetime, timedelta

class DungeonSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cooldown_minutes = 30  

    @commands.command(name="dungeon", aliases=["adventure", "petualang"])
    async def enter_dungeon(self, ctx):
        """Masuk ke Raid Dungeon memanfaatkan efek stats dari kartu gacha Anda!"""
        if not ctx.guild: return

        now = datetime.now()
        raw_cooldown_data = await asyncio.to_thread(self.bot.db.check_dungeon_cooldown, ctx.guild.id, ctx.author.id)
        
        if raw_cooldown_data:
            last_time_str = raw_cooldown_data[0] if isinstance(raw_cooldown_data, tuple) else raw_cooldown_data
            
            if last_time_str:
                last_time = datetime.strptime(last_time_str, "%Y-%m-%d %H:%M:%S")
                if now < last_time + timedelta(minutes=self.cooldown_minutes):
                    sisa_waktu = (last_time + timedelta(minutes=self.cooldown_minutes)) - now
                    menit_sisa = round(sisa_waktu.total_seconds() / 60)
                    return await ctx.send(f"⏰ {ctx.author.mention}, Anda masih kelelahan! Tunggu **{menit_sisa} menit** lagi sebelum berpetualang.")


        user_inv = await asyncio.to_thread(self.bot.db.get_user_inventory, ctx.guild.id, ctx.author.id, "card")
        
        rare_count = sum(qty for _, rarity, qty, _ in user_inv if "RARE" in rarity) if user_inv else 0
        has_epic = any("EPIC" in rarity for _, rarity, _, _ in user_inv) if user_inv else False
        has_legendary = any("LEGENDARY" in rarity for _, rarity, _, _ in user_inv) if user_inv else False

        win_rate = min(0.90, 0.50 + (rare_count * 0.05))

        loading_msg = await ctx.send("⚔️ *Anda mulai menyusuri gua Dungeon bawah tanah... Menghadapi Raid Monster...*")
        
        is_victory = random.random() < win_rate
        
        await asyncio.to_thread(self.bot.db.update_dungeon_time, ctx.guild.id, ctx.author.id, now.strftime("%Y-%m-%d %H:%M:%S"))
        await loading_msg.delete()

        # 3. Proses Hasil Output Embed Pertempuran 🟢
        if is_victory:
            hadiah_koin = random.randint(3000, 7500)
            msg_jackpot = ""

            # Efek Kartu Legendary (Peluang critical 25% memicu koin 3x lipat)
            if has_legendary and random.random() < 0.25:
                hadiah_koin *= 3
                msg_jackpot = "💥 **JACKPOT CRITICAL! Kartu LEGENDARY memicu koin 3x lipat!**\n"

            await asyncio.to_thread(self.bot.db.update_balance, ctx.guild.id, ctx.author.id, hadiah_koin)
            
            embed = discord.Embed(
                title="🏰 Kemenangan Raid Dungeon!",
                description=f"{msg_jackpot}Anda berhasil menaklukkan monster bawah tanah!\nHadiah: 🪙 `{hadiah_koin:,}` Koin",
                color=discord.Color.green()
            )
            embed.add_field(name="Win Rate Anda", value=f"`{round(win_rate * 100)}%` (Bonus {rare_count}x Kartu RARE)", inline=True)
            await ctx.send(embed=embed)
        else:
            if has_epic:
                # Efek Kartu Epic (Proteksi anti denda koin jika kalah)
                embed = discord.Embed(
                    title="🛡️ Anda Kalah (Terproteksi!)",
                    description="Anda tumbang di tangan monster! Untungnya, efek **Kartu EPIC** melindungi dompet Anda dari denda rumah sakit.",
                    color=discord.Color.orange()
                )
                await ctx.send(embed=embed)
            else:
                denda = random.randint(1500, 3000)
                await asyncio.to_thread(self.bot.db.update_balance, ctx.guild.id, ctx.author.id, -denda)
                
                embed = discord.Embed(
                    title="💀 Anda Terkapar di Dungeon!",
                    description=f"Monster mencuri koin di dompet Anda sebesar 🪙 `{denda:,}` Koin saat Anda pingsan!",
                    color=discord.Color.red()
                )
                await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(DungeonSystem(bot))
