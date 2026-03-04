# 🏍️ Pol Ferrer Academy Offers Bot

Telegram bot that automatically notifies you when new offers appear at [Pol Ferrer Academy website](https://www.polferrer.com/).

## 🚀 What does it do?

This bot monitors the Pol Ferrer website and sends you an instant notification when it detects new available offers.

**Never miss an offer again!**

## 📱 Commands

- `/start` - Subscribe to receive automatic alerts
- `/offers` - View currently available offers
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
   ```

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