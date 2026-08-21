import discord
from discord.ext import commands
import asyncio

class InventoryPaginator(discord.ui.View):
    def __init__(self, ctx, target, pages, total_cards, stats_embed_data):
        super().__init__(timeout=60.0)  # Tombol otomatis mati setelah 60 detik tidak aktif
        self.ctx = ctx
        self.target = target
        self.pages = pages
        self.current_page = 0
        self.total_cards = total_cards
        self.stats_data = stats_embed_data
        self.message = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("❌ Anda tidak bisa menggunakan tombol inventori milik orang lain!", ephemeral=True)
            return False
        return True

    def create_embed(self):
        """Membuat embed dinamis berdasarkan halaman aktif saat ini."""
        embed = discord.Embed(
            title=f"🎒 VAULT STORAGE — {self.target.display_name}",
            description=f"### Pemilik Vault: {self.target.mention}\nBerikut adalah isi koleksi kartu meme berharga yang tersimpan di dalam gudang:",
            color=0x2f3136
        )

        page_title = f"🗃️ KOLEKSI KARTU MEME (Halaman {self.current_page + 1}/{len(self.pages)})"
        page_content = self.pages[self.current_page]["text"]
        embed.add_field(name=page_title, value=page_content, inline=False)


        embed.add_field(name="📊 TOTAL KOLEKSI", value=f"```🎰 {self.total_cards} Kartu```", inline=True)
        embed.add_field(name="📈 BONUS WIN RATE", value=f"```📈 +{self.stats_data['bonus_pct']}%\n{self.stats_data['progress_bar']}```", inline=True)

        buff_text = self.stats_data["buff_text"]
        embed.add_field(name="⚡ SINEGRI EFEK PASIF KARAKTER", value=buff_text, inline=False)

        page_gif = self.pages[self.current_page]["best_gif"] or self.stats_data["global_best_gif"]
        if page_gif:
            embed.set_image(url=str(page_gif))

        embed.set_thumbnail(url=self.target.display_avatar.url)
        embed.set_footer(text=f"Sistem Gudang • Halaman {self.current_page + 1}/{len(self.pages)}", icon_url=self.ctx.author.display_avatar.url)
        return embed

    def update_buttons(self):
        """Mengaktifkan/menonaktifkan tombol panah berdasarkan posisi halaman."""
        self.prev_button.disabled = self.current_page == 0
        self.next_button.disabled = self.current_page == len(self.pages) - 1

    @discord.ui.button(label="◀️ Sebelum", style=discord.ButtonStyle.blurple, disabled=True)
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page -= 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.create_embed(), view=self)

    @discord.ui.button(label="▶️ Sesudah", style=discord.ButtonStyle.blurple)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page += 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.create_embed(), view=self)

    async def on_timeout(self):
        """Ketika tombol kedaluwarsa, matikan semua tombol agar tidak bisa diklik lagi."""
        try:
            for child in self.children:
                child.disabled = True
            if self.message:
                await self.message.edit(view=self)
        except Exception:
            pass


