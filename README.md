# 🏍️ Pol Ferrer Academy Offers Bot

Telegram bot that automatically notifies you when new offers appear at [Pol Ferrer Academy website](https://www.polferrer.com/).

## 🚀 What does it do?

This bot monitors the Pol Ferrer website and sends you an instant notification when it detects new available offers or scheduled events (courses, campuses, etc.).

**Never miss an offer or event again!**

## 📱 Commands

- `/start` - Subscribe to receive automatic alerts
- `/offers` - View currently available offers
- `/events` - View scheduled events
- `/stop` - Cancel subscription
- `/help` - Help and bot information

## 🔧 Installation (for developers)

1. **Clone the repository**

   ```bash
   git clone <repository-url>
   cd PolFerrerAcademyOffers
   ```

2. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

3. **Configure bot token**

   Create `.env` file:

   ```env
   BOT_TOKEN=your_telegram_token
   # Optional: expose the bot's stats, and the username they name
   # BOT_STATS_ADDR=:9180
   # BOT_NAME=PolAcademyOffersBot
   ```

   With `BOT_STATS_ADDR` set, every update is counted (`bot_stats.py`) and exposed as the
   [/bot-stats document](https://github.com/PlatanosVerdes/gonana#botstats-the-bot-stats-contract).
   It lists names: never publish that port. The people are kept in `data/bot-stats.json`.

4. **Run**
   ```bash
   python main.py
   ```

### With Docker

```bash
docker build -t pol-offers-bot .
docker run -d --name pol-bot --env-file .env pol-offers-bot
```
---

## Note for Pol

This bot was built out of pure admiration and a slightly unhealthy refresh-button habit, not evil mastermind energy. 🫶

If your offers start disappearing faster than usual… we promise it’s just enthusiasm. 🏍️💨