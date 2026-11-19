from __future__ import annotations

import logging
import os
from typing import Any

import httpx
from fastapi import FastAPI, Header, HTTPException, Request
from openai import AsyncOpenAI

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("telegram_pos_bot")

app = FastAPI(title="Telegram POS Assistant")
openai_client = AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"])

TELEGRAM_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_WEBHOOK_SECRET = os.environ["TELEGRAM_WEBHOOK_SECRET"]
SUPABASE_URL = os.environ["SUPABASE_URL"].rstrip("/")
SUPABASE_PUBLISHABLE_KEY = os.environ["SUPABASE_PUBLISHABLE_KEY"]
SUPABASE_BOT_EMAIL = os.environ["SUPABASE_BOT_EMAIL"]
SUPABASE_BOT_PASSWORD = os.environ["SUPABASE_BOT_PASSWORD"]
ALLOWED_TELEGRAM_IDS = {
    int(value.strip())
    for value in os.environ.get("ALLOWED_TELEGRAM_IDS", "").split(",")
    if value.strip()
}
MODEL = os.environ.get("OPENAI_MODEL", "gpt-5.4-mini")


async def supabase_access_token(client: httpx.AsyncClient) -> str:
    """Sign in as a dedicated Supabase Auth user for this request."""
    response = await client.post(
        f"{SUPABASE_URL}/auth/v1/token?grant_type=password",
        headers={"apikey": SUPABASE_PUBLISHABLE_KEY},
        json={"email": SUPABASE_BOT_EMAIL, "password": SUPABASE_BOT_PASSWORD},
    )
    response.raise_for_status()
    return response.json()["access_token"]


async def get_dashboard(client: httpx.AsyncClient, access_token: str) -> dict[str, Any]:
    response = await client.post(
        f"{SUPABASE_URL}/rest/v1/rpc/pos_dashboard",
        headers={
            "apikey": SUPABASE_PUBLISHABLE_KEY,
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
        json={},
    )
    response.raise_for_status()
    return response.json()


async def ask_openai(question: str, dashboard: dict[str, Any]) -> str:
    response = await openai_client.responses.create(
        model=MODEL,
        instructions=(
            "Anda adalah asisten laporan POS. Jawab dalam bahasa Indonesia dengan ringkas. "
            "Gunakan hanya data JSON yang diberikan. Jangan mengarang angka. "
            "Jika data tidak cukup untuk menjawab, katakan data yang tersedia belum mencukupi. "
            "Angka penjualan dan laba menggunakan rupiah."
        ),
        input=(
            f"Data dashboard POS (hari ini, zona waktu Asia/Jakarta): {dashboard}\n"
            f"Pertanyaan: {question}"
        ),
    )
    return response.output_text or "Maaf, saya belum bisa menyusun jawaban."


async def send_telegram_message(client: httpx.AsyncClient, chat_id: int, text: str) -> None:
    response = await client.post(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        json={"chat_id": chat_id, "text": text[:4000]},
    )
    response.raise_for_status()


@app.get("/")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "telegram-pos-assistant"}


@app.post("/telegram/webhook")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
) -> dict[str, bool]:
    if x_telegram_bot_api_secret_token != TELEGRAM_WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="Invalid webhook secret")

    update = await request.json()
    message = update.get("message") or update.get("edited_message")
    if not message or not message.get("text"):
        return {"ok": True}

    sender_id = int(message.get("from", {}).get("id", 0))
    chat_id = int(message["chat"]["id"])
    question = message["text"].strip()

    if not ALLOWED_TELEGRAM_IDS or sender_id not in ALLOWED_TELEGRAM_IDS:
        async with httpx.AsyncClient(timeout=20) as client:
            await send_telegram_message(
                client, chat_id,
                "Akses bot belum diizinkan. Minta admin menambahkan Telegram user ID Anda.",
            )
        return {"ok": True}

    if question == "/start":
        reply = (
            "Halo! Saya bisa menjawab pertanyaan berdasarkan ringkasan POS hari ini.\n"
            "Contoh: Berapa penjualan dan laba hari ini?"
        )
    else:
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                token = await supabase_access_token(client)
                dashboard = await get_dashboard(client, token)
            reply = await ask_openai(question, dashboard)
        except Exception:
            # Detail error tetap di log server, tidak dikirim ke chat pengguna.
            logger.exception("Failed to process Telegram update")
            reply = "Maaf, bot sedang mengalami kendala saat mengambil atau mengolah data POS."

    async with httpx.AsyncClient(timeout=20) as client:
        await send_telegram_message(client, chat_id, reply)
    return {"ok": True}


