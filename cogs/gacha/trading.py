import discord
from discord.ext import commands
import asyncio


def _utf16_len(s: str) -> int:
    return len(s.encode("utf-16-le")) // 2


def _utf16_truncate(s: str, max_units: int) -> str:
    result = []
    total = 0
    for ch in s:
        ch_units = len(ch.encode("utf-16-le")) // 2
        if total + ch_units > max_units:
            break
        result.append(ch)
        total += ch_units
    return "".join(result)


def safe_label(text: str, suffix: str = "", max_len: int = 100) -> str:
    text = str(text).strip() if text else "Item Tanpa Nama"
    if not text:
        text = "Item Tanpa Nama"

    full = f"{text}{suffix}"
    if _utf16_len(full) <= max_len:
        return full

    # Kepanjangan -> potong bagian nama, sisakan ruang buat suffix + elipsis "…" (1 unit)
    suffix_units = _utf16_len(suffix)
    room_for_name = max_len - suffix_units - 1
    if room_for_name < 1:
        # suffix sendiri sudah hampir/lewat batas -> potong suffix juga sebagai jalan terakhir
        return _utf16_truncate(full, max_len)

    truncated_name = _utf16_truncate(text, room_for_name)
    result = f"{truncated_name}…{suffix}"

    # Pengaman terakhir: kalau karena alasan apapun masih lewat, paksa potong total
    if _utf16_len(result) > max_len:
        result = _utf16_truncate(result, max_len)
    return result if result else "Item"


def safe_description(text: str, max_len: int = 100) -> str:
    text = str(text).strip() if text else "Tidak diketahui"
    if not text:
        text = "Tidak diketahui"
    if _utf16_len(text) > max_len:
        text = _utf16_truncate(text, max_len - 1) + "…"
    return text


def safe_value(text: str, fallback: str, max_len: int = 100) -> str:
    text = str(text).strip() if text else fallback
    if not text:
        text = fallback
    if _utf16_len(text) > max_len:
        text = _utf16_truncate(text, max_len)
    return text


