import discord
from discord.ext import commands
import asyncio

class UniversalInventory(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="inventory", aliases=["inv", "tas", "bag"])
    async def show_inventory(self, ctx, member: discord.Member = None):
        """Melihat isi tas dan memunculkan gambar kartu terakhir yang didapatkan."""
        if not ctx.guild: return

        target = member or ctx.author
        
        # 1. Ambil data dari database (Format baru: name, rarity, qty, item_url)
        items = await asyncio.to_thread(self.bot.db.get_user_inventory, ctx.guild.id, target.id, "card")

        if not items:
            embed = discord.Embed(
                title=f"🎒 Tas Gudang - {target.display_name}",
                description="Tas ini kosong melompong. Ketik `+gacha` untuk mulai mengisi tas Anda!",
                color=discord.Color.red()
            )
            return await ctx.send(embed=embed)

        embed = discord.Embed(
            title=f"🎒 Tas Gudang - {target.display_name}",
            description="Berikut adalah isi kartu meme berharga yang tersimpan di dalam tas Anda:",
            color=discord.Color.blue()
        )

        cards_text = ""
        rare_count = 0
        has_epic = False
        has_legendary = False
        sample_gif_url = None

        # 2. Urutkan isi tas
        for row in items:
            name, rarity, qty, item_url = row[0], row[1], row[2], row[3]

            if "RARE" in rarity: rare_count += qty
            if "EPIC" in rarity: has_epic = True
            if "LEGENDARY" in rarity: has_legendary = True

            # Ambil salah satu link GIF dari inventory untuk dijadikan preview pajangan di Embed
            if item_url and not sample_gif_url:
                sample_gif_url = item_url

            cards_text += f"• **{name}** ({rarity}) — `x{qty}`\n"

        embed.add_field(name="🃏 KOLEKSI KARTU MEME", value=cards_text, inline=False)

        # 3. KALKULASI STATUS EFEK PASIF
        buff_text = ""
        if has_legendary:
            buff_text += "🟡 **[LEGENDARY BUFF]** Diskon Gacha 20% aktif!\n💥 **[DUNGEON CRIT]** Peluang jackpot koin 3x lipat!\n"
        if has_epic:
            buff_text += "🛡️ **[EPIC BUFF]** Perisai anti denda Dungeon aktif!\n"
        if rare_count > 0:
            buff_text += f"📈 **[RARE DAMAGE]** Win Rate Dungeon meningkat **+{rare_count * 5}%**!\n"

        if not buff_text:
            buff_text = "❌ Belum ada efek pasif spesial yang aktif. Kumpulkan kartu RARE ke atas!"

        embed.add_field(name="⚡ STATUS EFEK PASIF AKTIF", value=buff_text, inline=False)
        
        # 🟢 PERBAIKAN UTAMA: Pasang gambar GIF asli milik user sebagai visual utama di dalam inventory!
        if sample_gif_url:
            embed.set_image(url=str(sample_gif_url))

        embed.set_thumbnail(url=target.display_avatar.url)
        embed.set_footer(text=f"Kolektor: {ctx.author.name}", icon_url=ctx.author.display_avatar.url)

        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(UniversalInventory(bot))
