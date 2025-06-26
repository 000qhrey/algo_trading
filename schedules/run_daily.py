"""
Cron‑ready wrapper.  E.g. `python schedules/run_daily.py` then leave running.
"""
import schedule
import time
from datetime import datetime
from main import run
from utils.logger import setup_logger

logger = setup_logger()

def job():
    logger.info(f"Running scheduled job @ {datetime.now()}")
    run()

schedule.every().day.at("16:00").do(job)   # market close IST~15:30

if __name__ == "__main__":
    logger.info("Scheduler started.")
    while True:
        schedule.run_pending()
        time.sleep(60) 