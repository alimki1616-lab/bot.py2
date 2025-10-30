import os
import asyncio
import logging
from datetime import datetime, timezone
from telegram import Bot
from telegram.constants import ParseMode
from telegram.error import TelegramError
import aiohttp

# تنظیمات لاگ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# تنظیمات از محیط
BOT_TOKEN = os.getenv('BOT_TOKEN')
CHANNEL_USERNAME = os.getenv('CHANNEL_USERNAME', '@tonpriceview')

# API برای دریافت قیمت Toncoin
BINANCE_API = 'https://api.binance.com/api/v3/ticker/price?symbol=TONUSDT'
COINGECKO_API = 'https://api.coingecko.com/api/v3/simple/price?ids=the-open-network&vs_currencies=usd'


class TonPriceBot:
    def __init__(self, token, channel):
        self.bot = Bot(token=token)
        self.channel = channel
        self.session = None
        self.last_price = None

    async def get_ton_price(self):
        """دریافت قیمت Toncoin با retry"""
        # تلاش 3 بار
        for attempt in range(3):
            try:
                if not self.session:
                    self.session = aiohttp.ClientSession()
                
                # تلاش CoinGecko
                try:
                    async with self.session.get(COINGECKO_API, timeout=15) as response:
                        if response.status == 200:
                            data = await response.json()
                            price = float(data['the-open-network']['usd'])
                            logger.info(f"✅ قیمت از CoinGecko: {price}")
                            self.last_price = price
                            return price
                except Exception as e:
                    logger.warning(f"CoinGecko خطا (تلاش {attempt + 1}): {e}")
                
                # تلاش Binance
                try:
                    async with self.session.get(BINANCE_API, timeout=15) as response:
                        if response.status == 200:
                            data = await response.json()
                            price = float(data['price'])
                            logger.info(f"✅ قیمت از Binance: {price}")
                            self.last_price = price
                            return price
                except Exception as e:
                    logger.warning(f"Binance خطا (تلاش {attempt + 1}): {e}")
                
                # صبر قبل از تلاش بعدی
                if attempt < 2:
                    await asyncio.sleep(2)
                    
            except Exception as e:
                logger.error(f"خطا در تلاش {attempt + 1}: {e}")
        
        # اگر همه تلاش‌ها ناموفق بود، از قیمت قبلی استفاده کن
        if self.last_price:
            logger.warning(f"⚠️ استفاده از قیمت قبلی: {self.last_price}")
            return self.last_price
        
        return None

    async def format_message(self, price):
        """فرمت پیام به صورت بولد"""
        formatted_price = f"{price:.3f}"
        message = f"<b>{formatted_price} $</b>"
        return message

    async def send_price_update(self):
        """ارسال قیمت به کانال"""
        try:
            price = await self.get_ton_price()
            
            if price is None:
                logger.error("❌ نتوانستیم قیمت دریافت کنیم")
                return False
            
            message = await self.format_message(price)
            
            # ارسال پیام به کانال
            await self.bot.send_message(
                chat_id=self.channel,
                text=message,
                parse_mode=ParseMode.HTML
            )
            
            current_time = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
            logger.info(f"✅ قیمت ارسال شد: {price:.3f} $ - {current_time}")
            return True
            
        except TelegramError as e:
            logger.error(f"❌ خطای تلگرام: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ خطای غیرمنتظره: {e}")
            return False

    async def wait_until_next_minute(self):
        """صبر تا شروع دقیقه بعدی بر اساس UTC"""
        now = datetime.now(timezone.utc)
        seconds_until_next_minute = 60 - now.second - (now.microsecond / 1000000)
        
        logger.info(f"⏳ صبر {seconds_until_next_minute:.1f} ثانیه...")
        await asyncio.sleep(seconds_until_next_minute)

    async def run(self):
        """اجرای ربات"""
        logger.info("🚀 ربات شروع شد")
        logger.info(f"📢 کانال: {self.channel}")
        
        try:
            bot_info = await self.bot.get_me()
            logger.info(f"✅ ربات متصل: @{bot_info.username}")
            
            while True:
                await self.wait_until_next_minute()
                await self.send_price_update()
                
        except KeyboardInterrupt:
            logger.info("⛔ ربات متوقف شد")
        except Exception as e:
            logger.error(f"❌ خطای کلی: {e}")
            await asyncio.sleep(60)
            await self.run()
        finally:
            if self.session:
                await self.session.close()


async def main():
    """تابع اصلی"""
    if not BOT_TOKEN:
        logger.error("❌ BOT_TOKEN تنظیم نشده!")
        return
    
    bot = TonPriceBot(BOT_TOKEN, CHANNEL_USERNAME)
    await bot.run()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("⛔ برنامه متوقف شد")
