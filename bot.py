import os
import logging
import asyncio
from datetime import datetime, timezone
import requests
from telegram import Bot
from telegram.constants import ParseMode
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

# تنظیمات لاگینگ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# تنظیمات بات
BOT_TOKEN = os.environ.get('BOT_TOKEN', '7996544413:AAE_mTT90IMvF8NeI66KZL927obZmmY00MQ')
CHANNEL_USERNAME = os.environ.get('CHANNEL_USERNAME', '@tonpriceview')

# ایجاد نمونه بات
bot = Bot(token=BOT_TOKEN)


def get_toncoin_price():
    """دریافت قیمت Toncoin از Binance API"""
    try:
        # استفاده از Binance API برای دریافت قیمت TON/USDT
        url = 'https://api.binance.com/api/v3/ticker/price?symbol=TONUSDT'
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        price = float(data['price'])
        
        logger.info(f"قیمت Toncoin دریافت شد: ${price}")
        return price
        
    except requests.exceptions.RequestException as e:
        logger.error(f"خطا در دریافت قیمت از Binance: {e}")
        
        # تلاش با CoinGecko به عنوان backup
        try:
            url = 'https://api.coingecko.com/api/v3/simple/price?ids=the-open-network&vs_currencies=usd'
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            price = float(data['the-open-network']['usd'])
            logger.info(f"قیمت Toncoin از CoinGecko دریافت شد: ${price}")
            return price
        except Exception as backup_error:
            logger.error(f"خطا در دریافت قیمت از CoinGecko: {backup_error}")
            return None
    except Exception as e:
        logger.error(f"خطای غیرمنتظره: {e}")
        return None


async def send_price_to_channel():
    """ارسال قیمت Toncoin به کانال"""
    try:
        # دریافت قیمت
        price = get_toncoin_price()
        
        if price is None:
            logger.error("قیمت دریافت نشد، پست ارسال نمی‌شود")
            return
        
        # فرمت کردن قیمت با 3 رقم اعشار
        formatted_price = f"{price:.3f}"
        
        # ایجاد متن با فرمت bold
        message = f"<b>{formatted_price} $</b>"
        
        # دریافت زمان UTC
        current_time = datetime.now(timezone.utc)
        time_str = current_time.strftime('%Y-%m-%d %H:%M UTC')
        
        # ارسال پیام به کانال
        await bot.send_message(
            chat_id=CHANNEL_USERNAME,
            text=message,
            parse_mode=ParseMode.HTML
        )
        
        logger.info(f"قیمت به کانال ارسال شد: {formatted_price} $ در {time_str}")
        
    except Exception as e:
        logger.error(f"خطا در ارسال پیام به کانال: {e}")


async def main():
    """تابع اصلی برای اجرای بات"""
    try:
        # بررسی اتصال بات
        bot_info = await bot.get_me()
        logger.info(f"بات با موفقیت راه‌اندازی شد: @{bot_info.username}")
        
        # ارسال یک پیام تست
        logger.info("ارسال اولین قیمت...")
        await send_price_to_channel()
        
        # ایجاد scheduler
        scheduler = AsyncIOScheduler(timezone='UTC')
        
        # اضافه کردن job برای اجرای هر دقیقه
        # با استفاده از CronTrigger برای همگام‌سازی دقیق با دقیقه‌های UTC
        scheduler.add_job(
            send_price_to_channel,
            CronTrigger(second=0, timezone='UTC'),  # اجرا در ثانیه 0 هر دقیقه
            id='price_posting',
            name='Post Toncoin Price',
            replace_existing=True
        )
        
        scheduler.start()
        logger.info("Scheduler راه‌اندازی شد - بات هر دقیقه قیمت را پست می‌کند")
        
        # نگه داشتن بات در حالت اجرا
        while True:
            await asyncio.sleep(60)
            
    except Exception as e:
        logger.error(f"خطا در اجرای بات: {e}")
        raise


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("بات متوقف شد")
    except Exception as e:
        logger.error(f"خطای کلی: {e}")
```
