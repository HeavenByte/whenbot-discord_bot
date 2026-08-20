import discord
from discord.ext import commands

class AdminWords(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="bannedword")
    @commands.has_permissions(manage_messages=True)
    async def add_noword(self, ctx, *, word: str = None):
        if not ctx.guild:
            return await ctx.send("❌ Perintah ini hanya bisa digunakan di dalam server!")
            
        if not word:
            return await ctx.send("❌ Masukkan kata yang ingin dilarang! Contoh: `+bannedword asuh`")
        
        clean_word = word.strip().lower()
        
        sukses = self.bot.db.add_word(ctx.guild.id, clean_word, str(ctx.author))
        
        if sukses:
            embed = discord.Embed(
                title="✅ Kata Terlarang Ditambahkan",
                description=f"Kata `{clean_word}` kini resmi masuk daftar hitam server.",
                color=discord.Color.green()
            )
            embed.add_field(name="Ditambahkan Oleh", value=ctx.author.mention, inline=True)
            embed.add_field(name="Server", value=ctx.guild.name, inline=True)
            embed.set_footer(text="Sistem Automod Server")
            
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"⚠️ Kata `{clean_word}` sudah terdaftar di server ini.")

    @commands.command(name="delword", aliases=["unbanword"])
    @commands.has_permissions(manage_messages=True)
    async def remove_noword(self, ctx, *, word: str = None):
        if not ctx.guild or not word:
            return await ctx.send("❌ Masukkan kata yang ingin dihapus dari blacklist! Contoh: `+delword asuh`")

        clean_word = word.strip().lower()

        with self.bot.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM banned_words WHERE guild_id = ? AND word = ?", 
                (str(ctx.guild.id), clean_word)
            )
            changes = cursor.rowcount
            conn.commit()

        if changes > 0:
            embed = discord.Embed(
                title="🗑️ Kata Diizinkan Kembali",
                description=f"Kata `{clean_word}` telah dihapus dari daftar larangan server.",
                color=discord.Color.blue()
            )
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"⚠️ Kata `{clean_word}` memang tidak ada di dalam daftar larangan server ini.")

async def setup(bot):
    await bot.add_cog(AdminWords(bot))
