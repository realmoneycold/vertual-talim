# 🩺 Propedevtika Telegram Bot

A highly modular, production-ready, asynchronous Telegram Bot built with `aiogram v3` and SQLite.

## 📁 Project Architecture

```
/home/ahror/Documents/Klent1/
├── .env                  # Environment secrets (Token, Admin IDs, DB file)
├── requirements.txt      # Python dependencies
├── README.md             # Project documentation
├── config.py             # Configuration loader & validation
├── database.py           # Thread-safe SQLite database manager
├── keyboards.py          # Unified keyboard interfaces
├── bot.py                # Main bot runner (startup/shutdown, polling)
├── handlers/             # Bot route handlers (modular routers)
│   ├── __init__.py       # Handlers aggregator
│   ├── start.py          # /start flow & registration requests
│   ├── admin.py          # /admin controls, broadcast, callback actions
│   └── courses.py        # Course information & WebApp integrations
└── utils/
    ├── __init__.py
    └── logger.py         # Advanced logging with daily rotating file outputs
```

## ✨ Features

- 🔐 **Multi-Admin Authorization:** Both administrators receive approval requests, and only authorized admins can approve, deny, or ban users.
- 📂 **Structured Architecture:** Built using `aiogram v3` router architecture for high clean-code scalability.
- 🗄️ **Database Persistence:** Uses a robust, thread-safe local SQLite database (`database.db`) instead of raw `.txt` files.
- 🚫 **Ban/Blacklist System:** Blocked/banned users cannot spam admins or re-trigger approval requests.
- 📢 **Broadcast Feature (Admin):** Admins can broadcast any message (text, photos, videos, formatting, etc.) to all approved users safely.
- 📊 **Admin Stats Panel:** Check active users, pending queue, and banned counts easily via `/admin` dashboard.
- 📝 **Failsafe Logging:** Real-time console logs and automatic error logging to rotating files (`bot.log`).

## 🚀 How to Run the Bot

1. **Activate Virtual Environment:**
   ```bash
   source venv/bin/bin/activate
   ```
2. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
3. **Configure Environment:**
   Configure your tokens and Admin IDs in the generated `.env` file (done automatically).
4. **Run the Bot:**
   ```bash
   python bot.py
   ```

*Note: The old files (`main.py` and `gemini.py`) have been backed up in the `old_backup/` directory.*
