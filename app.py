#!/usr/bin/env python3
"""
Консольный клиент Telegram.
Главный модуль, отвечающий за запуск приложения.
"""

import asyncio
import logging
import os
import sys
import signal
from typing import Optional

# Импорт внутренних модулей
from config import Config
from api.client import TelegramClient
from cli import TelegramCLI
from state import StateManager


# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='tg_cli.log'
)
logger = logging.getLogger(__name__)


class TelegramConsoleApp:
    """Основной класс приложения"""
    
    def __init__(self):
        self.config = Config()
        self.client: Optional[TelegramClient] = None
        self.cli: Optional[TelegramCLI] = None
        self.state_manager: Optional[StateManager] = None
        
    async def initialize(self):
        """Инициализация компонентов приложения"""
        try:
            # Инициализация клиента Telegram
            self.client = TelegramClient(
                session_name=self.config.SESSION_NAME,
                api_id=self.config.API_ID,
                api_hash=self.config.API_HASH
            )
            
            # Инициализация менеджера состояний
            self.state_manager = StateManager()
            
            # Инициализация консольного интерфейса
            self.cli = TelegramCLI(self.client, self.state_manager)
            
            # Регистрация обработчика сигнала прерывания (Ctrl+C)
            signal.signal(signal.SIGINT, self._handle_interrupt)
            
            # Подключение к Telegram
            await self.client.connect()
            
            # Проверка авторизации
            if not await self.client.is_user_authorized():
                await self._handle_authorization()
                
            logger.info("Приложение инициализировано успешно")
            
        except Exception as e:
            logger.error(f"Ошибка инициализации: {e}")
            await self.shutdown()
            sys.exit(1)
    
    async def _handle_authorization(self):
        """Обработка процесса авторизации"""
        try:
            print("Необходима авторизация в Telegram.")
            phone = input("Введите номер телефона: ")
            
            # Отправка кода авторизации
            await self.client.send_code_request(phone)
            
            # Запрос кода подтверждения у пользователя
            code = input("Введите код подтверждения: ")
            
            # Авторизация
            await self.client.sign_in(phone, code)
            print("Авторизация успешна!")
            
        except Exception as e:
            logger.error(f"Ошибка авторизации: {e}")
            await self.shutdown()
            sys.exit(1)
    
    def _handle_interrupt(self, sig, frame):
        """Обработчик сигнала прерывания (Ctrl+C)"""
        print("\nЗавершение работы...")
        asyncio.create_task(self.shutdown())
    
    async def run(self):
        """Запуск основного цикла приложения"""
        await self.initialize()
        try:
            # Запуск консольного интерфейса
            await self.cli.run()
        except Exception as e:
            logger.error(f"Ошибка в основном цикле: {e}")
        finally:
            await self.shutdown()
    
    async def shutdown(self):
        """Корректное завершение работы приложения"""
        if self.cli:
            await self.cli.shutdown()
        
        if self.client:
            await self.client.disconnect()
        
        logger.info("Приложение завершено")


def main():
    """Точка входа в приложение"""
    # Создание и запуск приложения
    app = TelegramConsoleApp()
    
    # Получение или создание цикла событий
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    try:
        loop.run_until_complete(app.run())
    except KeyboardInterrupt:
        pass
    finally:
        loop.close()


if __name__ == "__main__":
    main()