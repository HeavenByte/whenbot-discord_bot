import discord
from discord.ext import commands
from better_profanity import profanity

class BadWordDetector(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        profanity.load_censor_words()

    @commands.Cog.listener()
    async def on_message(self, message):

        if not message.guild or message.author.bot:
            return

        text_lower = message.content.lower()
        words_in_text = text_lower.split()


        guild_banned_words = self.bot.db.get_words_for_guild(message.guild.id)

        is_badword = any(word in guild_banned_words for word in words_in_text)

        if not is_badword:
            try:
                is_badword = self.multilang_filter.has_profanity(text_lower)
            except Exception:
                pass

        if is_badword:
            try:
                await message.delete()
                await message.channel.send(
                    f"⚠️ {message.author.mention}, kata tersebut dilarang oleh peraturan server ini!", 
                    delete_after=5
                )
            except discord.Forbidden:
                pass

async def setup(bot):
    await bot.add_cog(BadWordDetector(bot))