class TradeDropdown(discord.ui.Select):
    def __init__(self, items, member, prefix):
        self.member = member
        self.prefix = prefix


        options = []
        seen_values = set()
        for idx, row in enumerate(items[:25]):
            raw_name = row[0] if len(row) > 0 else None   # item_name
            rarity = row[2] if len(row) > 2 else None     # item_rarity
            qty = row[3] if len(row) > 3 and row[3] else 1  # quantity

            name = str(raw_name).strip() if raw_name else "Item Tanpa Nama"
            if not name:
                name = "Item Tanpa Nama"

            label = safe_label(name, suffix=f" (x{qty})")
            description = safe_description(f"Kelangkaan: {rarity}" if rarity else "Kelangkaan: Tidak diketahui")

            # value dipakai sebagai identifier balik ke DB — jaga tetap unik walau nama sama/kosong
            value = safe_value(name, fallback=f"item_{idx}")
            if value in seen_values:
                value = safe_value(f"{value}_{idx}", fallback=f"item_{idx}")
            seen_values.add(value)

   
            if _utf16_len(label) < 1 or _utf16_len(label) > 100:
                print(f"[trading.py] ⚠️ Label opsi #{idx} masih di luar batas ({_utf16_len(label)} unit): {label!r} | raw_name={raw_name!r}")
            if _utf16_len(description) < 1 or _utf16_len(description) > 100:
                print(f"[trading.py] ⚠️ Description opsi #{idx} masih di luar batas ({_utf16_len(description)} unit): {description!r}")
            if _utf16_len(value) < 1 or _utf16_len(value) > 100:
                print(f"[trading.py] ⚠️ Value opsi #{idx} masih di luar batas ({_utf16_len(value)} unit): {value!r}")

            options.append(discord.SelectOption(
                label=label,
                description=description,
                emoji="🃏",
                value=value
            ))

        super().__init__(
            placeholder="🤝 Pilih kartu dari tas Anda yang ingin dikirim...",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
      
        if interaction.user.id != self.view.sender.id:
            return await interaction.response.send_message("❌ Ini bukan sesi trade Anda!", ephemeral=True)

        selected_card = self.values[0]
        self.view.selected_card = selected_card

        for child in self.view.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = False


        embed = discord.Embed(
            title="⏳ KONFIRMASI PENGIRIMAN KARTU",
            description=f"Apakah Anda yakin ingin mengirimkan kartu berikut kepada {self.member.mention}?\n\n"
                        f"▪️ **Kartu Terpilih:** `{selected_card}`\n"
                        f"▪️ **Tujuan Transfer:** {self.member.mention}\n\n"
                        f"💬 *Silakan klik tombol di bawah untuk mengeksekusi data.*",
            color=0xffcc00
        )
        embed.set_footer(text="Menunggu verifikasi transaksi...")
        await interaction.response.edit_message(embed=embed, view=self.view)


class TradeView(discord.ui.View):
    def __init__(self, sender, member, items, prefix, cog_instance):
        super().__init__(timeout=60.0)
        self.sender = sender
        self.member = member
        self.prefix = prefix
        self.cog = cog_instance
        self.selected_card = None
        self.message = None

        # Tambahkan dropdown kartu pengirim ke dalam view
        self.add_item(TradeDropdown(items, member, prefix))

    @discord.ui.button(label="🟢 Setuju Kirim", style=discord.ButtonStyle.success, disabled=True)
    async def confirm_trade(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.sender.id:
            return await interaction.response.send_message("❌ Anda tidak berwenang mengeksekusi ini.", ephemeral=True)


        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(view=self)


        sukses = await asyncio.to_thread(
            self.cog.bot.db.transfer_item,
            interaction.guild.id,
            self.sender.id,
            self.member.id,
            self.selected_card
        )

        if sukses:

            penerima_inv = await asyncio.to_thread(self.cog.bot.db.get_user_inventory, interaction.guild.id, self.member.id, "card")
            gifted_card_url = None
            gifted_card_rarity = "COMMON"

            for row in penerima_inv:
                if row[0] == self.selected_card:
                    gifted_card_rarity = row[1]
                    gifted_card_url = row[3]
                    break

            embed_sukses = discord.Embed(
                title="🤝 TRANSAKSI KARTU BERHASIL!",
                description=f"Protokol transfer aset selesai. Kartu telah berpindah tangan!",
                color=0x00ffcc  
            )
            embed_sukses.add_field(name="📦 Pengirim", value=self.sender.mention, inline=True)
            embed_sukses.add_field(name="📥 Penerima", value=self.member.mention, inline=True)
            embed_sukses.add_field(name="🃏 Item Terkirim", value=f"`{self.selected_card}` ({gifted_card_rarity})", inline=False)

            if gifted_card_url:
                embed_sukses.set_image(url=str(gifted_card_url))

            embed_sukses.set_footer(text="Sistem Perdagangan Komunitas Server • Selesai")
            await interaction.message.edit(embed=embed_sukses, view=None)
        else:
            await interaction.message.edit(content=f"❌ **Transaksi Gagalkan!** Terjadi galat database atau kartu mendadak hilang dari tas Anda.", embed=None, view=None)

    @discord.ui.button(label="🔴 Batalkan", style=discord.ButtonStyle.danger, disabled=True)
    async def cancel_trade(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.sender.id:
            return await interaction.response.send_message("❌ Anda tidak berwenang menolak ini.", ephemeral=True)

        embed_batal = discord.Embed(title="❌ Transaksi Dibatalkan oleh Pengirim", color=0xff3333)
        await interaction.response.edit_message(embed=embed_batal, view=None)
        await asyncio.sleep(2.0)
        await interaction.message.delete()

    async def on_timeout(self):
        try:
            for child in self.children:
                child.disabled = True
            if self.message:
                await self.message.edit(content="🛑 [ TRANSACTION TIMEOUT — Sesi perdagangan kedaluwarsa ]", embed=None, view=None)
        except Exception:
            pass


class GachaTrading(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="trade", aliases=["barter", "tukar", "kirimkartu"])
    async def trade_card(self, ctx, member: discord.Member = None):
        """Mengirimkan kartu meme lewat antarmuka pilihan dropdown interaktif tanpa ketik manual."""
        if not ctx.guild: return

        # Validasi target transfer
        if not member:
            return await ctx.send(f"❌ Cara penggunaan salah!\nContoh: `{ctx.prefix}trade @NamaTeman`")

        if member.id == ctx.author.id:
            return await ctx.send("❌ Anda tidak bisa melakukan trade dengan diri sendiri!")

        if member.bot:
            return await ctx.send("❌ Anda tidak bisa melakukan trade kartu dengan Bot!")

        pengirim_inv = await asyncio.to_thread(self.bot.db.get_user_inventory, ctx.guild.id, ctx.author.id, "card")

        if not pengirim_inv:
            return await ctx.send("❌ Tas Anda kosong melompong! Tidak ada kartu yang bisa Anda perdagangkan.")


        embed = discord.Embed(
            title="🤝 MATRIX TRADE STATION",
            description=f"Halo {ctx.author.mention}!\nSilakan tentukan kartu yang ingin Anda hibahkan kepada {member.mention} melalui menu seleksi di bawah ini:",
            color=0x2f3136
        )
        embed.set_footer(text="Sesi perdagangan aktif selama 60 detik.")

        view = TradeView(ctx.author, member, pengirim_inv, ctx.prefix, self)
        try:
            msg = await ctx.send(embed=embed, view=view)
        except discord.HTTPException as e:
            print(f"[trading.py] ❌ Gagal kirim panel trade untuk {ctx.author.id}: {e}")
            return await ctx.send(
                "❌ Gagal membuka menu trade — ada data kartu di inventory Anda yang formatnya tidak wajar. "
                "Laporkan ke admin bot beserta waktu kejadian ini ya."
            )
        view.message = msg


async def setup(bot):
    await bot.add_cog(GachaTrading(bot))