class UniversalInventory(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="inventory", aliases=["inv", "tas", "bag"])
    async def show_inventory(self, ctx, member: discord.Member = None):
        """Melihat isi tas gacha dengan sistem halaman interaktif menggunakan tombol."""
        if not ctx.guild: return

        target = member or ctx.author
        
        items = await asyncio.to_thread(self.bot.db.get_user_inventory, ctx.guild.id, target.id, "card")

        if not items:
            embed = discord.Embed(
                title=f"🎒 PREMIUM INVENTORY",
                description=f"### 🛑 Tas Kosong Melompong!\nHalo {target.mention}, gudang penyimpanan kartu Anda masih belum memiliki isi. Yuk mulai berburu kartu meme lewat perintah `+gacha` sekarang!",
                color=0xff3333
            )
            embed.set_thumbnail(url=target.display_avatar.url)
            return await ctx.send(embed=embed)

        rarity_styles = {
            "LEGENDARY": {"emoji": "👑", "weight": 4},
            "EPIC": {"emoji": "🔮", "weight": 3},
            "RARE": {"emoji": "💎", "weight": 2},
            "COMMON": {"emoji": "📦", "weight": 1}
        }

        def get_rarity_weight(row):
            rarity_name = str(row[1]).upper() if len(row) > 1 else ""
            for key, config in rarity_styles.items():
                if key in rarity_name:
                    return config["weight"]
            return 0


        sorted_items = sorted(items, key=get_rarity_weight, reverse=True)

        rare_count = 0
        has_epic = False
        has_legendary = False
        total_cards_collected = 0
        global_best_gif = None
        global_highest_weight = 0

        pages_data = []
        current_page_text = ""
        current_page_best_gif = None
        current_page_highest_weight = 0
        items_per_page = 5  # Maksimal item per halaman
        item_counter = 0


        for row in sorted_items:
            name, rarity, qty, item_url = row[0], row[1], row[2], row[3]
            rarity_upper = rarity.upper()

            # Kalkulasi Statistik Koleksi
            total_cards_collected += qty
            if "RARE" in rarity_upper: rare_count += qty
            if "EPIC" in rarity_upper: has_epic = True
            if "LEGENDARY" in rarity_upper: has_legendary = True

            card_weight = get_rarity_weight(row)
            
   
            if item_url and card_weight > global_highest_weight:
                global_best_gif = item_url
                global_highest_weight = card_weight

            if item_url and card_weight > current_page_highest_weight:
                current_page_best_gif = item_url
                current_page_highest_weight = card_weight

            # Dapatkan Emoji Kelangkaan
            style = {"emoji": "🃏"}
            for key, config in rarity_styles.items():
                if key in rarity_upper:
                    style = config
                    break


            current_page_text += f"{style['emoji']} `{qty:02d}x` **{name}**\n┗ Kelangkaan: *{rarity_upper}*\n"
            item_counter += 1


            if item_counter >= items_per_page:
                pages_data.append({
                    "text": current_page_text,
                    "best_gif": current_page_best_gif
                })

                current_page_text = ""
                current_page_best_gif = None
                current_page_highest_weight = 0
                item_counter = 0


        if current_page_text:
            pages_data.append({
                "text": current_page_text,
                "best_gif": current_page_best_gif
            })

        # 4. Kalkulasi Data Statistik Luar untuk Embed
        max_rare_cap = 10
        clamped_rare = min(rare_count, max_rare_cap)
        progress_bar = "█" * clamped_rare + "░" * (max_rare_cap - clamped_rare)
        bonus_pct = rare_count * 5

        buff_lines = []
        if has_legendary:
            buff_lines.append("👑 **[LEGENDARY PERK]** Aktif: Diskon Biaya Gacha **-20%**")
            buff_lines.append("💥 **[CRITICAL BOOST]** Aktif: Multiplier Koin Dungeon **3x Lipat**")
        if has_epic:
            buff_lines.append("🛡️ **[EPIC SHIELD]** Aktif: Imunitas Kebangkrutan di Dungeon")
        if rare_count > 0:
            buff_lines.append(f"💎 **[RARE SYNERGY]** Aktif: Peningkatan Stat Tempur")

        buff_text = "\n".join(buff_lines) if buff_lines else "❌ *Tidak ada efek pasif aktif. Kumpulkan kartu RARE ke atas!*"

        stats_embed_data = {
            "bonus_pct": bonus_pct,
            "progress_bar": progress_bar,
            "buff_text": buff_text,
            "global_best_gif": global_best_gif
        }

        # 5. Jalankan Paginator & Kirim ke Discord
        view = None
        if len(pages_data) > 1:
            view = InventoryPaginator(ctx, target, pages_data, total_cards_collected, stats_embed_data)
            view.update_buttons()

        # Inisialisasi awal tampilan halaman 1
        initial_paginator = InventoryPaginator(ctx, target, pages_data, total_cards_collected, stats_embed_data)
        embed_awal = initial_paginator.create_embed()

        if view:
            msg = await ctx.send(embed=embed_awal, view=view)
            view.message = msg
        else:
            await ctx.send(embed=embed_awal)

async def setup(bot):
    await bot.add_cog(UniversalInventory(bot))
