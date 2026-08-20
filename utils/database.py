import sqlite3

class BotDatabase:
    def __init__(self, db_name="bot_database.db"):
        # Dipaksa ke satu nama konsisten agar tidak bertabrakan antar file
        self.db_name = "bot_database.db"
        self.init_db()

    def _get_connection(self):
        return sqlite3.connect(self.db_name, timeout=20)

    def init_db(self):
        """🟢 Unified structure initializing all tables and auto-patching missing columns."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            
            # 1. Moderation Banned Words
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS banned_words (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id TEXT NOT NULL,
                    word TEXT NOT NULL,
                    added_by TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(guild_id, word)
                )
            ''')
            
            # 2. Base Economy Matrix
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS economy (
                    guild_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    balance INTEGER DEFAULT 0,
                    last_daily TIMESTAMP,
                    PRIMARY KEY (guild_id, user_id)
                )
            ''')
            
            # 3. Universal Storage Inventory System
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS inventory (
                    guild_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    item_name TEXT NOT NULL,
                    item_type TEXT NOT NULL,
                    item_rarity TEXT NOT NULL,
                    quantity INTEGER DEFAULT 1,
                    item_url TEXT,
                    PRIMARY KEY (guild_id, user_id, item_name)
                )
            ''')
            
            # 4. Adventure Exploration Time tracking
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS dungeon_status (
                    guild_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    last_dungeon TEXT,
                    PRIMARY KEY (guild_id, user_id)
                )
            ''')
            
            # 🟢 DYNAMIC AUTO-PATCHER: Inserts item_url dynamically if old file exists
            try:
                cursor.execute("ALTER TABLE inventory ADD COLUMN item_url TEXT")
            except sqlite3.OperationalError:
                pass # Column already exists, skip patching safely

            conn.commit()
            print("✅ Database System: All tables verified, patched, and operational.")
        finally:
            conn.close()


    # ==================== UTILITIES: MODERATION ====================
    def add_word(self, guild_id: int, word: str, author_name: str) -> bool:
        clean_word = word.strip().lower()
        if not clean_word:
            return False
            
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            query = "INSERT INTO banned_words (guild_id, word, added_by) VALUES (?, ?, ?)"
            data = (str(guild_id), clean_word, author_name)
            
            cursor.execute(query, data)
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close() 

    def get_words_for_guild(self, guild_id: int) -> set:
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            query = "SELECT word FROM banned_words WHERE guild_id = ?"
            cursor.execute(query, (str(guild_id),))
            rows = cursor.fetchall()
            return {row for row in rows}
        finally:
            conn.close()

    # ==================== UTILITIES: ECONOMY ====================
    def get_balance(self, guild_id: int, user_id: int) -> int:
        """Mengambil saldo user sebagai angka murni (INTEGER)."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT balance FROM economy WHERE guild_id = ? AND user_id = ?", 
                (str(guild_id), str(user_id))
            )
            row = cursor.fetchone()
            
            if row is None:
                cursor.execute(
                    "INSERT INTO economy (guild_id, user_id, balance) VALUES (?, ?, 0)",
                    (str(guild_id), str(user_id))
                )
                conn.commit()
                return 0
                
            # 🟢 FIXED: Target index [0] to extract the numeric raw integer from the tuple channel
            return int(row[0])
        finally:
            conn.close()


    def update_balance(self, guild_id: int, user_id: int, amount: int) -> int:
        """Menambah atau mengurangi saldo user dalam satu koneksi aman (Anti-Lock)."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            
            # 1. Ambil saldo saat ini langsung di dalam koneksi ini ⚡
            cursor.execute(
                "SELECT balance FROM economy WHERE guild_id = ? AND user_id = ?", 
                (str(guild_id), str(user_id))
            )
            row = cursor.fetchone()
            
            # Jika user belum ada, inisialisasi saldo ke 0
            if row is None:
                cursor.execute(
                    "INSERT INTO economy (guild_id, user_id, balance) VALUES (?, ?, 0)",
                    (str(guild_id), str(user_id))
                )
                current_bal = 0
            else:
                # 🟢 SECURE PACK UNBOXING: Explicitly call index [0] to bypass tuple errors
                current_bal = int(row[0])
                
            # 2. Kalkulasi nilai baru dengan proteksi anti-minus
            new_bal = max(0, current_bal + amount)
            
            # 3. Update data langsung tanpa membuka koneksi baru ⚡
            cursor.execute(
                "UPDATE economy SET balance = ? WHERE guild_id = ? AND user_id = ?",
                (new_bal, str(guild_id), str(user_id))
            )
            conn.commit()
            return new_bal
        finally:
            conn.close() # Selesai, tutup total!

    def get_top_economy(self, guild_id: int, limit: int = 10) -> list:
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT user_id, balance FROM economy WHERE guild_id = ? ORDER BY balance DESC LIMIT ?", 
                (str(guild_id), limit)
            )
            return cursor.fetchall() 
        finally:
            conn.close()

    # ==================== UTILITIES: UNIVERSAL INVENTORY ====================
    def add_item_to_inventory(self, guild_id: int, user_id: int, item_name: str, item_type: str, rarity: str, item_url: str) -> int:
        """Menambahkan item ke dalam tas inventaris dengan mengunci URL GIF-nya."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO inventory (guild_id, user_id, item_name, item_type, item_rarity, quantity, item_url)
                VALUES (?, ?, ?, ?, ?, 1, ?)
                ON CONFLICT(guild_id, user_id, item_name)
                DO UPDATE SET quantity = quantity + 1
            ''', (str(guild_id), str(user_id), item_name, item_type, rarity, item_url))
            
            cursor.execute("SELECT quantity FROM inventory WHERE guild_id = ? AND user_id = ? AND item_name = ?", (str(guild_id), str(user_id), item_name))
            row = cursor.fetchone()
            conn.commit()
            return row if row else 1
        finally:
            conn.close()

    def get_user_inventory(self, guild_id: int, user_id: int, item_type: str = None) -> list:
        """Mengambil data tas lengkap termasuk kolom item_url."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            if item_type:
                cursor.execute("SELECT item_name, item_rarity, quantity, item_url FROM inventory WHERE guild_id = ? AND user_id = ? AND item_type = ?", (str(guild_id), str(user_id), item_type))
            else:
                cursor.execute("SELECT item_name, item_rarity, quantity, item_url, item_type FROM inventory WHERE guild_id = ? AND user_id = ?", (str(guild_id), str(user_id)))
            return cursor.fetchall()
        finally:
            conn.close()

    # ==================== UTILITIES: DUNGEON COOLDOWN ====================
    def check_dungeon_cooldown(self, guild_id: int, user_id: int) -> str:
        """Mengecek sisa waktu tunggu dungeon."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT last_dungeon FROM dungeon_status WHERE guild_id = ? AND user_id = ?", (str(guild_id), str(user_id)))
            row = cursor.fetchone()
            if row is None:
                cursor.execute("INSERT INTO dungeon_status (guild_id, user_id, last_dungeon) VALUES (?, ?, NULL)", (str(guild_id), str(user_id)))
                conn.commit()
                return None
            return row
        finally:
            conn.close()

    def update_dungeon_time(self, guild_id: int, user_id: int, timestamp_str: str):
        """Mencatat waktu terkini saat user berhasil masuk dungeon."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("UPDATE dungeon_status SET last_dungeon = ? WHERE guild_id = ? AND user_id = ?", (timestamp_str, str(guild_id), str(user_id)))
            conn.commit()
        finally:
            conn.close()

    def transfer_item(self, guild_id: int, from_user: int, to_user: int, item_name: str) -> bool:
        """Memindahkan item dari inventory satu user ke user lain. Mengembalikan True jika berhasil."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            
            # 1. Cek apakah pengirim benar-benar memiliki kartu tersebut
            cursor.execute(
                "SELECT item_rarity, quantity, item_url FROM inventory WHERE guild_id = ? AND user_id = ? AND item_name = ?",
                (str(guild_id), str(from_user), item_name)
            )
            row = cursor.fetchone()
            
            if row is None:
                return False # Pengirim tidak punya kartu ini
                
            rarity = row[0]
            current_qty = int(row[1])
            item_url = row[2]

            # 2. Kurangi jumlah kartu milik pengirim (Jika tinggal 1 hapus baris, jika lebih dari 1 kurangi 1)
            if current_qty == 1:
                cursor.execute(
                    "DELETE FROM inventory WHERE guild_id = ? AND user_id = ? AND item_name = ?",
                    (str(guild_id), str(from_user), item_name)
                )
            else:
                cursor.execute(
                    "UPDATE inventory SET quantity = quantity - 1 WHERE guild_id = ? AND user_id = ? AND item_name = ?",
                    (str(guild_id), str(from_user), item_name)
                )

            # 3. Masukkan atau tambahkan kartu tersebut ke dalam inventory penerima (Link gambar/item_url tetap utuh!)
            cursor.execute('''
                INSERT INTO inventory (guild_id, user_id, item_name, item_type, item_rarity, quantity, item_url)
                VALUES (?, ?, ?, 'card', ?, 1, ?)
                ON CONFLICT(guild_id, user_id, item_name)
                DO UPDATE SET quantity = quantity + 1
            ''', (str(guild_id), str(to_user), item_name, rarity, item_url))
            
            conn.commit()
            return True
        except Exception as e:
            print(f"Error saat transfer_item: {e}")
            return False
        finally:
            conn.close()
