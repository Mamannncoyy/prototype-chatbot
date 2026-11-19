# Telegram POS Assistant (Python)

Starter backend FastAPI untuk menerima webhook Telegram, membaca RPC `pos_dashboard()` dari Supabase, lalu menyusun jawaban dengan OpenAI Responses API.

## Prasyarat skema dan akses

- Jalankan migration/schema yang disediakan pemilik Supabase melalui proses mereka sendiri. File bot ini tidak menjalankan SQL.
- Di Supabase Auth, buat akun khusus bot dan set `profiles.role` akun tersebut menjadi `owner` atau `admin`. RPC `pos_dashboard()` diberikan ke role `authenticated` dan sesi login tersebut menjalankannya.
- Isi `ALLOWED_TELEGRAM_IDS` dengan Telegram user ID yang boleh mengakses laporan. Jangan deploy dengan daftar kosong.
- Gunakan publishable key Supabase di backend bersama sesi Auth akun bot. Hindari service-role/secret key untuk starter ini.

## Menjalankan lokal

1. Buat virtual environment dan pasang dependensi:

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

2. Salin `.env.example` menjadi `.env`, kemudian isi semua rahasia. Jangan commit `.env`.
3. Muat variabel environment dari `.env` menggunakan terminal/IDE atau alat lokal pilihan Anda (misalnya `python-dotenv`/PowerShell).
4. Jalankan:

   ```powershell
   uvicorn telegram_pos_bot:app --host 0.0.0.0 --port 8000
   ```

Endpoint kesehatan: `GET /`. Endpoint webhook: `POST /telegram/webhook`.

## Menghubungkan Telegram

Deploy backend ke hosting HTTPS, lalu set webhook satu kali dengan Telegram `setWebhook`:

- URL: `https://<domain-backend>/telegram/webhook`
- Sertakan `secret_token` yang sama dengan `TELEGRAM_WEBHOOK_SECRET`.

Telegram mengirim secret tersebut pada header `X-Telegram-Bot-Api-Secret-Token`. Jangan gunakan polling bersamaan dengan webhook.

## Data yang dipakai saat ini

Bot hanya mengambil hasil RPC `pos_dashboard()` yang ada di schema teman Anda. Jadi model hanya bisa menjawab ringkasan hari ini: omzet, laba kotor, jumlah transaksi, produk aktif, dan jumlah produk stok rendah. Pertanyaan tentang nama produk terlaris, riwayat tanggal lain, atau detail transaksi memerlukan query/RPC tambahan setelah kebutuhan dan aturan akses dikonfirmasi.

## Catatan sebelum demo

- `pos_dashboard()` menghitung tanggal dengan zona waktu `Asia/Jakarta`, seperti SQL yang diberikan.
- Uji dengan akun bot dan beberapa Telegram ID yang diizinkan sebelum demo skripsi.
- Jangan masukkan data pelanggan yang tidak diperlukan ke prompt OpenAI.
- Periksa dan sesuaikan model OpenAI yang tersedia di akun Anda melalui environment variable `OPENAI_MODEL`.

