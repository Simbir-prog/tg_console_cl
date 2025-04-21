#!/usr/bin/env python3
"""
Асинхронный загрузчик данных.
Модуль для управления асинхронными задачами загрузки данных.
"""

import asyncio
import logging
from typing import Dict, List, Any, Callable, Awaitable, Optional, Tuple
import uuid

logger = logging.getLogger(__name__)


class AsyncLoader:
    """Класс для асинхронной загрузки данных"""
    
    def __init__(self):
        """Инициализация загрузчика"""
        # Словарь активных задач: task_id -> (task, on_complete, on_error)
        self.active_tasks: Dict[str, Tuple[asyncio.Task, Optional[Callable], Optional[Callable]]] = {}
    
    def create_task(
        self,
        coro: Awaitable[Any],
        on_complete: Optional[Callable[[Any], None]] = None,
        on_error: Optional[Callable[[Exception], None]] = None
    ) -> str:
        """
        Создание и запуск асинхронной задачи.
        
        Args:
            coro: Корутина для выполнения
            on_complete: Коллбэк, вызываемый при успешном завершении задачи
            on_error: Коллбэк, вызываемый при ошибке в задаче
            
        Returns:
            ID созданной задачи
        """
        # Генерация уникального ID задачи
        task_id = str(uuid.uuid4())
        
        # Создание задачи
        task = asyncio.create_task(self._task_wrapper(task_id, coro, on_complete, on_error))
        
        # Сохранение задачи и коллбэков
        self.active_tasks[task_id] = (task, on_complete, on_error)
        
        logger.debug(f"Создана асинхронная задача {task_id}")
        
        return task_id
    
    async def _task_wrapper(
        self,
        task_id: str,
        coro: Awaitable[Any],
        on_complete: Optional[Callable[[Any], None]],
        on_error: Optional[Callable[[Exception], None]]
    ):
        """
        Обертка для выполнения задачи с обработкой результата и ошибок.
        
        Args:
            task_id: ID задачи
            coro: Корутина для выполнения
            on_complete: Коллбэк для успешного завершения
            on_error: Коллбэк для обработки ошибок
        """
        try:
            # Выполнение корутины
            result = await coro
            
            # Вызов коллбэка успешного завершения
            if on_complete:
                try:
                    on_complete(result)
                except Exception as e:
                    logger.error(f"Ошибка в обработчике успешного завершения задачи {task_id}: {e}")
            
            logger.debug(f"Задача {task_id} успешно завершена")
            
        except asyncio.CancelledError:
            # Задача была отменена
            logger.debug(f"Задача {task_id} отменена")
            raise
            
        except Exception as e:
            # Произошла ошибка при выполнении задачи
            logger.error(f"Ошибка в задаче {task_id}: {e}")
            
            # Вызов коллбэка обработки ошибок
            if on_error:
                try:
                    on_error(e)
                except Exception as callback_error:
                    logger.error(f"Ошибка в обработчике ошибок задачи {task_id}: {callback_error}")
        
        finally:
            # Удаление задачи из списка активных
            if task_id in self.active_tasks:
                del self.active_tasks[task_id]
    
    def cancel_task(self, task_id: str) -> bool:
        """
        Отмена выполнения задачи.
        
        Args:
            task_id: ID задачи
            
        Returns:
            True если задача была найдена и отменена, иначе False
        """
        if task_id in self.active_tasks:
            task, _, _ = self.active_tasks[task_id]
            task.cancel()
            logger.debug(f"Задача {task_id} отменена")
            return True
        
        logger.warning(f"Попытка отменить несуществующую задачу {task_id}")
        return False
    
    def cancel_all_tasks(self):
        """Отмена всех активных задач"""
        for task_id, (task, _, _) in list(self.active_tasks.items()):
            task.cancel()
            logger.debug(f"Задача {task_id} отменена при общей отмене")
        
        self.active_tasks.clear()
        logger.info("Все активные задачи отменены")
    
    async def process_pending_tasks(self):
        """Обработка ожидающих задач"""
        # Позволяем задачам выполниться
        await asyncio.sleep(0)
    
    def get_active_tasks_count(self) -> int:
        """
        Получение количества активных задач.
        
        Returns:
            Количество активных задач
        """
        return len(self.active_tasks)
    
    def is_task_active(self, task_id: str) -> bool:
        """
        Проверка активности задачи.
        
        Args:
            task_id: ID задачи
            
        Returns:
            True если задача активна, иначе False
        """
        return task_id in self.active_tasks