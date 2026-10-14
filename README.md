# Telegram-ассистент (userbot)

Отвечает от твоего имени в личных сообщениях Telegram, используя Claude (Anthropic API)
через Telethon (MTProto, работает через твой личный аккаунт, а не отдельного бота).

⚠️ Это работает через личный аккаунт, а не Bot API — формально это нарушает
[Terms of Service Telegram](https://core.telegram.org/api/terms) для ботов на пользовательских
аккаунтах. Риск минимальный при разумном использовании (10-15 сообщений/день, без спама),
но помни, что аккаунт теоретически может быть ограничен.

## 1. Получить учётные данные

**Telegram API (обязательно, бесплатно):**
1. Зайди на https://my.telegram.org → Log in → API development tools
2. Создай приложение (любое название), получишь `api_id` и `api_hash`

**Anthropic API (обязательно, платно по токенам):**
1. https://console.anthropic.com → API Keys → Create Key
2. Пополни баланс (при твоём объёме сообщений — пары долларов хватит надолго)

## 2. Настройка

```bash
pip install -r requirements.txt
cp .env.example .env
```

Заполни `.env`: `TG_API_ID`, `TG_API_HASH`, `TG_PHONE`, `ANTHROPIC_API_KEY`.

Заполни [persona.md](persona.md) — кто ты, как отвечать, что нельзя обещать.

## 3. Первый запуск (локально, для логина)

```bash
python main.py
```

При первом запуске Telethon спросит код из Telegram (придёт в само приложение) и,
если включена двухфакторка, пароль. После этого создастся файл сессии
(`assistant_session.session`) — он и логинит тебя дальше без повторного ввода кода.

**Файл сессии = полный доступ к аккаунту, храни его так же аккуратно, как пароль.**
Не коммить `.env` и `*.session` в git (уже добавлено в `.gitignore`).

## 4. Деплой на VPS

Когда сессия создана локально:

1. Возьми любой недорогой VPS (Ubuntu 22.04+), например Timeweb, Selectel, Hetzner — от ~200-300₽/мес.
2. Залей на сервер весь проект **вместе с `.env` и файлом `*.session`**, чтобы не логиниться заново:
   ```bash
   scp -r . user@your-server:/opt/telegram-assistant
   ```
3. На сервере:
   ```bash
   cd /opt/telegram-assistant
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
4. Проверь, что стартует без интерактивного ввода (сессия уже есть):
   ```bash
   python main.py
   ```
5. Заверни в systemd-сервис, чтобы работал постоянно и поднимался после перезагрузки
   (пример юнита — `assistant.service` в этой папке).

```bash
sudo cp assistant.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now assistant
sudo journalctl -u assistant -f   # логи
```

## Настройки в .env

- `IGNORE_CHAT_IDS` — список chat_id, которым бот не должен отвечать (например, себе самому
  в "Избранное" или близким, с которыми хочешь общаться сам). Получить chat_id можно из логов
  (`main.py` логирует `sender.id` для каждого входящего).
- `HISTORY_LIMIT` — сколько последних сообщений диалога помнит ассистент (на чат).
- `ANTHROPIC_MODEL` — по умолчанию `claude-haiku-4-5`, дешёвая модель, для 10-15 сообщений/день
  расходы — центы в месяц.
