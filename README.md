# 💰 WhenBot - Discord Economy & RPG Bot 🎮

<div align="center">

![Discord Bot](https://img.shields.io/badge/Discord-Bot-5865F2?style=for-the-badge&logo=discord&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.9-blue?style=for-the-badge&logo=python&logoColor=white)
![Status](https://img.shields.io/badge/Status-Active-brightgreen?style=for-the-badge)

**WhenBot** adalah bot Discord interaktif yang membawa sistem ekonomi virtual, minigames RPG, dan fitur gacha seru langsung ke dalam server komunitas Anda.

[Fitur Utama](#-fitur-utama) • [Instalasi](#%EF%B8%8F-cara-instalasi) • [Struktur Kategori](#-struktur-kategori-bot) • [Kontribusi](#-kontribusi)

</div>

---

---

## ✨ Fitur Utama

- 🌾 **Sistem Ekonomi & Bisnis:** Fitur Bekerja (`farming`), menambang (`mining`), dan mengelola keuangan server (`bal`).
- 🃏 **Gacha & Koleksi Kartu:** Koleksi kartu unik melalui sistem `gacha` dan simpan di dalam `inventory` Anda.
- ⚔️ **Dungeon RPG:** Masuk ke dalam `dungeon` berbahaya untuk mendapatkan hadiah dan item langka(`coming soon`).
- 🤝 **Sistem Trading:** Tukarkan item atau kartu koleksi antar pengguna server secara aman (`trading`).
- 🛡️ **Moderasi Otomatis:** Menjaga kebersihan server dari kata-kata kasar dengan fitur `banned_word`.

---

## 📂 Struktur Kategori Bot

Bot ini menggunakan sistem **Cogs** agar kodingan rapi dan terbagi menjadi beberapa kategori utama:

### 🪙 1. Kategori: Economy
*   `farming.py` — Perintah untuk bekerja farming early.
*   `mining.py` — Perintah untuk pergi menambang batu mulia atau batu bara.
*   `money.py` — Mengatur saldo, transfer uang, dan cek peringkat terkaya.

### 🎲 2. Kategori: Gacha & RPG
*   `cards.py` — Daftar kartu koleksi yang bisa didapatkan pemain.
*   `dungeon.py` — Sistem petualangan melawan monster di dalam dungeon.
*   `inventory.py` — Tempat untuk melihat semua item, senjata, dan kartu milik user.
*   `trading.py` — Sistem tukar-menukar barang atau uang antar pemain.

### 🛠️ 3. Kategori: Utilitas & Moderasi
*   `help.py` — Custom help command dinamis berbasis embed untuk melihat daftar perintah.
*   `banned_word.py` — Sistem sensor otomatis untuk menyaring kata-kata terlarang di server.

---

## 🛠️ Cara Instalasi

### 1. Clone & Masuk ke Folder Project
```bash
git clone https://github.com/HeavenByte/whenbot-discord_bot
cd whenbot-discord_bot
```

### 2. Instal Dependencies
Pastikan virtual environment (`.venv`) Anda aktif, lalu jalankan:
```bash
pip install -r requirement.txt
```

### 3. Konfigurasi Token & Database
Sesuaikan token bot Discord Anda di dalam file konfigurasi utama atau file `.env`, lalu jalankan bot:
```bash
python main.py
```

---

---

## 🤝 Kontribusi

Kami sangat terbuka untuk perbaikan fitur, perbaikan bug, atau ide minigames baru! Ikuti langkah-langkah berikut untuk berkontribusi:

1. **Fork** repository ini ke akun GitHub Anda.
2. Buat **Branch** baru untuk fitur Anda:
   ```bash
   git checkout -b fitur/fitur-baru-anda
   ```
3. Lakukan **Commit** perubahan Anda dengan pesan yang jelas:
   ```bash
   git commit -m "Menambahkan minigame bertani baru"
   ```
4. **Push** branch tersebut ke akun fork Anda:
   ```bash
   git push origin fitur/fitur-baru-anda
   ```
5. Buka halaman repository utama [HeavenByte/whenbot-discord_bot](https://github.com/HeavenByte/whenbot-discord_bot/) dan klik tombol **New Pull Request**.

---


<div align="center">
    <p>Dibuat oleh <a href="https://github.com">HeavenByte</a></p>
</div>
