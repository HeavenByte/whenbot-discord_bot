import discord
from discord.ext import commands
import asyncio
import io
import random
import aiohttp
from urllib.parse import urlparse


class DungeonBattleView(discord.ui.View):
    def __init__(self, ctx, cog_instance, enemies, passives):
        super().__init__(timeout=90.0)
        self.ctx, self.cog, self.enemies, self.current_stage = ctx, cog_instance, enemies, 0
        self.message, self.ended, self.player_hp, self.total_loot = None, False, 100, 0
        self.load_enemy(0)
        self.crit_chance = 0.15 + (0.05 * passives["rare_count"]) + (0.20 if passives["has_legendary"] else 0)
        self.has_shield = passives["has_epic"]
        self.coin_multiplier = 3 if passives["has_legendary"] else 1
        self.combat_logs = "⚔️ Gerbang Dungeon Terbuka! Hadapi kroco penjaga!"

    def clean_gif_url(self, url: str) -> str:
        """Pembersih Tautan: Memvalidasi & memperbaiki link Giphy/Tenor ke Direct File (.gif) yang aman."""
        if not url:
            return None
        url = url.strip()

        try:
            parsed = urlparse(url)
            if all([parsed.scheme, parsed.netloc]):
                return url
        except Exception:
            pass

        if "giphy.com" in url:
            try:
                slug = url.split("giphy.com", 1)[-1].lstrip("/")
                gif_id = slug.split("-")[-1] if "-" in slug else slug
                if "/" in gif_id:
                    gif_id = gif_id.split("/")[0]
                return f"https://media.giphy.com/media/{gif_id}/giphy.gif"
            except Exception:
                pass

        if "tenor.com" in url and not url.endswith(".gif"):
            return url + ".gif"

        return None

    def load_enemy(self, idx):
        """Memuat data statistik monster berdasarkan index stage pertarungan."""
        ed = self.enemies[idx]
        self.enemy_name, self.enemy_max_hp, self.enemy_hp = ed["name"], ed["hp"], ed["hp"]
        self.enemy_gif = self.clean_gif_url(ed["gif"])
        self.enemy_reward, self.is_boss = ed["reward"], ed["is_boss"]

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("❌ Anda tidak bisa mengontrol pertarungan dungeon ksatria lain!", ephemeral=True)
            return False
        return True

    def make_hp_bar(self, cur, max_v, emoji="🟥"):
        if cur <= 0:
            return "░░░░░░░░░░ [0/100%]"
        pct = max(1, int((cur / max_v) * 10))
        return f"{emoji * pct}{'░' * (10 - pct)} [{cur}/{max_v}]"

    async def build_battle_payload(self):
        """Menyiapkan embed + file gif musuh saat ini (gif diunduh & dilampirkan, bukan hotlink)."""
        st = "😈 STAGE 1: ANTEK KROCO" if not self.is_boss else "🚨 FINAL STAGE: LELUHUR BOSS"
        embed = discord.Embed(title=f"⚔️ DUNGEON RAID — {st}", color=0x2f3136 if not self.is_boss else 0xff3333)
        embed.add_field(name=f"👾 HP {self.enemy_name}", value=f"```\n{self.make_hp_bar(self.enemy_hp, self.enemy_max_hp, '🟥')}\n```", inline=False)
        embed.add_field(name=f"🛡️ HP Anda", value=f"```\n{self.make_hp_bar(self.player_hp, 100, '🟩')}\n```", inline=False)
        embed.add_field(name="📜 COMBAT LOGS", value=f"```md\n{self.combat_logs}\n```", inline=False)

        file = await self.cog.fetch_gif_file(self.enemy_gif)
        if file:
            embed.set_image(url=f"attachment://{file.filename}")

        embed.set_thumbnail(url=self.ctx.author.display_avatar.url)
        embed.set_footer(text=f"Total Harta Dijarah: 💰 {self.total_loot} Koin")
        return embed, file

    async def check_battle_end(self, inter):
        # NOTE: inter sudah di-defer() oleh caller sebelum method ini dipanggil,
        # jadi semua edit di sini WAJIB pakai edit_original_response (bukan response.edit_message).
        if self.enemy_hp <= 0:
            loot = int(self.enemy_reward * self.coin_multiplier)
            self.total_loot += loot
            if self.current_stage == 0:
                self.current_stage = 1
                self.load_enemy(1)
                self.player_hp = min(100, self.player_hp + 35)
                self.combat_logs = f"🎉 KROCO TUMBANG! +{loot} koin.\n💖 HP pulih +35!\n⚠️ WASPADA! {self.enemy_name} Telah Bangkit!"
                embed, file = await self.build_battle_payload()
                await inter.edit_original_response(embed=embed, attachments=[file] if file else [], view=self)
                return True
            else:
                self.ended = True
                await asyncio.to_thread(self.cog.bot.db.update_balance, inter.guild.id, self.ctx.author.id, self.total_loot)
                await inter.edit_original_response(content=f"🏆 **VICTORY CLEAR!** Membawa pulang `+ {self.total_loot} Koin`!", embed=None, attachments=[], view=None)
                self.stop()
                return True
        elif self.player_hp <= 0:
            self.ended = True
            denda = int(self.enemy_reward * 0.5)
            if self.has_shield:
                msg = f"💀 **DEFEAT!** Hancur dihajar {self.enemy_name}!\n🛡️ **SHIELD AKTIF:** Saldo aman!"
            else:
                await asyncio.to_thread(self.cog.bot.db.update_balance, inter.guild.id, self.ctx.author.id, -denda)
                msg = f"💀 **DEFEAT!** Tewas dibantai {self.enemy_name}!\n💸 **Denda:** Kehilangan `{denda} Koin`."
            await inter.edit_original_response(content=msg, embed=None, attachments=[], view=None)
            self.stop()
            return True
        return False

    @discord.ui.button(label="⚔️ SERANG MUSUH!", style=discord.ButtonStyle.danger)
    async def attack_button(self, inter: discord.Interaction, button: discord.ui.Button):
        if self.ended: return
        # 🟢 Ack duluan SEBELUM ada proses lambat (download gif) - wajib < 3 detik,
        # kalau tidak Discord invalidate token interaction-nya (Unknown interaction).
        await inter.response.defer()

        p_dmg = random.randint(15, 32) if self.is_boss else random.randint(25, 45)
        if random.random() < self.crit_chance:
            p_dmg = int(p_dmg * 2)
            log_p = f"[PLAYER]: 💥 CRITICAL! Menebas -{p_dmg} HP!"
        else:
            log_p = f"[PLAYER]: Melukai -{p_dmg} HP."
        self.enemy_hp = max(0, self.enemy_hp - p_dmg)
        if self.enemy_hp <= 0:
            if await self.check_battle_end(inter) and not self.ended: return
            return
        b_dmg = random.randint(15, 30) if self.is_boss else random.randint(8, 18)
        self.player_hp = max(0, self.player_hp - b_dmg)
        log_b = f"[MUSUH]: Membalas, mencabik Anda -{b_dmg} HP."
        self.combat_logs = f"{log_p}\n{log_b}"
        if await self.check_battle_end(inter): return
        embed, file = await self.build_battle_payload()
        await inter.edit_original_response(embed=embed, attachments=[file] if file else [], view=self)

    @discord.ui.button(label="🏃 Kabur", style=discord.ButtonStyle.secondary)
    async def flee_button(self, inter: discord.Interaction, button: discord.ui.Button):
        self.ended = True
        await inter.response.edit_message(content="🏳️ **Melarikan Diri!** Pertempuran dibatalkan.", embed=None, attachments=[], view=None)
        self.stop()


