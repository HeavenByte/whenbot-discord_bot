import discord
from discord.ext import commands
import random
import asyncio  # 🟢 WAJIB DI-IMPORT UNTUK THREAD DELEGATION

class EconomyFarming(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ==================== 1. PERINTAH WORK (SAFE FARMING) ====================
    @commands.command(name="work", aliases=["kerja"])
    @commands.cooldown(1, 600, commands.BucketType.user) # Cooldown 10 menit
    async def work_command(self, ctx):
        """Bekerja dengan aman untuk mendapatkan koin kustom."""
        if not ctx.guild: return

        jobs = [
            "Menjadi Kasir Minimarket", "Supir Taksi Online", "Penambang Bitcoin",
            "Content Creator", "Developer Bot Discord", "Koki Restoran", "Petani Tambak"
        ]
        job_terpilih = random.choice(jobs)
        koin_didapat = random.randint(200, 600)

        # 🟢 PERBAIKAN MUTLAK: Offload blocking database write ke background thread pool
        await asyncio.to_thread(
            self.bot.db.update_balance, 
            ctx.guild.id, 
            ctx.author.id, 
            koin_didapat
        )

        embed = discord.Embed(
            title="💼 Laporan Kerja",
            description=f"Anda bekerja sebagai **{job_terpilih}** dan digaji sebesar 🪙 `{koin_didapat:,}` koin!",
            color=discord.Color.green()
        )
        embed.set_footer(text=f"Pekerja: {ctx.author.name}")
        await ctx.send(embed=embed)

    # ==================== 2. PERINTAH CRIME (HIGH RISK FARMING) ====================
    @commands.command(name="crime", aliases=["kriminal"])
    @commands.cooldown(1, 1200, commands.BucketType.user) # Cooldown 20 menit
    async def crime_command(self, ctx):
        """Melakukan aksi kriminal. Hadiah besar tapi bisa didenda jika gagal."""
        if not ctx.guild: return

        sukses = random.random() < 0.6 

        if sukses:
            crimes_success = [
                "Membobol ATM tua", "Meretas situs judi online", 
                "Mencuri skuter listrik", "Menyelundupkan barang antik"
            ]
            aksi = random.choice(crimes_success)
            hadiah = random.randint(800, 2000)
            
            # 🟢 PERBAIKAN MUTLAK: Gunakan asyncio.to_thread untuk penambahan saldo
            await asyncio.to_thread(self.bot.db.update_balance, ctx.guild.id, ctx.author.id, hadiah)
            
            embed = discord.Embed(
                title="🥷 Kriminal Sukses!",
                description=f"Anda berhasil **{aksi}** dan meraup 🪙 `{hadiah:,}` koin hitam!",
                color=discord.Color.dark_green()
            )
        else:
            crimes_failed = [
                "Tertangkap basah mencuri jemuran", "Situs yang Anda retas melacak IP Anda",
                "Alarm berbunyi saat membobol toko", "Terpeleset saat dikejar satpam"
            ]
            aksi = random.choice(crimes_failed)
            denda = random.randint(400, 1000)
            
            # 🟢 PERBAIKAN MUTLAK: Gunakan asyncio.to_thread untuk pengurangan saldo (nilai denda minus)
            await asyncio.to_thread(self.bot.db.update_balance, ctx.guild.id, ctx.author.id, -denda)
            
            embed = discord.Embed(
                title="🚨 Aksi Digagalkan!",
                description=f"Anda gagal karena **{aksi}**! Polisi mendenda Anda sebesar 🪙 `{denda:,}` koin.",
                color=discord.Color.red()
            )
            
        embed.set_footer(text=f"Pelaku: {ctx.author.name}")
        await ctx.send(embed=embed)

    # ==================== HANDLER COOLDOWN GLOBAL ====================
    @work_command.error
    @crime_command.error
    async def farming_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            menit = round(error.retry_after / 60)
            detik = round(error.retry_after % 60)
            waktu_tunggu = f"{menit} menit {detik} detik" if menit > 0 else f"{detik} detik"
            
            await ctx.send(
                f"⏰ {ctx.author.mention}, Anda lelah! Istirahat dulu selama **{waktu_tunggu}** sebelum farming lagi.", 
                delete_after=7
            )

async def setup(bot):
    await bot.add_cog(EconomyFarming(bot))
