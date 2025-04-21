#!/usr/bin/env python3
"""
Конфигурация приложения.
Модуль для хранения настроек и параметров приложения.
"""

import os
import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class Config:
    """Класс для хранения и управления настройками приложения"""
    
    # Имя файла конфигурации
    CONFIG_FILE = os.path.expanduser("%USERPROFILE%\.tg_cli_config.json")
    
    # Имя файла сессии Telegram
    DEFAULT_SESSION_NAME = os.path.expanduser("%USERPROFILE%\.tg_cli_session")
    
    # Значения по умолчанию
    DEFAULT_CONFIG = {
        "api_id": ххххх,
        "api_hash": "YYYYY",
        "session_name": DEFAULT_SESSION_NAME,
        "messages_limit": 30,
        "dialogs_limit": 100,
        "show_all_dialogs": False,
        "color_scheme": {
            "header": "cyan",
            "unread": "green",
            "selected": "yellow",
            "error": "red"
        }
    }
    
    def __init__(self):
        """Инициализация конфигурации"""
        self.config = self.DEFAULT_CONFIG.copy()
        self.load_config()
    
    def load_config(self):
        """Загрузка конфигурации из файла"""
        try:
            if os.path.exists(self.CONFIG_FILE):
                with open(self.CONFIG_FILE, 'r') as f:
                    loaded_config = json.load(f)
                    # Обновление текущей конфигурации загруженными значениями
                    self.config.update(loaded_config)
                    logger.info(f"Конфигурация загружена из {self.CONFIG_FILE}")
            else:
                # Если файла конфигурации нет, проверяем переменные окружения
                self._load_from_env()
                # Сохраняем начальную конфигурацию
                self.save_config()
                
        except Exception as e:
            logger.error(f"Ошибка загрузки конфигурации: {e}")
            
            # В случае ошибки проверяем переменные окружения
            self._load_from_env()
    
    def _load_from_env(self):
        """Загрузка конфигурации из переменных окружения"""
        # API ID и Hash можно получить из переменных окружения
        api_id = os.environ.get("TG_API_ID")
        api_hash = os.environ.get("TG_API_HASH")
        
        if api_id:
            self.config["api_id"] = int(api_id)
            logger.info("API ID загружен из переменной окружения")
            
        if api_hash:
            self.config["api_hash"] = api_hash
            logger.info("API Hash загружен из переменной окружения")
    
    def save_config(self):
        """Сохранение конфигурации в файл"""
        try:
            # Создаем директорию для файла, если ее нет
            os.makedirs(os.path.dirname(self.CONFIG_FILE), exist_ok=True)
            
            # Сохранение конфигурации в файл
            with open(self.CONFIG_FILE, 'w') as f:
                json.dump(self.config, f, indent=4)
                logger.info(f"Конфигурация сохранена в {self.CONFIG_FILE}")
                
        except Exception as e:
            logger.error(f"Ошибка сохранения конфигурации: {e}")
    
    def update_config(self, key: str, value: Any):
        """
        Обновление значения конфигурации.
        
        Args:
            key: Ключ конфигурации
            value: Новое значение
        """
        if key in self.config:
            self.config[key] = value
            self.save_config()
        else:
            logger.warning(f"Попытка обновить несуществующий ключ конфигурации: {key}")
    
    def get_value(self, key: str, default: Optional[Any] = None) -> Any:
        """
        Получение значения конфигурации.
        
        Args:
            key: Ключ конфигурации
            default: Значение по умолчанию, если ключ не найден
            
        Returns:
            Значение конфигурации или default, если ключ не найден
        """
        return self.config.get(key, default)
    
    # Свойства для прямого доступа к основным настройкам
    
    @property
    def API_ID(self) -> Optional[int]:
        """API ID для работы с Telegram"""
        return self.config.get("api_id")
    
    @property
    def API_HASH(self) -> Optional[str]:
        """API Hash для работы с Telegram"""
        return self.config.get("api_hash")
    
    @property
    def SESSION_NAME(self) -> str:
        """Имя файла сессии"""
        return self.config.get("session_name", self.DEFAULT_SESSION_NAME)
    
    @property
    def MESSAGES_LIMIT(self) -> int:
        """Лимит загружаемых сообщений"""
        return self.config.get("messages_limit", 30)
    
    @property
    def DIALOGS_LIMIT(self) -> int:
        """Лимит загружаемых диалогов"""
        return self.config.get("dialogs_limit", 100)
    
    @property
    def SHOW_ALL_DIALOGS(self) -> bool:
        """Показывать все диалоги или только с непрочитанными сообщениями"""
        return self.config.get("show_all_dialogs", False)
    
    @property
    def COLOR_SCHEME(self) -> Dict[str, str]:
        """Цветовая схема интерфейса"""
        return self.config.get("color_scheme", self.DEFAULT_CONFIG["color_scheme"])
    
    def validate(self) -> bool:
        """
        Проверка валидности конфигурации.
        
        Returns:
            True если конфигурация валидна, иначе False
        """
        # Проверка необходимых параметров для работы с Telegram API
        if not self.API_ID or not self.API_HASH:
            logger.error("Не заданы API_ID или API_HASH. Используйте переменные окружения TG_API_ID и TG_API_HASH или файл конфигурации.")
            return False
        
        return True
