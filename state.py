#!/usr/bin/env python3
"""
Управление состоянием приложения.
Модуль для отслеживания и управления текущим состоянием приложения.
"""

import enum
import logging
from typing import Optional, Callable, Dict, Any

logger = logging.getLogger(__name__)


class AppState(enum.Enum):
    """Перечисление возможных состояний приложения"""
    INIT = 0          # Инициализация
    DIALOGS = 1       # Просмотр списка диалогов
    CHAT = 2          # Просмотр конкретного чата
    REPLY = 3         # Режим ответа на сообщение
    SETTINGS = 4      # Настройки приложения
    ERROR = 5         # Состояние ошибки


class StateManager:
    """Класс для управления состоянием приложения"""
    
    def __init__(self):
        """Инициализация менеджера состояний"""
        self._current_state = AppState.INIT
        self._prev_state: Optional[AppState] = None
        self._state_data: Dict[str, Any] = {}
        self._state_change_callbacks: Dict[AppState, list] = {}
        
        logger.info("Менеджер состояний инициализирован")
    
    def set_state(self, state: AppState, **state_data):
        """
        Установка нового состояния приложения.
        
        Args:
            state: Новое состояние
            state_data: Данные, связанные с новым состоянием
        """
        if state != self._current_state:
            logger.info(f"Изменение состояния: {self._current_state} -> {state}")
            
            # Сохранение предыдущего состояния
            self._prev_state = self._current_state
            
            # Установка нового состояния
            self._current_state = state
            
            # Обновление данных состояния
            self._state_data.update(state_data)
            
            # Вызов коллбэков для изменения состояния
            self._notify_state_change()
    
    def get_state(self) -> AppState:
        """
        Получение текущего состояния приложения.
        
        Returns:
            Текущее состояние
        """
        return self._current_state
    
    def get_previous_state(self) -> Optional[AppState]:
        """
        Получение предыдущего состояния приложения.
        
        Returns:
            Предыдущее состояние или None, если его не было
        """
        return self._prev_state
    
    def return_to_previous_state(self):
        """Возврат к предыдущему состоянию приложения"""
        if self._prev_state:
            self.set_state(self._prev_state)
    
    def get_state_data(self, key: str, default: Any = None) -> Any:
        """
        Получение данных, связанных с текущим состоянием.
        
        Args:
            key: Ключ данных
            default: Значение по умолчанию
            
        Returns:
            Данные состояния или default, если ключ не найден
        """
        return self._state_data.get(key, default)
    
    def set_state_data(self, key: str, value: Any):
        """
        Установка данных, связанных с текущим состоянием.
        
        Args:
            key: Ключ данных
            value: Значение данных
        """
        self._state_data[key] = value
    
    def register_state_change_callback(self, state: AppState, callback: Callable):
        """
        Регистрация функции обратного вызова для изменения состояния.
        
        Args:
            state: Состояние, для которого регистрируется коллбэк
            callback: Функция обратного вызова
        """
        if state not in self._state_change_callbacks:
            self._state_change_callbacks[state] = []
            
        self._state_change_callbacks[state].append(callback)
    
    def _notify_state_change(self):
        """Уведомление о изменении состояния"""
        state = self._current_state
        
        # Вызов коллбэков для текущего состояния
        if state in self._state_change_callbacks:
            for callback in self._state_change_callbacks[state]:
                try:
                    callback(self._state_data)
                except Exception as e:
                    logger.error(f"Ошибка в обработчике изменения состояния: {e}")