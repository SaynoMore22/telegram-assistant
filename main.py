import asyncio
import logging
import os
from collections import defaultdict, deque

from dotenv import load_dotenv
from telethon import TelegramClient, events
from telethon.tl.types import User
from anthropic import Anthropic

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("assistant")

API_ID = int(os.environ["TG_API_ID"])
API_HASH = os.environ["TG_API_HASH"]
PHONE = os.environ["TG_PHONE"]
SESSION = os.environ.get("TG_SESSION", "assistant_session")

ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-haiku-4-5")

HISTORY_LIMIT = int(os.environ.get("HISTORY_LIMIT", "20"))
IGNORE_CHAT_IDS = {
    int(x) for x in os.environ.get("IGNORE_CHAT_IDS", "").split(",") if x.strip()
}

PERSONA_PATH = os.path.join(os.path.dirname(__file__), "persona.md")

anthropic = Anthropic(api_key=ANTHROPIC_API_KEY)
client = TelegramClient(SESSION, API_ID, API_HASH)

history: dict[int, deque] = defaultdict(lambda: deque(maxlen=HISTORY_LIMIT))


def load_persona() -> str:
    try:
        with open(PERSONA_PATH, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return ""


def build_system_prompt() -> str:
    persona = load_persona()
    return (
        "Ты — личный ассистент, который отвечает в Telegram от лица владельца аккаунта "
        "в его личных сообщениях. Пиши коротко, естественно, как обычный человек в мессенджере, "
        "без канцелярита и длинных вступлений. Не представляйся ассистентом или ИИ, если тебя "
        "прямо не спросили, кто ты. Если не уверен в ответе — не выдумывай факты, лучше ответь "
        "уклончиво или предложи, что владелец аккаунта ответит позже сам.\n\n"
        f"Информация о владельце аккаунта:\n{persona}"
    )


async def generate_reply(chat_id: int, user_text: str) -> str:
    history[chat_id].append({"role": "user", "content": user_text})

    response = await asyncio.to_thread(
        anthropic.messages.create,
        model=MODEL,
        max_tokens=400,
        system=build_system_prompt(),
        messages=list(history[chat_id]),
    )
    reply = "".join(block.text for block in response.content if block.type == "text").strip()
    history[chat_id].append({"role": "assistant", "content": reply})
    return reply


@client.on(events.NewMessage(incoming=True))
async def handler(event):
    if not event.is_private:
        return

    sender = await event.get_sender()
    if not isinstance(sender, User) or sender.bot or sender.is_self:
        return

    if event.chat_id in IGNORE_CHAT_IDS:
        return

    text = event.raw_text.strip()
    if not text:
        return

    log.info("Входящее от %s (%s): %s", sender.id, sender.username, text[:80])

    async with client.action(event.chat_id, "typing"):
        try:
            reply = await generate_reply(event.chat_id, text)
        except Exception:
            log.exception("Ошибка генерации ответа для чата %s", event.chat_id)
            return
        await asyncio.sleep(min(2 + len(reply) / 20, 8))

    if reply:
        await event.reply(reply)
        log.info("Ответ в чат %s: %s", event.chat_id, reply[:80])


async def main():
    await client.start(phone=PHONE)
    log.info("Ассистент запущен, слушаю личные сообщения...")
    await client.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(main())
