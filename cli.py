#!/usr/bin/env python3
"""
Консольный интерфейс пользователя.
Отвечает за отображение информации в консоли и взаимодействие с пользователем.
"""

import asyncio
import curses
import logging
from typing import List, Optional, Dict, Any, Tuple

from api.client import TelegramClient
from state import StateManager, AppState
from input.keys import KeyHandler
import views.dialogs as dialog_view
import views.chat as chat_view
from services.cache import CacheManager
from services.media import MediaHandler
from utils.async_loader import AsyncLoader

logger = logging.getLogger(__name__)


class TelegramCLI:
    """
    Класс консольного интерфейса Telegram.
    Использует библиотеку curses для создания интерактивного интерфейса.
    """
    
    def __init__(self, client: TelegramClient, state_manager: StateManager):
        """
        Инициализация консольного интерфейса.
        
        Args:
            client: Клиент Telegram
            state_manager: Менеджер состояний приложения
        """
        self.client = client
        self.state_manager = state_manager
        self.stdscr = None
        self.key_handler = None
        self.running = False
        self.dialog_list = []
        self.selected_messages = []
        self.selected_dialog_index = 0
        self.selected_message_index = 0
        self.is_all_dialogs_mode = False  # Режим отображения (False - только с непрочитанными)
        self.reply_mode = False
        
        # Инициализация кеш-менеджера
        self.cache_manager = CacheManager()
        
        # Инициализация обработчика медиа
        self.media_handler = MediaHandler(client)
        
        # Инициализация загрузчика
        self.async_loader = AsyncLoader()
        
        # Флаг загрузки (для отображения индикатора)
        self.is_loading = False
    
    async def run(self):
        """Запуск консольного интерфейса"""
        # Запуск curses
        self.running = True
        curses.wrapper(self._main_loop)
    
    def _main_loop(self, stdscr):
        """
        Основной цикл обработки событий.
        
        Args:
            stdscr: Основной экран curses
        """
        # Инициализация экрана
        self.stdscr = stdscr
        self._setup_screen()
        
        # Инициализация обработчика клавиш
        self.key_handler = KeyHandler(self)
        
        # Начальное состояние - список диалогов
        self.state_manager.set_state(AppState.DIALOGS)
        
        # Запуск асинхронного цикла внутри curses
        asyncio.run(self._async_main_loop())
    
    def _setup_screen(self):
        """Настройка параметров экрана curses"""
        # Отключение отображения курсора
        curses.curs_set(0)
        
        # Включение поддержки цветов, если возможно
        if curses.has_colors():
            curses.start_color()
            curses.init_pair(1, curses.COLOR_CYAN, curses.COLOR_BLACK)  # Заголовки
            curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)  # Непрочитанные
            curses.init_pair(3, curses.COLOR_YELLOW, curses.COLOR_BLACK)  # Выделение
            curses.init_pair(4, curses.COLOR_RED, curses.COLOR_BLACK)    # Ошибки
        
        # Отключение задержки для специальных клавиш (например, Escape)
        self.stdscr.nodelay(False)
        self.stdscr.timeout(-1)
        
        # Включение поддержки функциональных и специальных клавиш
        self.stdscr.keypad(True)
        
        # Отключение эхо-вывода нажатых клавиш
        curses.noecho()
        
        # Получение размеров экрана
        self.height, self.width = self.stdscr.getmaxyx()
    
    async def _async_main_loop(self):
        """Асинхронный цикл обработки событий"""
        try:
            # Начальная загрузка данных
            await self.refresh_dialogs()
            await self.refresh_screen()
            
            # Основной цикл обработки ввода
            while self.running:
                # Обработка нажатий клавиш
                key = self.stdscr.getch()
                await self.key_handler.handle_key(key)
                
                # Обновление экрана после обработки клавиши
                await self.refresh_screen()
                
                # Проверка и выполнение асинхронных задач в фоне
                await self.async_loader.process_pending_tasks()
                
                # Небольшая задержка для снижения нагрузки на CPU
                await asyncio.sleep(0.01)
                
        except Exception as e:
            logger.error(f"Ошибка в асинхронном цикле: {e}")
            self.running = False
    
    async def refresh_dialogs(self):
        """Обновление списка диалогов"""
        try:
            # Установка флага загрузки
            self.is_loading = True
            
            # Создание асинхронной задачи для загрузки диалогов
            self.async_loader.create_task(
                self.client.get_dialogs(
                    limit=100, 
                    only_unread=not self.is_all_dialogs_mode
                ),
                on_complete=self._on_dialogs_loaded,
                on_error=self._on_load_error
            )
            
            # Обновление интерфейса с индикатором загрузки
            await self.refresh_screen()
            
        except Exception as e:
            logger.error(f"Ошибка при обновлении диалогов: {e}")
            self.is_loading = False
    
    def _on_dialogs_loaded(self, dialogs):
        """Обработчик успешной загрузки диалогов"""
        self.dialog_list = dialogs
        
        # Сброс индекса при обновлении списка
        if self.selected_dialog_index >= len(self.dialog_list):
            self.selected_dialog_index = 0
            
        self.is_loading = False
    
    def _on_load_error(self, error):
        """Обработчик ошибки загрузки"""
        logger.error(f"Ошибка загрузки: {error}")
        self.is_loading = False
        self._show_error_message(f"Ошибка загрузки: {error}")
    
    def _show_error_message(self, message):
        """Отображение сообщения об ошибке"""
        if not self.stdscr:
            return
            
        height, width = self.stdscr.getmaxyx()
        
        # Очистка нижней строки
        self.stdscr.move(height-3, 0)
        self.stdscr.clrtoeol()
        
        # Отображение сообщения об ошибке
        if curses.has_colors():
            self.stdscr.attron(curses.color_pair(4))  # Красный цвет для ошибок
        
        error_text = f"ОШИБКА: {message}"
        if len(error_text) > width - 4:
            error_text = error_text[:width - 7] + "..."
            
        self.stdscr.addstr(height-3, 2, error_text)
        
        if curses.has_colors():
            self.stdscr.attroff(curses.color_pair(4))
        
        self.stdscr.refresh()
    
    async def refresh_messages(self):
        """Обновление списка сообщений для выбранного диалога"""
        try:
            if not self.dialog_list or self.selected_dialog_index >= len(self.dialog_list):
                self.selected_messages = []
                return
                
            # Получение выбранного диалога
            dialog = self.dialog_list[self.selected_dialog_index]
            
            # Установка флага загрузки
            self.is_loading = True
            
            # Проверка кеша перед загрузкой
            cached_messages = self.cache_manager.get_messages(dialog.id)
            if cached_messages:
                self.selected_messages = cached_messages
                self.is_loading = False
                
                # Сброс индекса при обновлении списка
                if self.selected_message_index >= len(self.selected_messages):
                    self.selected_message_index = 0
                    
                return
            
            # Создание асинхронной задачи для загрузки сообщений
            self.async_loader.create_task(
                self.client.get_messages(dialog.entity, limit=30),
                on_complete=lambda messages: self._on_messages_loaded(dialog.id, messages),
                on_error=self._on_load_error
            )
            
            # Обновление интерфейса с индикатором загрузки
            await self.refresh_screen()
                
        except Exception as e:
            logger.error(f"Ошибка при обновлении сообщений: {e}")
            self.is_loading = False
            self.selected_messages = []
    
    def _on_messages_loaded(self, dialog_id, messages):
        """Обработчик успешной загрузки сообщений"""
        self.selected_messages = messages
        
        # Сохранение в кеш
        self.cache_manager.store_messages(dialog_id, messages)
        
        # Сброс индекса при обновлении списка
        if self.selected_message_index >= len(self.selected_messages):
            self.selected_message_index = 0
            
        self.is_loading = False
    
    async def refresh_screen(self):
        """Обновление содержимого экрана"""
        # Очистка экрана
        self.stdscr.clear()
        
        # Определение текущего состояния приложения
        current_state = self.state_manager.get_state()
        
        # Отрисовка индикатора загрузки, если данные загружаются
        if self.is_loading:
            self._render_loading_indicator()
        
        # Отрисовка в зависимости от состояния
        if current_state == AppState.DIALOGS:
            # Отображение списка диалогов
            dialog_view.render_dialogs(
                self.stdscr, 
                self.dialog_list, 
                self.selected_dialog_index,
                self.is_all_dialogs_mode,
                self.is_loading
            )
        
        elif current_state == AppState.CHAT:
            # Отображение чата
            chat_view.render_chat(
                self.stdscr,
                self.dialog_list[self.selected_dialog_index] if self.dialog_list else None,
                self.selected_messages,
                self.selected_message_index,
                self.reply_mode,
                self.is_loading,
                self.media_handler
            )
        
        # Отображение строки статуса
        self._render_status_bar()
        
        # Обновление экрана
        self.stdscr.refresh()
    
    def _render_loading_indicator(self):
        """Отрисовка индикатора загрузки"""
        if not self.stdscr:
            return
            
        height, width = self.stdscr.getmaxyx()
        
        # Символы для анимации загрузки
        animation_chars = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
        
        # Получение текущего символа анимации
        import time
        char_index = int(time.time() * 10) % len(animation_chars)
        loading_char = animation_chars[char_index]
        
        # Текст загрузки
        loading_text = f"{loading_char} Загрузка данных..."
        
        # Отображение в правом верхнем углу
        if curses.has_colors():
            self.stdscr.attron(curses.color_pair(3))  # Желтый цвет для индикатора
            
        self.stdscr.addstr(0, width - len(loading_text) - 2, loading_text)
        
        if curses.has_colors():
            self.stdscr.attroff(curses.color_pair(3))
    
    def _render_status_bar(self):
        """Отрисовка строки статуса"""
        status_line = self.height - 1
        self.stdscr.attron(curses.A_REVERSE)
        
        # Определение текущего состояния для строки статуса
        current_state = self.state_manager.get_state()
        
        if current_state == AppState.DIALOGS:
            mode = "Только непрочитанные" if not self.is_all_dialogs_mode else "Все диалоги"
            status = f"TG CLI | {mode} | ↑/↓:навигация | →:открыть чат | Tab:сменить режим | Ctrl+R:переподключиться | Ctrl+C:выход"
        
        elif current_state == AppState.CHAT:
            status = "TG CLI | ↑/↓:навигация | ←:назад к списку | r:ответить | s:сохранить медиа | Ctrl+R:переподключиться | Ctrl+C:выход"
            if self.reply_mode:
                status = "TG CLI | РЕЖИМ ОТВЕТА | Введите текст и нажмите Enter | Esc:отмена"
        
        else:
            status = "TG CLI | Ctrl+C:выход"
        
        # Обрезка статуса под ширину экрана
        status = status[:self.width]
        
        # Добавление пробелов до конца строки
        status = status.ljust(self.width)
        
        # Вывод статуса
        self.stdscr.addstr(status_line, 0, status)
        self.stdscr.attroff(curses.A_REVERSE)
    
    async def toggle_dialogs_mode(self):
        """Переключение режима отображения диалогов"""
        self.is_all_dialogs_mode = not self.is_all_dialogs_mode
        await self.refresh_dialogs()
    
    async def open_selected_dialog(self):
        """Открытие выбранного диалога"""
        if not self.dialog_list or self.selected_dialog_index >= len(self.dialog_list):
            return
            
        # Получение сообщений диалога
        await self.refresh_messages()
        
        # Переключение в режим чата
        self.state_manager.set_state(AppState.CHAT)
    
    async def back_to_dialogs(self):
        """Возврат к списку диалогов"""
        # Сброс выбранного сообщения
        self.selected_message_index = 0
        self.selected_messages = []
        
        # Отключение режима ответа, если он был активен
        self.reply_mode = False
        
        # Обновление диалогов перед отображением
        await self.refresh_dialogs()
        
        # Переключение в режим диалогов
        self.state_manager.set_state(AppState.DIALOGS)
    
    async def enter_reply_mode(self):
        """Вход в режим ответа на сообщение"""
        if not self.selected_messages or self.selected_message_index >= len(self.selected_messages):
            return
            
        self.reply_mode = True
        
        # Включение отображения курсора
        curses.curs_set(1)
        
        # Отрисовка строки ввода
        message_input_line = self.height - 2
        self.stdscr.move(message_input_line, 0)
        self.stdscr.clrtoeol()
        self.stdscr.addstr(message_input_line, 0, "reply> ")
        self.stdscr.refresh()
        
        # Включение эхо-вывода для строки ввода
        curses.echo()
        
        # Получение текста от пользователя
        reply_text = self.stdscr.getstr(message_input_line, 7, self.width - 8).decode('utf-8')
        
        # Восстановление параметров экрана
        curses.noecho()
        curses.curs_set(0)
        
        # Если был введен текст, отправляем ответ
        if reply_text.strip():
            await self.send_reply(reply_text)
        
        # Выход из режима ответа
        self.reply_mode = False
    
    async def send_reply(self, text: str):
        """
        Отправка ответа на выбранное сообщение.
        
        Args:
            text: Текст ответа
        """
        try:
            if not self.dialog_list or self.selected_dialog_index >= len(self.dialog_list):
                return
                
            if not self.selected_messages or self.selected_message_index >= len(self.selected_messages):
                return
                
            # Получение выбранного диалога и сообщения
            dialog = self.dialog_list[self.selected_dialog_index]
            message = self.selected_messages[self.selected_message_index]
            
            # Установка флага загрузки
            self.is_loading = True
            
            # Асинхронная отправка ответа
            self.async_loader.create_task(
                self.client.send_message(dialog.entity, text, reply_to=message),
                on_complete=lambda _: self._on_reply_sent(dialog, message),
                on_error=self._on_load_error
            )
            
        except Exception as e:
            logger.error(f"Ошибка при отправке ответа: {e}")
            self.is_loading = False
            self._show_error_message(f"Ошибка отправки: {e}")
    
    def _on_reply_sent(self, dialog, message):
        """Обработчик успешной отправки ответа"""
        # Асинхронная отметка сообщения как прочитанного
        self.async_loader.create_task(
            self.client.mark_as_read(dialog.entity, message),
            on_complete=lambda _: self._on_message_marked_read(),
            on_error=self._on_load_error
        )
    
    def _on_message_marked_read(self):
        """Обработчик успешной отметки сообщения как прочитанного"""
        # Обновление списка сообщений
        self.async_loader.create_task(
            self.refresh_messages(),
            on_error=self._on_load_error
        )
        
        # Сброс флага загрузки
        self.is_loading = False
    
    async def save_media(self):
        """Сохранение медиа из выбранного сообщения"""
        if not self.selected_messages or self.selected_message_index >= len(self.selected_messages):
            return
            
        message = self.selected_messages[self.selected_message_index]
        
        # Проверка наличия медиа в сообщении
        if not message.media:
            self._show_error_message("В этом сообщении нет медиа-контента")
            return
        
        # Установка флага загрузки
        self.is_loading = True
        
        # Асинхронная загрузка медиа
        self.async_loader.create_task(
            self.media_handler.download_media(message),
            on_complete=self._on_media_downloaded,
            on_error=self._on_load_error
        )
    
    def _on_media_downloaded(self, filepath):
        """Обработчик успешной загрузки медиа"""
        self.is_loading = False
        
        if not filepath:
            self._show_error_message("Не удалось загрузить медиа")
            return
        
        height, width = self.stdscr.getmaxyx()
        
        # Очистка нижней строки
        self.stdscr.move(height-3, 0)
        self.stdscr.clrtoeol()
        
        # Отображение сообщения об успешной загрузке
        if curses.has_colors():
            self.stdscr.attron(curses.color_pair(2))  # Зеленый цвет для успеха
        
        success_text = f"Медиа сохранено: {filepath}"
        if len(success_text) > width - 4:
            success_text = success_text[:width - 7] + "..."
            
        self.stdscr.addstr(height-3, 2, success_text)
        
        if curses.has_colors():
            self.stdscr.attroff(curses.color_pair(2))
        
        self.stdscr.refresh()
        
        # Попытка открыть файл во внешней программе
        self.media_handler.open_media(filepath)
    
    async def shutdown(self):
        """Завершение работы консольного интерфейса"""
        self.running = False
        
        # Остановка всех асинхронных задач
        self.async_loader.cancel_all_tasks()
        
        # Сохранение кеша
        self.cache_manager.save_cache()
        
        # Восстановление нормального состояния терминала
        if self.stdscr:
            self.stdscr.clear()
            self.stdscr.refresh()
            curses.endwin()