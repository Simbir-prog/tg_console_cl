#!/usr/bin/env python3
"""
Обработка клавиатурного ввода.
Модуль для обработки нажатий клавиш и связанных с ними действий.
"""

import curses
import logging
import asyncio
from typing import Dict, Callable, Any, Awaitable, Optional

from state import AppState

logger = logging.getLogger(__name__)


class KeyHandler:
    """Класс для обработки клавиатурного ввода"""
    
    def __init__(self, cli):
        """
        Инициализация обработчика клавиш.
        
        Args:
            cli: Экземпляр консольного интерфейса
        """
        self.cli = cli
        
        # Определение специальных клавиш
        self.KEYS = {
            # Стрелки
            "UP": curses.KEY_UP,
            "DOWN": curses.KEY_DOWN,
            "LEFT": curses.KEY_LEFT,
            "RIGHT": curses.KEY_RIGHT,
            
            # Управляющие клавиши
            "ENTER": 10,  # ASCII код Enter (LF)
            "ESC": 27,    # ASCII код Escape
            "TAB": 9,     # ASCII код Tab
            
            # Буквенные клавиши
            "R": ord('r'),
            "Q": ord('q'),
            "S": ord('s'),
            
            # Комбинации клавиш (Ctrl + клавиша)
            "CTRL_C": 3,  # ASCII код Ctrl+C (ETX)
            "CTRL_R": 18, # ASCII код Ctrl+R (DC2)
            "CTRL_L": 12  # ASCII код Ctrl+L (FF)
        }
        
        # Обработчики глобальных клавиш (работают во всех состояниях)
        self.global_handlers = {
            self.KEYS["CTRL_C"]: self._handle_exit,
            self.KEYS["CTRL_R"]: self._handle_reconnect,
            self.KEYS["CTRL_L"]: self._handle_refresh
        }
        
        # Обработчики клавиш для разных состояний
        self.state_handlers = {
            AppState.DIALOGS: {
                self.KEYS["UP"]: self._handle_dialog_up,
                self.KEYS["DOWN"]: self._handle_dialog_down,
                self.KEYS["RIGHT"]: self._handle_open_dialog,
                self.KEYS["TAB"]: self._handle_toggle_dialog_mode,
                self.KEYS["Q"]: self._handle_exit
            },
            AppState.CHAT: {
                self.KEYS["UP"]: self._handle_message_up,
                self.KEYS["DOWN"]: self._handle_message_down,
                self.KEYS["LEFT"]: self._handle_back_to_dialogs,
                self.KEYS["R"]: self._handle_reply_mode,
                self.KEYS["S"]: self._handle_save_media,
                self.KEYS["Q"]: self._handle_back_to_dialogs
            },
            AppState.REPLY: {
                self.KEYS["ESC"]: self._handle_cancel_reply,
                self.KEYS["ENTER"]: self._handle_send_reply
            }
        }
    
    async def handle_key(self, key: int) -> bool:
        """
        Обработка нажатия клавиши.
        
        Args:
            key: Код нажатой клавиши
            
        Returns:
            True если клавиша была обработана, иначе False
        """
        # Проверка глобальных обработчиков
        if key in self.global_handlers:
            await self.global_handlers[key]()
            return True
        
        # Получение текущего состояния приложения
        current_state = self.cli.state_manager.get_state()
        
        # Проверка обработчиков для текущего состояния
        if current_state in self.state_handlers and key in self.state_handlers[current_state]:
            await self.state_handlers[current_state][key]()
            return True
        
        # Клавиша не была обработана
        return False
    
    # Глобальные обработчики клавиш
    
    async def _handle_exit(self):
        """Обработка выхода из приложения"""
        self.cli.running = False
    
    async def _handle_reconnect(self):
        """Обработка переподключения к серверу"""
        try:
            # Отключение от Telegram
            await self.cli.client.disconnect()
            
            # Повторное подключение
            await self.cli.client.connect()
            
            # Обновление данных
            await self.cli.refresh_dialogs()
            
            logger.info("Успешное переподключение к серверу")
            
        except Exception as e:
            logger.error(f"Ошибка при переподключении: {e}")
    
    async def _handle_refresh(self):
        """Обработка обновления экрана"""
        # Очистка экрана и перерисовка интерфейса
        self.cli.stdscr.clear()
        self.cli.stdscr.refresh()
        await self.cli.refresh_screen()
    
    # Обработчики для режима списка диалогов
    
    async def _handle_dialog_up(self):
        """Обработка перемещения вверх по списку диалогов"""
        if self.cli.dialog_list:
            # Перемещение выделения вверх
            self.cli.selected_dialog_index = max(0, self.cli.selected_dialog_index - 1)
    
    async def _handle_dialog_down(self):
        """Обработка перемещения вниз по списку диалогов"""
        if self.cli.dialog_list:
            # Перемещение выделения вниз
            self.cli.selected_dialog_index = min(
                len(self.cli.dialog_list) - 1, 
                self.cli.selected_dialog_index + 1
            )
    
    async def _handle_open_dialog(self):
        """Обработка открытия выбранного диалога"""
        await self.cli.open_selected_dialog()
    
    async def _handle_toggle_dialog_mode(self):
        """Обработка переключения режима отображения диалогов"""
        await self.cli.toggle_dialogs_mode()
    
    # Обработчики для режима чата
    
    async def _handle_message_up(self):
        """Обработка перемещения вверх по списку сообщений"""
        if self.cli.selected_messages:
            # Перемещение выделения вверх
            self.cli.selected_message_index = max(0, self.cli.selected_message_index - 1)
    
    async def _handle_message_down(self):
        """Обработка перемещения вниз по списку сообщений"""
        if self.cli.selected_messages:
            # Перемещение выделения вниз
            self.cli.selected_message_index = min(
                len(self.cli.selected_messages) - 1, 
                self.cli.selected_message_index + 1
            )
    
    async def _handle_back_to_dialogs(self):
        """Обработка возврата к списку диалогов"""
        await self.cli.back_to_dialogs()
    
    async def _handle_reply_mode(self):
        """Обработка входа в режим ответа"""
        # Если мы уже в режиме ответа, ничего не делаем
        if self.cli.reply_mode:
            return
            
        # Переключение в режим ответа
        self.cli.state_manager.set_state(AppState.REPLY)
        await self.cli.enter_reply_mode()
        
        # Возврат в режим чата после отправки или отмены
        self.cli.state_manager.set_state(AppState.CHAT)
    
    async def _handle_save_media(self):
        """Обработка сохранения медиа"""
        await self.cli.save_media()
    
    # Обработчики для режима ответа
    
    async def _handle_cancel_reply(self):
        """Обработка отмены ответа"""
        # Отключение режима ответа
        self.cli.reply_mode = False
        
        # Возврат в режим чата
        self.cli.state_manager.set_state(AppState.CHAT)
    
    async def _handle_send_reply(self):
        """Обработка отправки ответа"""
        # Эта функция не должна вызываться напрямую,
        # так как отправка происходит в методе enter_reply_mode
        pass