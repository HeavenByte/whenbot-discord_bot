import discord
from discord.ext import commands
import random
import asyncio  # 🟢 Required for thread delegation handling

class EconomyCore(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="balance", aliases=["bal", "koin", "dompet"])
    async def check_balance(self, ctx, member: discord.Member = None):
        """Mengecek saldo koin sendiri atau orang lain."""
        if not ctx.guild: return
        
        target = member or ctx.author

        # 🟢 Offload blocking query to background thread pool
        saldo = await asyncio.to_thread(self.bot.db.get_balance, ctx.guild.id, target.id)

        embed = discord.Embed(
            title=f"💰 Dompet {target.display_name}",
            description=f"Berikut adalah isi kantong Anda di server **{ctx.guild.name}**:",
            color=discord.Color.gold()
        )
        embed.add_field(name="Saldo Tunai", value=f"🪙 `{saldo:,}` Koin", inline=False)
        embed.set_thumbnail(url=target.display_avatar.url)
        await ctx.send(embed=embed)

    @commands.command(name="beg", aliases=["minta"])
    @commands.cooldown(1, 30, commands.BucketType.user) # Cooldown 30 detik
    async def beg_coin(self, ctx):
        if not ctx.guild: return

        koin_gratis = random.randint(10, 100)
   
        # 🟢 Offload blocking database write to prevent gateway heartbeat blocks
        await asyncio.to_thread(self.bot.db.update_balance, ctx.guild.id, ctx.author.id, koin_gratis)

        await ctx.send(f"💸 {ctx.author.mention} baru saja mengemis dan diberi koin sebesar 🪙 `{koin_gratis}` koin!")

    @beg_coin.error
    async def beg_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"⏰ Jangan serakah! Mengemis lagi dalam `{round(error.retry_after)}` detik.", delete_after=5)

    @commands.command(name="leaderboard", aliases=["lb", "top"])
    async def economy_leaderboard(self, ctx):
        """Menampilkan daftar 10 orang terkaya di server saat ini."""
        if not ctx.guild: return

        # 🟢 Offload blocking leaderboard aggregation query to background thread
        top_users = await asyncio.to_thread(self.bot.db.get_top_economy, ctx.guild.id, limit=10)

        if not top_users:
            return await ctx.send("📢 Belum ada data ekonomi di server ini.")

        # Tampilkan animasi loading singkat karena proses fetch membutuhkan waktu milidetik
        loading_msg = await ctx.send("⏳ Menyusun peringkat konglomerat server...")

        embed = discord.Embed(
            title=f"🏆 LEADERBOARD KOIN - {ctx.guild.name.upper()}",
            color=discord.Color.gold()
        )
        
        leaderboard_text = ""
        
        for index, row in enumerate(top_users, start=1):
            user_id = int(row[0])
            saldo = int(row[1])

            # Cek cache dulu, kalau gagal langsung tembak fetch API
            member = ctx.guild.get_member(user_id)
            if not member:
                try:
                    member = await ctx.guild.fetch_member(user_id)
                except discord.NotFound:
                    member = None # User benar-benar sudah left/keluar dari server

            nama_user = member.display_name if member else f"Mantan Member ({user_id})"

            # Berikan penanda medali podium unik
            if index == 1:
                medal = "🥇 "
            elif index == 2:
                medal = "🥈 "
            elif index == 3:
                medal = "🥉 "
            else:
                medal = f"`#{index}` "

            leaderboard_text += f"{medal} **{nama_user}** — 🪙 `{saldo:,}`\n"

        embed.description = f"Daftar pengguna dengan koin terbanyak:\n\n{leaderboard_text}"
        embed.set_thumbnail(url=ctx.guild.icon.url if ctx.guild.icon else self.bot.user.display_avatar.url)
        embed.set_footer(text=f"Diminta oleh {ctx.author.name}", icon_url=ctx.author.display_avatar.url)

        # Hapus pesan loading, lalu kirim embed asli yang sudah matang namanya
        await loading_msg.delete()
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(EconomyCore(bot))
