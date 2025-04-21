#!/usr/bin/env python3
"""
Менеджер кеширования данных.
Модуль для кеширования диалогов и сообщений для уменьшения количества запросов к API.
"""

import os
import json
import logging
import time
import datetime
from typing import Dict, List, Optional, Any, Union

logger = logging.getLogger(__name__)


class CacheManager:
    """Класс для кеширования данных из Telegram API"""
    
    def __init__(self, cache_dir: Optional[str] = None, max_age_minutes: int = 5):
        """
        Инициализация кеш-менеджера.
        
        Args:
            cache_dir: Директория для хранения кеша (по умолчанию ~/.tg_cli_cache)
            max_age_minutes: Максимальное время хранения кеша в минутах
        """
        # Настройка директории кеша
        if cache_dir:
            self.cache_dir = cache_dir
        else:
            self.cache_dir = os.path.expanduser("~/.tg_cli_cache")
        
        # Создание директории кеша, если её нет
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Максимальное время хранения кеша
        self.max_age_minutes = max_age_minutes
        
        # Кеш диалогов
        self.dialogs_cache: Dict[str, Dict[str, Any]] = {
            "data": None,
            "timestamp": 0,
            "only_unread": False
        }
        
        # Кеш сообщений по ID диалога
        self.messages_cache: Dict[int, Dict[str, Any]] = {}
        
        # Загрузка кеша из файлов
        self._load_cache()
        
        logger.info(f"Кеш-менеджер инициализирован в {self.cache_dir}")
    
    def get_dialogs(self, only_unread: bool = False) -> Optional[List[Any]]:
        """
        Получение кешированных диалогов.
        
        Args:
            only_unread: Признак фильтрации только непрочитанных диалогов
            
        Returns:
            Список диалогов или None, если кеш устарел или отсутствует
        """
        # Проверка наличия и актуальности кеша
        cache_valid = (
            self.dialogs_cache["data"] is not None and
            self.dialogs_cache["only_unread"] == only_unread and
            time.time() - self.dialogs_cache["timestamp"] < self.max_age_minutes * 60
        )
        
        if cache_valid:
            logger.debug("Использование кешированных диалогов")
            return self.dialogs_cache["data"]
        
        logger.debug("Кеш диалогов отсутствует или устарел")
        return None
    
    def store_dialogs(self, dialogs: List[Any], only_unread: bool = False):
        """
        Сохранение диалогов в кеш.
        
        Args:
            dialogs: Список диалогов
            only_unread: Признак фильтрации только непрочитанных диалогов
        """
        self.dialogs_cache = {
            "data": dialogs,
            "timestamp": time.time(),
            "only_unread": only_unread
        }
        
        logger.debug(f"Кеширование {len(dialogs)} диалогов")
    
    def get_messages(self, dialog_id: int) -> Optional[List[Any]]:
        """
        Получение кешированных сообщений для диалога.
        
        Args:
            dialog_id: ID диалога
            
        Returns:
            Список сообщений или None, если кеш устарел или отсутствует
        """
        # Проверка наличия и актуальности кеша
        if dialog_id in self.messages_cache:
            cache_entry = self.messages_cache[dialog_id]
            
            if time.time() - cache_entry["timestamp"] < self.max_age_minutes * 60:
                logger.debug(f"Использование кешированных сообщений для диалога {dialog_id}")
                return cache_entry["data"]
        
        logger.debug(f"Кеш сообщений для диалога {dialog_id} отсутствует или устарел")
        return None
    
    def store_messages(self, dialog_id: int, messages: List[Any]):
        """
        Сохранение сообщений в кеш.
        
        Args:
            dialog_id: ID диалога
            messages: Список сообщений
        """
        self.messages_cache[dialog_id] = {
            "data": messages,
            "timestamp": time.time()
        }
        
        logger.debug(f"Кеширование {len(messages)} сообщений для диалога {dialog_id}")
    
    def invalidate_dialog_cache(self):
        """Инвалидация кеша диалогов"""
        self.dialogs_cache["data"] = None
        logger.debug("Кеш диалогов инвалидирован")
    
    def invalidate_messages_cache(self, dialog_id: Optional[int] = None):
        """
        Инвалидация кеша сообщений.
        
        Args:
            dialog_id: ID диалога (если None, инвалидируются все диалоги)
        """
        if dialog_id is None:
            self.messages_cache = {}
            logger.debug("Кеш всех сообщений инвалидирован")
        elif dialog_id in self.messages_cache:
            del self.messages_cache[dialog_id]
            logger.debug(f"Кеш сообщений для диалога {dialog_id} инвалидирован")
    
    def save_cache(self):
        """Сохранение кеша на диск"""
        try:
            # Сохранение кеша диалогов
            dialogs_cache_path = os.path.join(self.cache_dir, "dialogs_cache.json")
            with open(dialogs_cache_path, 'w') as f:
                # Сохраняем только timestamp и only_unread, данные не сохраняем
                cache_data = {
                    "timestamp": self.dialogs_cache["timestamp"],
                    "only_unread": self.dialogs_cache["only_unread"]
                }
                json.dump(cache_data, f)
            
            # Сохранение метаданных кеша сообщений
            messages_cache_path = os.path.join(self.cache_dir, "messages_cache.json")
            with open(messages_cache_path, 'w') as f:
                # Сохраняем только идентификаторы диалогов и timestamp, данные не сохраняем
                cache_data = {
                    str(dialog_id): {
                        "timestamp": entry["timestamp"]
                    }
                    for dialog_id, entry in self.messages_cache.items()
                }
                json.dump(cache_data, f)
            
            logger.info("Кеш сохранен на диск")
            
        except Exception as e:
            logger.error(f"Ошибка при сохранении кеша: {e}")
    
    def _load_cache(self):
        """Загрузка кеша с диска"""
        try:
            # Загрузка кеша диалогов
            dialogs_cache_path = os.path.join(self.cache_dir, "dialogs_cache.json")
            if os.path.exists(dialogs_cache_path):
                with open(dialogs_cache_path, 'r') as f:
                    cache_data = json.load(f)
                    self.dialogs_cache["timestamp"] = cache_data.get("timestamp", 0)
                    self.dialogs_cache["only_unread"] = cache_data.get("only_unread", False)
            
            # Загрузка метаданных кеша сообщений
            messages_cache_path = os.path.join(self.cache_dir, "messages_cache.json")
            if os.path.exists(messages_cache_path):
                with open(messages_cache_path, 'r') as f:
                    cache_data = json.load(f)
                    for dialog_id_str, entry in cache_data.items():
                        dialog_id = int(dialog_id_str)
                        self.messages_cache[dialog_id] = {
                            "data": None,
                            "timestamp": entry.get("timestamp", 0)
                        }
            
            logger.info("Кеш загружен с диска")
            
        except Exception as e:
            logger.error(f"Ошибка при загрузке кеша: {e}")
    
    def clean_old_cache(self):
        """Очистка устаревшего кеша"""
        current_time = time.time()
        max_age_seconds = self.max_age_minutes * 60
        
        # Проверка кеша диалогов
        if current_time - self.dialogs_cache["timestamp"] > max_age_seconds:
            self.invalidate_dialog_cache()
        
        # Проверка кеша сообщений
        dialogs_to_invalidate = []
        for dialog_id, entry in self.messages_cache.items():
            if current_time - entry["timestamp"] > max_age_seconds:
                dialogs_to_invalidate.append(dialog_id)
        
        # Инвалидация устаревших кешей сообщений
        for dialog_id in dialogs_to_invalidate:
            self.invalidate_messages_cache(dialog_id)
        
        if dialogs_to_invalidate:
            logger.debug(f"Очищен устаревший кеш {len(dialogs_to_invalidate)} диалогов")