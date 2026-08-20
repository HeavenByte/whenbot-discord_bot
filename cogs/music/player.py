import discord
from discord.ext import commands
import yt_dlp
import asyncio
import shutil


def resolve_ffmpeg_path() -> str:
    """Cari executable FFmpeg: system PATH dulu, fallback ke binary bawaan imageio-ffmpeg."""
    system_ffmpeg = shutil.which("ffmpeg")
    if system_ffmpeg:
        return system_ffmpeg
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        raise RuntimeError("FFmpeg tidak ditemukan! Jalankan: pip install imageio-ffmpeg")


class MusicSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.FFMPEG_PATH = resolve_ffmpeg_path()

        self.YTDL_OPTIONS = {
            'format': 'bestaudio/best',
            'noplaylist': True,
            'nocheckcertificate': True,
            'ignoreerrors': False,
            'logtostderr': False,
            'quiet': True,
            'no_warnings': True,
            'default_search': 'ytsearch',
            'source_address': '0.0.0.0',
            # 🟢 FIX 403: hindari klien ANDROID_VR (butuh PO Token, selalu 403 di FFmpeg).
            # Kasih beberapa klien sebagai fallback — kalau satu gagal decode format,
            # yt_dlp otomatis coba klien berikutnya di list ini.
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'web', 'tv'],
                }
            },
        }

    def _extract_audio_url(self, search_query: str) -> dict:
        """Cari lagu di YouTube via yt_dlp (dijalankan di background thread)."""
        with yt_dlp.YoutubeDL(self.YTDL_OPTIONS) as ytdl:
            info = ytdl.extract_info(search_query, download=False)
            if 'entries' in info:
                info = info['entries'][0]

            return {
                'source_url': info['url'],
                'title': info.get('title', 'Lagu Misterius'),
                # 🟢 Header yang dipakai yt_dlp saat extract — WAJIB diteruskan ke FFmpeg,
                # kalau tidak, YouTube menolak koneksi FFmpeg (403) dan audio jadi kosong.
                'http_headers': info.get('http_headers', {}),
            }

    @commands.command(name="play", aliases=["p", "setel", "lagu"])
    async def play_song(self, ctx, *, search: str = None):
        """Membuat bot masuk ke Voice Channel Anda dan memutar lagu dari YouTube."""
        if not ctx.guild: return

        if not search:
            return await ctx.send(f"❌ Cara penggunaan salah! Contoh: `{ctx.prefix}play Judul Lagu`")

        if not ctx.author.voice:
            return await ctx.send("❌ Anda harus bergabung ke dalam Voice Channel terlebih dahulu!")

        voice_channel = ctx.author.voice.channel

        if ctx.voice_client is None:
            vc = await voice_channel.connect()
        else:
            vc = ctx.voice_client
            if vc.channel != voice_channel:
                await vc.move_to(voice_channel)

        if vc.is_playing():
            vc.stop()

        loading_msg = await ctx.send(f"🔍 *Mencari lagu `{search}` di YouTube...*")

        try:
            song_data = await asyncio.to_thread(self._extract_audio_url, search)
            source_url = song_data['source_url']
            title = song_data['title']
            http_headers = song_data.get('http_headers', {})
            print(f"🔎 DEBUG http_headers: {http_headers}")  # Sementara, hapus setelah beres

            # 🟢 FIX UTAMA: teruskan header (User-Agent dll) yang sama dipakai yt_dlp ke FFmpeg.
            # Tanpa ini, request FFmpeg ke URL googlevideo ditolak YouTube (403) → tidak ada suara.
            before_options = "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"
            if http_headers:
                header_str = "\r\n".join(f"{k}: {v}" for k, v in http_headers.items()) + "\r\n"
                before_options += f' -headers "{header_str}"'

            # 🟢 FIX: pakai FFmpegPCMAudio biasa, BUKAN FFmpegOpusAudio.from_probe().
            # from_probe() menjalankan FFmpeg 2x (probe + play) dan probe-nya TIDAK menerima
            # header sama sekali — itu penyebab error 403/CalledProcessError yang kamu lihat.
            # PCMAudio cukup dan tidak perlu probing karena kita sudah tahu ini audio stream.
            ffmpeg_log = open("ffmpeg_debug.log", "a", encoding="utf-8", errors="ignore")
            audio_source = discord.FFmpegPCMAudio(
                source_url,
                executable=self.FFMPEG_PATH,
                before_options=before_options,
                options="-vn",
                stderr=ffmpeg_log,
            )

            def _after_play(error):
                if error:
                    print(f"⚠️ Playback error (FFmpeg): {error}")

            vc.play(audio_source, after=_after_play)

            embed = discord.Embed(
                title="🎶 MEMUTAR LAGU",
                description=f"Berhasil menyetel audio streaming langsung dari YouTube pusat!\n\n📌 **Judul:** `{title}`",
                color=discord.Color.green()
            )
            embed.set_footer(text=f"Diputar oleh: {ctx.author.name}", icon_url=ctx.author.display_avatar.url)

            await loading_msg.delete()
            await ctx.send(embed=embed)

        except Exception as e:
            if 'loading_msg' in locals():
                await loading_msg.delete()
            print(f"⚠️ Sistem musik gagal: {e}")
            await ctx.send("❌ Gagal memutar lagu! Silakan coba lagi dengan kata kunci judul yang berbeda.")

    @commands.command(name="stop", aliases=["dc", "keluar", "leave"])
    async def stop_music(self, ctx):
        if not ctx.guild: return
        if ctx.voice_client:
            await ctx.voice_client.disconnect()
            await ctx.send("👋 **Sampai jumpa!** Bot telah keluar dari Voice Channel.")
        else:
            await ctx.send("❌ Bot sedang tidak bergabung di Voice Channel manapun.")

    @commands.command(name="pause", aliases=["jeda"])
    async def pause_music(self, ctx):
        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.pause()
            await ctx.send("⏸️ Lagu berhasil dijeda!")
        else:
            await ctx.send("❌ Bot sedang tidak memutar lagu apapun.")

    @commands.command(name="resume", aliases=["lanjut"])
    async def resume_music(self, ctx):
        if ctx.voice_client and ctx.voice_client.is_paused():
            ctx.voice_client.resume()
            await ctx.send("▶️ Lagu dilanjutkan kembali!")
        else:
            await ctx.send("❌ Lagu sedang tidak dalam kondisi dijeda.")


async def setup(bot):
    await bot.add_cog(MusicSystem(bot))