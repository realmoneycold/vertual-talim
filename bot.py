import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, BotCommandScopeDefault, BotCommandScopeChat

from config import Config
from database import Database
from handlers import get_handlers_router
from utils.logger import setup_logger

# Initialize logger first
setup_logger()
logger = logging.getLogger(__name__)

async def setup_bot_commands(bot: Bot):
    """Configures bot commands for autocomplete suggestions when typing '/'."""
    # 1. Default commands for ordinary users
    default_commands = [
        BotCommand(command="start", description="Botni qayta ishga tushirish"),
        BotCommand(command="help", description="Yordam va ko'rsatmalar"),
        BotCommand(command="yordam", description="Yordam va ko'rsatmalar (o'zbekcha)")
    ]
    await bot.set_my_commands(commands=default_commands, scope=BotCommandScopeDefault())
    
    # 2. Advanced commands specifically visible only to administrators
    admin_commands = [
        BotCommand(command="start", description="Botni qayta ishga tushirish"),
        BotCommand(command="help", description="Yordam va ko'rsatmalar"),
        BotCommand(command="yordam", description="Yordam va ko'rsatmalar (o'zbekcha)"),
        BotCommand(command="admin", description="Admin boshqaruv panelini ochish")
    ]
    for admin_id in Config.ADMIN_IDS:
        try:
            await bot.set_my_commands(
                commands=admin_commands,
                scope=BotCommandScopeChat(chat_id=admin_id)
            )
        except Exception as e:
            logger.warning(f"Could not register admin commands scope for admin {admin_id}: {e}")

async def on_startup(bot: Bot):
    """Event handler triggered when bot starts up."""
    logger.info("Bot starting up...")
    Config.validate()
    
    # Initialize DB
    Database()

    # Configure autocompletes
    await setup_bot_commands(bot)
    
    # Notify admins about startup
    for admin_id in Config.ADMIN_IDS:
        try:
            await bot.send_message(
                chat_id=admin_id, 
                text="🚀 <b>Bot muvaffaqiyatli ishga tushirildi!</b>", 
                parse_mode="HTML"
            )
        except Exception as e:
            logger.warning(f"Could not notify admin {admin_id} on startup: {e}")

async def on_shutdown(bot: Bot):
    """Event handler triggered when bot shuts down."""
    logger.info("Bot shutting down...")
    for admin_id in Config.ADMIN_IDS:
        try:
            await bot.send_message(
                chat_id=admin_id, 
                text="🛑 <b>Bot faoliyati to'xtatildi!</b>", 
                parse_mode="HTML"
            )
        except Exception as e:
            logger.warning(f"Could not notify admin {admin_id} on shutdown: {e}")

async def main():
    # Load and validate configs
    try:
        Config.validate()
    except ValueError as e:
        logger.critical(f"Configuration error: {e}")
        return

    # Initialize bot and dispatcher
    bot = Bot(token=Config.BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    # Include modular handler routers
    dp.include_router(get_handlers_router())

    # Register startup and shutdown hooks
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    # Delete webhook to prevent conflicts and start polling
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("Starting bot polling...")
        await dp.start_polling(bot)
    except Exception as e:
        logger.critical(f"Polling loop encountered an error: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped manually.")
