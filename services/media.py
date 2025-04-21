#!/usr/bin/env python3
"""
Обработчик медиа-контента.
Модуль для работы с медиа-сообщениями Telegram (фото, видео, документы и т.д.).
"""

import os
import logging
import time
import subprocess
import platform
from typing import Optional, Dict, Any, Union

logger = logging.getLogger(__name__)


class MediaHandler:
    """Класс для обработки медиа-контента из сообщений Telegram"""
    
    def __init__(self, client, download_dir: Optional[str] = None):
        """
        Инициализация обработчика медиа.
        
        Args:
            client: Экземпляр клиента Telegram
            download_dir: Директория для сохранения медиа-файлов
        """
        self.client = client
        
        # Настройка директории для загрузок
        if download_dir:
            self.download_dir = download_dir
        else:
            self.download_dir = os.path.expanduser("~/tg_cli_downloads")
        
        # Создание директории, если её нет
        os.makedirs(self.download_dir, exist_ok=True)
        
        logger.info(f"Обработчик медиа инициализирован, директория загрузок: {self.download_dir}")
    
    def get_media_info(self, message) -> Optional[Dict[str, Any]]:
        """
        Получение информации о медиа-контенте в сообщении.
        
        Args:
            message: Объект сообщения
            
        Returns:
            Словарь с информацией о медиа или None, если медиа отсутствует
        """
        if not message or not hasattr(message, 'media') or not message.media:
            return None
        
        # Определение типа медиа
        media_type = self._get_media_type(message)
        
        # Базовая информация
        media_info = {
            "type": media_type,
            "can_download": True,
            "filename": None,
            "size": None,
            "duration": None,
            "preview_text": f"[{media_type.upper()}]"
        }
        
        # Дополнительная информация в зависимости от типа
        if media_type == "photo":
            # Фотография
            if hasattr(message.media, "photo") and hasattr(message.media.photo, "sizes"):
                # Поиск самого большого размера
                biggest = None
                for size in message.media.photo.sizes:
                    if biggest is None or (hasattr(size, "w") and hasattr(size, "h") and 
                                          size.w * size.h > biggest.w * biggest.h):
                        biggest = size
                
                if biggest and hasattr(biggest, "w") and hasattr(biggest, "h"):
                    media_info["preview_text"] = f"[ФОТО {biggest.w}x{biggest.h}]"
                    media_info["width"] = biggest.w
                    media_info["height"] = biggest.h
        
        elif media_type == "document":
            # Документ
            if hasattr(message.media, "document"):
                doc = message.media.document
                
                # Размер файла
                if hasattr(doc, "size"):
                    size_kb = doc.size / 1024
                    if size_kb > 1024:
                        size_mb = size_kb / 1024
                        media_info["preview_text"] = f"[ДОКУМЕНТ {size_mb:.1f} МБ]"
                    else:
                        media_info["preview_text"] = f"[ДОКУМЕНТ {size_kb:.1f} КБ]"
                    
                    media_info["size"] = doc.size
                
                # Имя файла и MIME-тип
                if hasattr(doc, "attributes"):
                    for attr in doc.attributes:
                        if hasattr(attr, "file_name"):
                            media_info["filename"] = attr.file_name
                            media_info["preview_text"] = f"[ФАЙЛ: {attr.file_name}]"
                
                # MIME-тип
                if hasattr(doc, "mime_type"):
                    media_info["mime_type"] = doc.mime_type
        
        elif media_type in ["video", "animation"]:
            # Видео или GIF
            if hasattr(message.media, "document"):
                doc = message.media.document
                
                # Размер файла
                if hasattr(doc, "size"):
                    size_mb = doc.size / (1024 * 1024)
                    media_info["size"] = doc.size
                
                # Информация о видео
                if hasattr(doc, "attributes"):
                    for attr in doc.attributes:
                        # Размеры видео
                        if hasattr(attr, "w") and hasattr(attr, "h"):
                            media_info["width"] = attr.w
                            media_info["height"] = attr.h
                            
                        # Длительность
                        if hasattr(attr, "duration"):
                            media_info["duration"] = attr.duration
                            minutes = attr.duration // 60
                            seconds = attr.duration % 60
                            
                            if media_type == "video":
                                media_info["preview_text"] = f"[ВИДЕО {minutes}:{seconds:02d}]"
                            else:
                                media_info["preview_text"] = f"[GIF {attr.w}x{attr.h}]"
        
        elif media_type == "voice":
            # Голосовое сообщение
            if hasattr(message.media, "document"):
                doc = message.media.document
                
                # Длительность
                if hasattr(doc, "attributes"):
                    for attr in doc.attributes:
                        if hasattr(attr, "duration"):
                            media_info["duration"] = attr.duration
                            minutes = attr.duration // 60
                            seconds = attr.duration % 60
                            media_info["preview_text"] = f"[ГОЛОС {minutes}:{seconds:02d}]"
        
        elif media_type == "audio":
            # Аудио
            if hasattr(message.media, "document"):
                doc = message.media.document
                
                # Информация об аудио
                title = None
                performer = None
                duration = None
                
                if hasattr(doc, "attributes"):
                    for attr in doc.attributes:
                        if hasattr(attr, "title"):
                            title = attr.title
                        
                        if hasattr(attr, "performer"):
                            performer = attr.performer
                        
                        if hasattr(attr, "duration"):
                            duration = attr.duration
                
                if title and performer:
                    media_info["preview_text"] = f"[АУДИО: {performer} - {title}]"
                elif title:
                    media_info["preview_text"] = f"[АУДИО: {title}]"
                elif duration:
                    minutes = duration // 60
                    seconds = duration % 60
                    media_info["preview_text"] = f"[АУДИО {minutes}:{seconds:02d}]"
                
                media_info["title"] = title
                media_info["performer"] = performer
                media_info["duration"] = duration
        
        return media_info
    
    def _get_media_type(self, message) -> str:
        """
        Определение типа медиа-контента в сообщении.
        
        Args:
            message: Объект сообщения
            
        Returns:
            Строка с типом медиа
        """
        if not hasattr(message, 'media') or not message.media:
            return "text"
        
        media = message.media
        media_type = type(media).__name__.lower()
        
        if "photo" in media_type:
            return "photo"
        elif "document" in media_type:
            # Проверка специфических типов документов
            if hasattr(media, "document"):
                doc = media.document
                
                # Проверка MIME-типа
                if hasattr(doc, "mime_type"):
                    mime = doc.mime_type.lower()
                    
                    if mime.startswith("video/"):
                        return "video"
                    elif mime.startswith("audio/"):
                        return "audio"
                    elif mime == "image/gif":
                        return "animation"
                
                # Проверка атрибутов
                if hasattr(doc, "attributes"):
                    for attr in doc.attributes:
                        attr_type = type(attr).__name__.lower()
                        
                        if "voice" in attr_type:
                            return "voice"
                        elif "video" in attr_type:
                            return "video"
                        elif "audio" in attr_type:
                            return "audio"
                        elif "animated" in attr_type:
                            return "animation"
            
            return "document"
        elif "voice" in media_type:
            return "voice"
        elif "audio" in media_type:
            return "audio"
        elif "video" in media_type:
            return "video"
        elif "animation" in media_type or "gif" in media_type:
            return "animation"
        else:
            return "unknown"
    
    async def download_media(self, message) -> Optional[str]:
        """
        Загрузка медиа-контента сообщения.
        
        Args:
            message: Объект сообщения
            
        Returns:
            Путь к сохраненному файлу или None в случае ошибки
        """
        if not message or not hasattr(message, 'media') or not message.media:
            logger.warning("Попытка загрузки медиа из сообщения без медиа-контента")
            return None
        
        try:
            # Получение информации о медиа
            media_info = self.get_media_info(message)
            media_type = media_info.get("type") if media_info else "unknown"
            
            # Генерация имени файла
            filename = self._generate_filename(message, media_info)
            
            # Полный путь к файлу
            filepath = os.path.join(self.download_dir, filename)
            
            # Загрузка файла
            downloaded_path = await self.client.download_media(message, filepath)
            
            logger.info(f"Медиа '{media_type}' сохранено в '{downloaded_path}'")
            
            return downloaded_path
            
        except Exception as e:
            logger.error(f"Ошибка при загрузке медиа: {e}")
            return None
    
    def _generate_filename(self, message, media_info: Optional[Dict[str, Any]] = None) -> str:
        """
        Генерация имени файла для медиа-контента.
        
        Args:
            message: Объект сообщения
            media_info: Информация о медиа
            
        Returns:
            Имя файла
        """
        # Получение информации о медиа
        if media_info is None:
            media_info = self.get_media_info(message)
        
        # Базовое имя файла
        base_filename = f"tg_{message.id}_{int(time.time())}"
        
        # Если есть оригинальное имя файла, используем его
        if media_info and media_info.get("filename"):
            _, file_ext = os.path.splitext(media_info["filename"])
            if file_ext:
                return f"{base_filename}{file_ext}"
        
        # Добавление расширения в зависимости от типа медиа
        if media_info:
            media_type = media_info.get("type", "unknown")
            
            if media_type == "photo":
                return f"{base_filename}.jpg"
            elif media_type == "video":
                return f"{base_filename}.mp4"
            elif media_type == "voice":
                return f"{base_filename}.ogg"
            elif media_type == "audio":
                return f"{base_filename}.mp3"
            elif media_type == "animation":
                return f"{base_filename}.gif"
        
        # По умолчанию без расширения
        return base_filename
    
    def open_media(self, filepath: str) -> bool:
        """
        Открытие медиа-файла во внешней программе.
        
        Args:
            filepath: Путь к файлу
            
        Returns:
            True в случае успеха, иначе False
        """
        if not filepath or not os.path.exists(filepath):
            logger.warning(f"Попытка открыть несуществующий файл: {filepath}")
            return False
        
        try:
            # Открытие файла с помощью системной программы по умолчанию
            system = platform.system()
            
            if system == 'Darwin':  # macOS
                subprocess.Popen(['open', filepath])
            elif system == 'Windows':
                os.startfile(filepath)
            else:  # Linux
                subprocess.Popen(['xdg-open', filepath])
            
            logger.info(f"Файл '{filepath}' открыт во внешней программе")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при открытии файла '{filepath}': {e}")
            return False
    
    def get_download_dir(self) -> str:
        """
        Получение директории для загрузок.
        
        Returns:
            Путь к директории загрузок
        """
        return self.download_dir
    
    def set_download_dir(self, download_dir: str) -> bool:
        """
        Установка директории для загрузок.
        
        Args:
            download_dir: Путь к директории
            
        Returns:
            True в случае успеха, иначе False
        """
        try:
            # Создание директории, если её нет
            os.makedirs(download_dir, exist_ok=True)
            
            # Установка новой директории
            self.download_dir = download_dir
            
            logger.info(f"Директория загрузок изменена на '{download_dir}'")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при изменении директории загрузок: {e}")
            return False