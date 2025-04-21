#!/usr/bin/env python3
"""
Клиент для взаимодействия с API Telegram.
Обертка над библиотекой Telethon для работы с Telegram API.
"""

import asyncio
import logging
from typing import List, Optional, Union, Dict, Any

from telethon import TelegramClient as TelethonClient
from telethon.tl.types import Message, Dialog, Channel, Chat, User
from telethon.tl.functions.messages import GetDialogsRequest, GetHistoryRequest
from telethon.errors import SessionPasswordNeededError

logger = logging.getLogger(__name__)


class TelegramClient:
    """Класс для взаимодействия с API Telegram"""
    
    def __init__(self, session_name: str, api_id: int, api_hash: str):
        """
        Инициализация клиента Telegram.
        
        Args:
            session_name: Имя файла сессии
            api_id: API ID, полученный на https://my.telegram.org
            api_hash: API Hash, полученный на https://my.telegram.org
        """
        self.client = TelethonClient(session_name, api_id, api_hash)
        self._me = None
    
    async def connect(self):
        """Подключение к Telegram API"""
        await self.client.connect()
    
    async def disconnect(self):
        """Отключение от Telegram API"""
        await self.client.disconnect()
    
    async def is_user_authorized(self) -> bool:
        """Проверка авторизации пользователя"""
        return await self.client.is_user_authorized()
    
    async def send_code_request(self, phone: str):
        """
        Отправка запроса на получение кода авторизации.
        
        Args:
            phone: Номер телефона
        """
        await self.client.send_code_request(phone)
    
    async def sign_in(self, phone: str, code: str, password: Optional[str] = None):
        """
        Авторизация в Telegram.
        
        Args:
            phone: Номер телефона
            code: Код авторизации
            password: Пароль двухфакторной аутентификации (если включена)
        """
        try:
            await self.client.sign_in(phone, code)
        except SessionPasswordNeededError:
            if password is None:
                raise ValueError("Требуется пароль двухфакторной аутентификации")
            await self.client.sign_in(password=password)
        
        # Обновление информации о текущем пользователе
        self._me = await self.client.get_me()
    
    async def get_me(self) -> User:
        """Получение информации о текущем пользователе"""
        if self._me is None:
            self._me = await self.client.get_me()
        return self._me
    
    async def get_dialogs(self, limit: int = 100, only_unread: bool = False) -> List[Dialog]:
        """
        Получение списка диалогов.
        
        Args:
            limit: Максимальное количество диалогов
            only_unread: Только диалоги с непрочитанными сообщениями
            
        Returns:
            Список диалогов
        """
        dialogs = await self.client(GetDialogsRequest(
            offset_date=None,
            offset_id=0,
            offset_peer=None,
            limit=limit,
            hash=0
        ))
        
        result = dialogs.dialogs
        
        # Фильтрация только непрочитанных диалогов, если требуется
        if only_unread:
            result = [dialog for dialog in result if dialog.unread_count > 0]
            
        return result
    
    async def get_dialog_entity(self, dialog_id: int) -> Union[Chat, Channel, User]:
        """
        Получение сущности диалога (чат, канал, пользователь).
        
        Args:
            dialog_id: ID диалога
            
        Returns:
            Сущность диалога
        """
        entity = await self.client.get_entity(dialog_id)
        return entity
    
    async def get_messages(self, entity, limit: int = 20) -> List[Message]:
        """
        Получение сообщений из диалога.
        
        Args:
            entity: Сущность диалога (чат, канал, пользователь)
            limit: Максимальное количество сообщений
            
        Returns:
            Список сообщений
        """
        messages = await self.client(GetHistoryRequest(
            peer=entity,
            limit=limit,
            offset_date=None,
            offset_id=0,
            max_id=0,
            min_id=0,
            add_offset=0,
            hash=0
        ))
        
        return messages.messages
    
    async def send_message(self, entity, message: str, reply_to: Optional[Message] = None):
        """
        Отправка сообщения.
        
        Args:
            entity: Сущность диалога (чат, канал, пользователь)
            message: Текст сообщения
            reply_to: Сообщение, на которое отвечаем (опционально)
        """
        await self.client.send_message(
            entity,
            message,
            reply_to=reply_to.id if reply_to else None
        )
    
    async def mark_as_read(self, entity, message: Optional[Message] = None):
        """
        Отметка сообщения или всего диалога как прочитанного.
        
        Args:
            entity: Сущность диалога (чат, канал, пользователь)
            message: Конкретное сообщение (если None, то весь диалог)
        """
        if message:
            await self.client.mark_read(entity, message.id)
        else:
            await self.client.mark_read(entity)