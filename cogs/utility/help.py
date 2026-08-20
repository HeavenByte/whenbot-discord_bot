import discord
from discord.ext import commands

class CustomHelpCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Menonaktifkan perintah help bawaan discord.py agar tidak tabrakan
        self.bot.remove_command("help")

    @commands.command(name="help", aliases=["bantuan", "menu", "h"])
    async def help_command(self, ctx, nama_modul: str = None):
        """Menampilkan menu bantuan instruksi bot terstruktur per kategori."""
        prefix = ctx.prefix

        # 🟢 OPSIONAL A: JIKA USER MENGETIK '+help <nama_perintah>' UNTUK DETAIL SPESIFIK
        if nama_modul:
            command = self.bot.get_command(nama_modul.lower())
            if command:
                embed = discord.Embed(
                    title=f"❓ Detail Perintah: {prefix}{command.name}",
                    description=command.help or "Tidak ada deskripsi yang tersedia.",
                    color=discord.Color.blue()
                )
                if command.aliases:
                    embed.add_field(name="Nama Lain (Aliases)", value=", ".join([f"`{a}`" for a in command.aliases]), inline=False)
                
                # Mengambil info cara pakai jika argumen diisi
                cara_pakai = f"`{prefix}{command.name} {command.signature}`" if command.signature else f"`{prefix}{command.name}`"
                embed.add_field(name="Cara Penggunaan", value=cara_pakai, inline=False)
                return await ctx.send(embed=embed)
            else:
                return await ctx.send(f"❌ Perintah `{nama_modul}` tidak ditemukan!")

        # 🟢 OPSIONAL B: MENU UTAMA '+help' (OTOMATIS MEMBACA SEMUA COGS)
        embed = discord.Embed(
            title=f"🤖 Menu Bantuan Bot - {self.bot.user.name}",
            description=f"Gunakan prefix `{prefix}` sebelum mengetik perintah.\nTulis `{prefix}help <nama_command>` untuk info detail pemakaian.",
            color=discord.Color.teal()
        )

        # Menelusuri seluruh Cogs (Genre Folder) yang terdaftar di dalam bot
        for cog_name, cog in self.bot.cogs.items():
            # Filter agar internal event handler tidak ikut memunculkan menu kosong
            commands_list = cog.get_commands()
            if not commands_list:
                continue

            # Menyusun daftar nama perintah menjadi string baris koma
            # Contoh hasil: `+balance`, `+beg`, `+work`
            formatted_commands = ", ".join([f"`{c.name}`" for c in commands_list])
            
            # Format penamaan genre kategori agar lebih rapi saat dicetak
            kategori_tampil = cog_name.replace("Cog", "").upper()
            
            embed.add_field(
                name=f"📁 Kategori: {kategori_tampil}",
                value=formatted_commands,
                inline=False
            )

        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.set_footer(text=f"Diminta oleh {ctx.author.name}", icon_url=ctx.author.display_avatar.url)
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(CustomHelpCommand(bot))
