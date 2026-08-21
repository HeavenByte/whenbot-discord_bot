import discord
from discord.ext import commands
import random
import asyncio
import time

class MiningGameView(discord.ui.View):
    def __init__(self, ctx, cog_instance):
        super().__init__(timeout=60.0)
        self.ctx = ctx
        self.cog = cog_instance
        self.message = None
        
        # Stat penambangan sesi ini
        self.coins_earned = 0
        self.total_taps = 0
        self.pickaxe_level = 1
        self.upgrade_cost = 150
        self.last_tap_time = 0

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("❌ Ini area tambang milik orang lain! Ketik `+mining` untuk membuka tambang Anda sendiri.", ephemeral=True)
            return False
        return True

    def create_embed(self):
        max_taps_bonus = 20
        clamped_taps = self.total_taps % max_taps_bonus
        progress_bar = "🟩" * (clamped_taps // 2) + "⬛" * (10 - (clamped_taps // 2))

        embed = discord.Embed(
            title="⛏️ DEEP CORE MINING STATION",
            description=f"Halo {self.ctx.author.mention}, selamat datang di tambang bawah tanah!\n"
                        f"Ketuk tombol **⛏️ TAP MINING** di bawah ini berulang kali untuk mengumpulkan koin!",
            color=0xffaa00
        )
        
        embed.add_field(name="💰 Koin Didapat (Sesi Ini)", value=f"```🎰 {self.coins_earned} Koin```", inline=True)
        embed.add_field(name="🛠️ Level Pickaxe", value=f"```⚡ Lvl {self.pickaxe_level} (+{self.pickaxe_level}x Coin)```", inline=True)
        embed.add_field(name="📊 Total Ketukan", value=f"```🎯 {self.total_taps} Taps```", inline=False)
        embed.add_field(name="🎁 Progress Jackpot Tambang", value=f"```\n{progress_bar} [{clamped_taps}/{max_taps_bonus}]\n```", inline=False)
        
        embed.set_thumbnail(url="https://giphy.com")
        embed.set_footer(text="Sesi tambang otomatis ditutup jika idle selama 60 detik.")
        return embed

    @discord.ui.button(label="⛏️ TAP MINING!", style=discord.ButtonStyle.success, row=0)
    async def tap_mining(self, interaction: discord.Interaction, button: discord.ui.Button):
        current_time = time.time()
        
        if current_time - self.last_tap_time < 0.2:
            return await interaction.response.send_message("⚠️ **Sistem Keamanan:** Deteksi ketukan terlalu cepat! Santai saja mentambangnya.", ephemeral=True)
        
        self.last_tap_time = current_time
        self.total_taps += 1
        
        base_coin = random.randint(3, 8)
        earned = base_coin * self.pickaxe_level
        
        bonus_text = ""
        if self.total_taps % 20 == 0:
            jackpot = random.randint(50, 150)
            earned += jackpot
            bonus_text = f"\n🎉 **JACKPOT!** Anda menemukan bongkahan berlian: **+{jackpot} Koin!**"

        self.coins_earned += earned

        # 🔥 DIKUNCI: Menggunakan update_balance sesuai skrip sqlite3 Anda
        await asyncio.to_thread(self.cog.bot.db.update_balance, interaction.guild.id, interaction.user.id, earned)

        await interaction.response.edit_message(content=bonus_text, embed=self.create_embed(), view=self)

    @discord.ui.button(label="🔧 Upgrade Pickaxe (💰 150)", style=discord.ButtonStyle.primary, row=0)
    async def upgrade_pickaxe(self, interaction: discord.Interaction, button: discord.ui.Button):
        # 🔥 DIKUNCI: Menggunakan get_balance & update_balance sesuai skrip sqlite3 Anda
        user_balance = await asyncio.to_thread(self.cog.bot.db.get_balance, interaction.guild.id, interaction.user.id)
        
        if user_balance < self.upgrade_cost:
            return await interaction.response.send_message(f"❌ Koin Anda tidak cukup! Butuh **💰 {self.upgrade_cost} Koin** untuk upgrade.", ephemeral=True)
            
        await asyncio.to_thread(self.cog.bot.db.update_balance, interaction.guild.id, interaction.user.id, -self.upgrade_cost)
        
        self.pickaxe_level += 1
        self.upgrade_cost = int(self.upgrade_cost * 1.8)
        button.label = f"🔧 Upgrade Pickaxe (💰 {self.upgrade_cost})"
        
        await interaction.response.edit_message(content="⚡ **Upgrade Berhasil!** Daya hancur ketukan tambang Anda meningkat!", embed=self.create_embed(), view=self)

    @discord.ui.button(label="🛑 Keluar Tambang", style=discord.ButtonStyle.danger, row=1)
    async def exit_mining(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content=f"🏁 **Sesi Tambang Selesai!** Anda membawa pulang total **💰 {self.coins_earned} Koin** ke dompet database.", embed=None, view=None)
        self.stop()

    async def on_timeout(self):
        try:
            if self.message:
                await self.message.edit(content=f"💤 **Sesi Tambang Berakhir (Idle):** Total koin terkumpul **💰 {self.coins_earned} Koin** telah aman tersimpan di bank.", embed=None, view=None)
        except Exception:
            pass


class GachaMining(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="mining", aliases=["nambang", "tap", "clicker"])
    async def start_mining(self, ctx):
        """Membuka mini-game tambang interaktif tap-tap untuk mengumpulkan koin."""
        if not ctx.guild: return

        view = MiningGameView(ctx, self)
        embed = view.create_embed()
        
        msg = await ctx.send(embed=embed, view=view)
        view.message = msg

async def setup(bot):
    await bot.add_cog(GachaMining(bot))