class GachaDungeon(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._session = None
        self._gif_cache = {}  # url -> raw bytes, biar gif yg sama nggak diunduh berulang

        self.kroco_pool = [
            {"name": "Goblin Kroco", "hp": 45, "reward": 50, "gif": "https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExYmxkeDVpdXo0ejFjd3Jyc3Zmamh5dTl4cGU1MmVwcmV1d2M4NjRzYyZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/fSMN4qTlIcOt6soROD/giphy.gif", "is_boss": False},
            {"name": "Wizard Goblin", "hp": 55, "reward": 65, "gif": "https://media2.giphy.com/media/v1.Y2lkPTc5MGI3NjExbTF0eXllbThrbXJkcGdpNWJ2azZxMjQ1aGl3ZW5tYjQxNzBkbmszcSZlcD12MV9naWZzX3JlbGF0ZWQmY3Q9Zw/bEtps2CTzR81LmT6pg/giphy.gif", "is_boss": False}
        ]
        self.boss_pool = [
            {"name": "Green Goblin Boss", "hp": 130, "reward": 250, "gif": "https://media3.giphy.com/media/v1.Y2lkPTc5MGI3NjExbTF0eXllbThrbXJkcGdpNWJ2azZxMjQ1aGl3ZW5tYjQxNzBkbmszcSZlcD12MV9naWZzX3JlbGF0ZWQmY3Q9Zw/9MYyY0y4CvBFaXwADV/giphy.gif", "is_boss": True},
            {"name": "Goblin Clash Boss", "hp": 160, "reward": 350, "gif": "https://media2.giphy.com/media/v1.Y2lkPTc5MGI3NjExbTF0eXllbThrbXJkcGdpNWJ2azZxMjQ1aGl3ZW5tYjQxNzBkbmszcSZlcD12MV9naWZzX3JlbGF0ZWQmY3Q9Zw/LBpSMh9WK7Ma3wsIm3/giphy.gif", "is_boss": True}
        ]
        self.intro_gif_pool = [
            "https://media4.giphy.com/media/v1.Y2lkPTc5MGI3NjExbnFyNGc3MGkzcnAwb3czenpwMWFyZmNnY3JpYXZvZ2FndHVqZjZpZiZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/x7Ul109L9TZvi5DxfA/giphy.gif",
            "https://media4.giphy.com/media/v1.Y2lkPTc5MGI3NjExODhoNDNxZHg0bWM5cjRxdDJ5eG93dWdrOWhjbXI5bjVuOHFzdHliaCZlcD12MV9naWZzX3JlbGF0ZWQmY3Q9Zw/8zcxAaOLgHFN3HQsGM/giphy.gif",
        ]

    def cog_unload(self):
        if self._session and not self._session.closed:
            asyncio.create_task(self._session.close())

    async def get_session(self):
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def fetch_gif_file(self, url: str):
        """Unduh gif dari url (dengan cache), lalu bungkus jadi discord.File untuk dilampirkan.
        Mengembalikan None kalau gif tidak bisa diunduh (biar embed tetap terkirim tanpa error)."""
        if not url:
            return None

        data = self._gif_cache.get(url)
        if data is None:
            try:
                session = await self.get_session()
                headers = {"User-Agent": "Mozilla/5.0 (compatible; WhenBotDungeon/1.0)"}
                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status != 200:
                        return None
                    data = await resp.read()
                    if not data:
                        return None
                    self._gif_cache[url] = data
            except Exception:
                return None

        gif_id = url.rstrip("/").split("/")[-2] if "/" in url else "gif"
        filename = f"{gif_id}.gif"
        return discord.File(fp=io.BytesIO(data), filename=filename)

    def create_intro_embed(self, ctx, file):
        """Embed 'menjelajah dungeon' yang tampil sesaat sebelum battle dimulai."""
        embed = discord.Embed(
            title="🗺️ MEMASUKI DUNGEON...",
            description="Anda melangkah menyusuri lorong gelap, mencari kroco penjaga pertama...",
            color=0x2f3136
        )
        if file:
            embed.set_image(url=f"attachment://{file.filename}")
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        return embed

    @commands.command(name="dungeon", aliases=["raid", "adventure"])
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def enter_dungeon(self, ctx):
        """Kalahkan kroco penjaga sebelum menantang raja boss utama."""
        if not ctx.guild: return
        user_inv = await asyncio.to_thread(self.bot.db.get_user_inventory, ctx.guild.id, ctx.author.id, "card")
        passives = {"rare_count": 0, "has_epic": False, "has_legendary": False}
        if user_inv:
            for row in user_inv:
                row_str = str(row).upper()
                qty = 1
                for element in row:
                    if isinstance(element, int) and element < 1000:
                        qty = element
                        break
                if "RARE" in row_str: passives["rare_count"] += qty
                if "EPIC" in row_str: passives["has_epic"] = True
                if "LEGENDARY" in row_str: passives["has_legendary"] = True

        enemies_lineup = [random.choice(self.kroco_pool), random.choice(self.boss_pool)]
        view = DungeonBattleView(ctx, self, enemies_lineup, passives)

        # 🎬 Tampilkan gif "menjelajah dungeon" dulu sebelum ketemu kroco
        intro_gif = random.choice(self.intro_gif_pool)
        intro_file = await self.fetch_gif_file(intro_gif)
        intro_embed = self.create_intro_embed(ctx, intro_file)
        if intro_file:
            msg = await ctx.send(embed=intro_embed, file=intro_file)
        else:
            msg = await ctx.send(embed=intro_embed)
        await asyncio.sleep(2.5)

        battle_embed, battle_file = await view.build_battle_payload()
        await msg.edit(embed=battle_embed, attachments=[battle_file] if battle_file else [], view=view)
        view.message = msg

    @enter_dungeon.error
    async def dungeon_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            return await ctx.send(f"⏳ **Stamina Habis!** Tunda **{int(error.retry_after)} detik**.")
        raise error


async def setup(bot):
    await bot.add_cog(GachaDungeon(bot))