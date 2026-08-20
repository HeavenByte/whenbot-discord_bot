import discord
from discord.ext import commands
import aiohttp
import random
import asyncio
import urllib.parse  
from dotenv import load_dotenv
import os
class GachaMemeCards(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.gacha_cost = 500
        
        self.giphy_api_key = os.getenv("APIKEY_GIPHY")

        self.search_pools = [
            "meme indonesia", "lucu", "ngakak", "kucing oren", 
            "bocil kematian", "reaksi lucu", "joget gaul"
        ]

        self.card_titles = [
            "Meme Warga Konoha Gaul", "Kucing Oren Mode Reog", "Akibat Begadang Ngegame",
            "Sultan Kebanyakan Duit", "Meme Bocil Kematian", "Meme Dompet Kering Akhir Bulan"
        ]

    @commands.command(name="gacha", aliases=["pull", "gachacard"])
    async def pull_meme_card(self, ctx):
        """Membayar koin untuk melakukan gacha GIF meme Indonesia acak secara online murni via Giphy API."""
        if not ctx.guild: return

        user_inv = await asyncio.to_thread(self.bot.db.get_user_inventory, ctx.guild.id, ctx.author.id, "card")
        has_legendary = any("LEGENDARY" in row for row in user_inv) if user_inv else False
        current_cost = 400 if has_legendary else self.gacha_cost

        current_balance = await asyncio.to_thread(self.bot.db.get_balance, ctx.guild.id, ctx.author.id)
        if current_balance < current_cost:
            return await ctx.send(f"❌ Saldo koin Anda tidak cukup! Biaya gacha: 🪙 `{current_cost:,}` koin | Dompet Anda: 🪙 `{current_balance:,}` koin.")

        await asyncio.to_thread(self.bot.db.update_balance, ctx.guild.id, ctx.author.id, -current_cost)

        loading_msg = await ctx.send("🎰 *Menghubungi satelit Giphy Pusat... Mengacak koleksi GIF Meme Indonesia...*")

        chosen_title = random.choice(self.card_titles)
        chosen_url = None
        keyword = random.choice(self.search_pools)

        safe_keyword = urllib.parse.quote(keyword)
        random_offset = random.randint(0, 40)


        giphy_url = (
           "https://api.giphy.com/v1/gifs/search"
           f"?api_key={self.giphy_api_key.strip()}"
           f"&q={safe_keyword}&limit=1&offset={random_offset}&rating=g&lang=id"
)

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(giphy_url, timeout=6) as response:
                    if response.status == 200:
                        json_payload = await response.json()
                        data_arr = json_payload.get("data", [])
                        
                        if data_arr:
                            selected_gif = data_arr[0]
                            chosen_url = selected_gif.get("images", {}).get("original", {}).get("url")
                            chosen_title = f"{chosen_title} #{random.randint(10, 99)}"
                    else:
                        print(f"⚠️ Giphy responded with bad HTTP code: {response.status}")
            except Exception as e:
                print(f"⚠️ Giphy connection execution failed: {e}")

        if not chosen_url:
            await loading_msg.delete()
            await asyncio.to_thread(self.bot.db.update_balance, ctx.guild.id, ctx.author.id, current_cost)
            return await ctx.send("⚠️ **Gacha Gagal!** Giphy API Key Anda ditolak, limit, atau koneksi timeout. Koin Anda telah dikembalikan aman!")

        roll = random.random()
        if roll < 0.05:
            rarity = "LEGENDARY 🟡"
            embed_color = discord.Color.gold()
            admin_commentary = "ANJAY SUJUD SUNGKEM KEPADA SULTAN!"
        elif roll < 0.20:
            rarity = "EPIC 🟣"
            embed_color = discord.Color.purple()
            admin_commentary = "Gila keren banget kartu ungu meluncur!"
        elif roll < 0.50:
            rarity = "RARE 🔵"
            embed_color = discord.Color.blue()
            admin_commentary = "Boleh lah, dapet kartu biru penambah damage!"
        else:
            rarity = "COMMON 🔴"
            embed_color = discord.Color.light_grey()
            admin_commentary = "Wkwkwk apes banget dapet kartu debu jalanan!"

        total_owned = await asyncio.to_thread(
            self.bot.db.add_item_to_inventory, 
            ctx.guild.id, ctx.author.id, chosen_title, "card", rarity, str(chosen_url)
        )

        embed = discord.Embed(
            title=f"🃏 KARTU GACHA: {rarity}",
            description=f"💬 *{admin_commentary}*\n\n**Nama Kartu:** `{chosen_title}`",
            color=embed_color
        )
        embed.set_image(url=str(chosen_url))
        embed.set_footer(text=f"Kolektor: {ctx.author.name} • Total Dimiliki: {total_owned}x", icon_url=ctx.author.display_avatar.url)

        await loading_msg.delete()
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(GachaMemeCards(bot))
