import discord
from discord.ext import commands
import asyncio

class GachaTrading(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="trade", aliases=["barter", "tukar", "kirimkartu"])
    async def trade_card(self, ctx, member: discord.Member = None, *, nama_kartu: str = None):
        """Mengirimkan/bertukar kartu meme dari inventory Anda kepada pengguna lain."""
        if not ctx.guild: return

        # Validasi input pengguna
        if not member or not nama_kartu:
            return await ctx.send(f"❌ Cara penggunaan salah!\nContoh: `{ctx.prefix}trade @NamaTeman Nama Kartu Meme`")

        if member.id == ctx.author.id:
            return await ctx.send("❌ Anda tidak bisa melakukan trade dengan diri sendiri!")

        if member.bot:
            return await ctx.send("❌ Anda tidak bisa melakukan trade kartu dengan Bot!")

        clean_item_name = nama_kartu.strip()

        # 1. Eksekusi pemindahan data kartu di dalam background thread pool ⚡
        sukses = await asyncio.to_thread(
            self.bot.db.transfer_item, 
            ctx.guild.id, 
            ctx.author.id, 
            member.id, 
            clean_item_name
        )

        # 2. Cek hasil operasi transfer database
        if sukses:
            # Ambil data inventory terbaru si penerima untuk menarik item_url gambar demi visual trading
            penerima_inv = await asyncio.to_thread(self.bot.db.get_user_inventory, ctx.guild.id, member.id, "card")
            
            # Cari link gambar/GIF dari kartu yang baru saja ditransfer untuk dipajang di Embed
            gifted_card_url = None
            gifted_card_rarity = "COMMON"
            for row in penerima_inv:
                if row[0] == clean_item_name:
                    gifted_card_rarity = row[1]
                    gifted_card_url = row[3]
                    break

            # 3. Tampilkan Embed bukti transaksi sukses beserta gambarnya yang ikut terkirim 🟢
            embed = discord.Embed(
                title="🤝 TRANSAKSI KARTU BERHASIL!",
                description=f"Sebuah kartu berharga telah resmi berpindah tangan!",
                color=discord.Color.dark_green()
            )
            embed.add_field(name="📦 Pengirim", value=ctx.author.mention, inline=True)
            embed.add_field(name="📥 Penerima", value=member.mention, inline=True)
            embed.add_field(name="🃏 Nama Kartu", value=f"`{clean_item_name}` ({gifted_card_rarity})", inline=False)
            
            # 🟢 KUNCI UTAMA: Gambar/GIF dari database ikut dimuat secara instan di layar trade!
            if gifted_card_url:
                embed.set_image(url=str(gifted_card_url))

            embed.set_footer(text=f"Sistem Perdagangan Komunitas Server", icon_url=ctx.guild.icon.url if ctx.guild.icon else None)
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"❌ **Gagal melakukan trade!** Anda tidak memiliki kartu bernama `{clean_item_name}` di dalam `+inventory` Anda. Pastikan huruf besar-kecil dan spasi namanya sudah sama persis.")

async def setup(bot):
    await bot.add_cog(GachaTrading(bot))
