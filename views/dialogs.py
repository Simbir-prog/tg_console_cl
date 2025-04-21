#!/usr/bin/env python3
"""
Отображение списка диалогов.
Модуль для визуализации списка диалогов в консольном интерфейсе.
"""

import curses
import logging
from typing import List, Optional
from telethon.tl.types import Dialog

logger = logging.getLogger(__name__)


def get_dialog_display_name(dialog: Dialog) -> str:
    """
    Получение отображаемого имени диалога.
    
    Args:
        dialog: Объект диалога
        
    Returns:
        Отображаемое имя диалога
    """
    entity = dialog.entity
    
    try:
        if hasattr(entity, 'title') and entity.title:
            return entity.title
        elif hasattr(entity, 'first_name'):
            if hasattr(entity, 'last_name') and entity.last_name:
                return f"{entity.first_name} {entity.last_name}"
            return entity.first_name
        else:
            return "Неизвестный диалог"
    except AttributeError:
        return "Неизвестный диалог"


def render_dialogs(
    stdscr: 'curses._CursesWindow', 
    dialogs: List[Dialog], 
    selected_index: int,
    show_all_dialogs: bool,
    is_loading: bool = False
) -> None:
    """
    Отрисовка списка диалогов.
    
    Args:
        stdscr: Окно curses
        dialogs: Список диалогов
        selected_index: Индекс выбранного диалога
        show_all_dialogs: Флаг отображения всех диалогов (не только с непрочитанными)
        is_loading: Флаг загрузки данных
    """
    height, width = stdscr.getmaxyx()
    
    # Очистка экрана
    stdscr.clear()
    
    # Отрисовка заголовка
    header = "Telegram CLI - Список диалогов"
    mode = "Все диалоги" if show_all_dialogs else "Только непрочитанные"
    header_line = f"{header} ({mode})"
    
    stdscr.attron(curses.A_BOLD)
    if curses.has_colors():
        stdscr.attron(curses.color_pair(1))  # Цвет заголовка
    
    # Центрирование заголовка
    header_x = max(0, (width - len(header_line)) // 2)
    stdscr.addstr(0, header_x, header_line)
    
    if curses.has_colors():
        stdscr.attroff(curses.color_pair(1))
    stdscr.attroff(curses.A_BOLD)
    
    # Отрисовка разделителя
    stdscr.addstr(1, 0, "─" * width)
    
    # Если загрузка данных в процессе и список пуст
    if is_loading and not dialogs:
        message = "Загрузка данных..."
        message_x = max(0, (width - len(message)) // 2)
        message_y = height // 2
        stdscr.addstr(message_y, message_x, message)
        return
    
    # Если список диалогов пуст
    if not dialogs:
        message = "Нет доступных диалогов" if show_all_dialogs else "Нет непрочитанных диалогов"
        # Центрирование сообщения
        message_x = max(0, (width - len(message)) // 2)
        message_y = height // 2
        stdscr.addstr(message_y, message_x, message)
        return
    
    # Определение видимой области
    visible_lines = height - 3  # За вычетом заголовка, разделителя и строки статуса
    
    # Вычисление начального индекса для прокрутки
    start_index = max(0, min(selected_index - visible_lines // 2, len(dialogs) - visible_lines))
    
    # Отрисовка диалогов
    for i in range(min(visible_lines, len(dialogs))):
        index = start_index + i
        
        # Выход за пределы списка
        if index >= len(dialogs):
            break
            
        dialog = dialogs[index]
        
        # Получение имени диалога
        name = get_dialog_display_name(dialog)
        
        # Добавление индикатора непрочитанных сообщений
        if dialog.unread_count > 0:
            name = f"{name} [{dialog.unread_count}]"
        
        # Ограничение длины имени
        if len(name) > width - 4:
            name = name[:width - 7] + "..."
        
        # Выделение выбранного диалога
        if index == selected_index:
            stdscr.attron(curses.A_REVERSE)
            
        # Выделение диалогов с непрочитанными сообщениями
        elif dialog.unread_count > 0 and curses.has_colors():
            stdscr.attron(curses.color_pair(2))  # Цвет непрочитанных
        
        # Отрисовка строки диалога
        stdscr.addstr(i + 2, 2, name)
        
        # Сброс атрибутов
        if index == selected_index:
            stdscr.attroff(curses.A_REVERSE)
        elif dialog.unread_count > 0 and curses.has_colors():
            stdscr.attroff(curses.color_pair(2))
    
    # Отрисовка индикатора прокрутки
    if len(dialogs) > visible_lines:
        # Вычисление позиции и размера ползунка
        scrollbar_height = max(1, int(visible_lines * visible_lines / len(dialogs)))
        scrollbar_pos = min(
            visible_lines - scrollbar_height,
            int(start_index * visible_lines / len(dialogs))
        )
        
        for i in range(visible_lines):
            char = "█" if scrollbar_pos <= i < scrollbar_pos + scrollbar_height else "░"
            stdscr.addstr(i + 2, width - 2, char)