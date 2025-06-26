import requests
from utils.logger import setup_logger

logger = setup_logger()

class TelegramAlert:
    def __init__(self, bot_token: str, chat_id: str):
        self.base = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        self.chat_id = chat_id

    def send(self, msg: str):
        resp = requests.post(self.base, data={"chat_id": self.chat_id, "text": msg})
        if resp.ok:
            logger.info("Telegram alert sent.")
        else:
            logger.error(f"Failed to send Telegram alert: {resp.text}") 