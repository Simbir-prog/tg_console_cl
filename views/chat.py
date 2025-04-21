#!/usr/bin/env python3
"""
Отображение чата.
Модуль для визуализации сообщений чата в консольном интерфейсе.
"""

import curses
import logging
import datetime
from typing import List, Optional, Union

from telethon.tl.types import Message, Dialog, Chat, Channel, User
import views.dialogs as dialog_view

logger = logging.getLogger(__name__)


def get_sender_name(message: Message) -> str:
    """
    Получение имени отправителя сообщения.
    
    Args:
        message: Объект сообщения
        
    Returns:
        Имя отправителя
    """
    if message.sender:
        if hasattr(message.sender, 'first_name'):
            if hasattr(message.sender, 'last_name') and message.sender.last_name:
                return f"{message.sender.first_name} {message.sender.last_name}"
            return message.sender.first_name
        elif hasattr(message.sender, 'title'):
            return message.sender.title
    
    return "Неизвестный отправитель"


def format_message_text(message: Message, width: int) -> List[str]:
    """
    Форматирование текста сообщения для отображения.
    
    Args:
        message: Объект сообщения
        width: Доступная ширина для текста
        
    Returns:
        Список строк отформатированного текста
    """
    # Получение текста сообщения
    text = message.message if message.message else ""
    
    # Если текст пустой, но есть медиа
    if not text and message.media:
        media_type = type(message.media).__name__
        text = f"[{media_type}]"
    
    # Если текст все еще пустой
    if not text:
        text = "[Пустое сообщение]"
    
    # Разбиение текста на строки с учетом ширины экрана
    lines = []
    for line in text.split("\n"):
        # Если строка короче доступной ширины, добавляем как есть
        if len(line) <= width:
            lines.append(line)
        else:
            # Разбиение длинной строки
            current_line = ""
            for word in line.split(" "):
                # Если слово помещается в текущую строку
                if len(current_line) + len(word) + 1 <= width:
                    if current_line:
                        current_line += " " + word
                    else:
                        current_line = word
                else:
                    # Добавление текущей строки и начало новой
                    lines.append(current_line)
                    current_line = word
            
            # Добавление последней строки
            if current_line:
                lines.append(current_line)
    
    return lines


def render_chat(
    stdscr: 'curses._CursesWindow',
    dialog: Optional[Dialog],
    messages: List[Message],
    selected_index: int,
    reply_mode: bool,
    is_loading: bool = False,
    media_handler = None
) -> None:
    """
    Отрисовка чата.
    
    Args:
        stdscr: Окно curses
        dialog: Объект диалога
        messages: Список сообщений
        selected_index: Индекс выбранного сообщения
        reply_mode: Флаг режима ответа
        is_loading: Флаг загрузки данных
        media_handler: Обработчик медиа
    """
    height, width = stdscr.getmaxyx()
    
    # Очистка экрана
    stdscr.clear()
    
    # Если диалог не задан
    if not dialog:
        message = "Диалог не выбран"
        message_x = max(0, (width - len(message)) // 2)
        message_y = height // 2
        stdscr.addstr(message_y, message_x, message)
        return
    
    # Отрисовка заголовка
    header = dialog_view.get_dialog_display_name(dialog)
    header_with_unread = f"{header} [{dialog.unread_count}]" if dialog.unread_count > 0 else header
    
    stdscr.attron(curses.A_BOLD)
    if curses.has_colors():
        stdscr.attron(curses.color_pair(1))  # Цвет заголовка
    
    # Ограничение длины заголовка
    if len(header_with_unread) > width - 4:
        header_with_unread = header_with_unread[:width - 7] + "..."
    
    # Центрирование заголовка
    header_x = max(0, (width - len(header_with_unread)) // 2)
    stdscr.addstr(0, header_x, header_with_unread)
    
    if curses.has_colors():
        stdscr.attroff(curses.color_pair(1))
    stdscr.attroff(curses.A_BOLD)
    
    # Отрисовка разделителя
    stdscr.addstr(1, 0, "─" * width)
    
    # Если загрузка данных в процессе и список пуст
    if is_loading and not messages:
        message = "Загрузка сообщений..."
        message_x = max(0, (width - len(message)) // 2)
        message_y = height // 2
        stdscr.addstr(message_y, message_x, message)
        return
    
    # Если список сообщений пуст
    if not messages:
        message = "Нет сообщений"
        message_x = max(0, (width - len(message)) // 2)
        message_y = height // 2
        stdscr.addstr(message_y, message_x, message)
        return
    
    # Определение видимой области
    content_height = height - 4  # За вычетом заголовка, разделителя, строки ввода и строки статуса
    
    # Подсчет общей высоты всех сообщений
    message_heights = []
    total_height = 0
    
    for msg in messages:
        # Высота информации об отправителе и времени (1 строка)
        msg_height = 1
        
        # Высота текста сообщения
        text_lines = format_message_text(msg, width - 8)
        msg_height += len(text_lines)
        
        # Добавление строки для медиа-контента, если есть
        if media_handler and hasattr(msg, 'media') and msg.media:
            msg_height += 1
        
        # Разделительная линия между сообщениями (1 строка)
        msg_height += 1
        
        message_heights.append(msg_height)
        total_height += msg_height
    
    # Вычисление начального индекса для прокрутки
    # Проверка, полностью ли помещаются все сообщения
    if total_height <= content_height:
        # Все сообщения помещаются, начинаем с первого
        start_index = 0
    else:
        # Нужна прокрутка
        # Находим сообщение, которое должно быть видимым (выбранное)
        target_index = selected_index
        
        # Вычисляем, сколько строк нужно для отображения сообщений до целевого
        lines_before_target = sum(message_heights[:target_index])
        
        # Вычисляем, сколько строк нужно для отображения целевого сообщения
        target_height = message_heights[target_index]
        
        # Определяем начальный индекс так, чтобы целевое сообщение было видимым
        if lines_before_target + target_height > content_height:
            # Целевое сообщение не помещается полностью, начинаем с него
            start_index = target_index
        else:
            # Определяем максимальное количество сообщений, которые можно показать до целевого
            start_index = target_index
            current_height = target_height
            
            for i in range(target_index - 1, -1, -1):
                if current_height + message_heights[i] <= content_height:
                    current_height += message_heights[i]
                    start_index = i
                else:
                    break
    
    # Отрисовка сообщений
    y_pos = 2  # Начальная позиция после заголовка и разделителя
    drawn_messages = 0
    
    for i in range(start_index, len(messages)):
        message = messages[i]
        msg_height = message_heights[i]
        
        # Проверка, хватает ли места для отображения текущего сообщения
        if y_pos + msg_height > height - 2:
            break
        
        # Получение информации о сообщении
        sender_name = get_sender_name(message)
        date_str = message.date.strftime("%H:%M:%S")
        
        # Формирование строки с информацией об отправителе и времени
        header_line = f"{sender_name} | {date_str}"
        
        # Выделение выбранного сообщения
        if i == selected_index:
            stdscr.attron(curses.A_REVERSE)
        
        # Отрисовка информации об отправителе и времени
        stdscr.addstr(y_pos, 4, header_line)
        y_pos += 1
        
        # Отрисовка медиа-информации, если есть
        if media_handler and hasattr(message, 'media') and message.media:
            media_info = media_handler.get_media_info(message)
            if media_info:
                media_line = media_info.get("preview_text", "[МЕДИА]")
                
                # Выделение медиа-контента цветом
                if curses.has_colors():
                    stdscr.attron(curses.color_pair(3))  # Желтый цвет для медиа
                    
                stdscr.addstr(y_pos, 6, media_line)
                
                if curses.has_colors():
                    stdscr.attroff(curses.color_pair(3))
                    
                y_pos += 1
        
        # Отрисовка текста сообщения
        text_lines = format_message_text(message, width - 8)
        for line in text_lines:
            stdscr.addstr(y_pos, 6, line)
            y_pos += 1
        
        # Сброс выделения для выбранного сообщения
        if i == selected_index:
            stdscr.attroff(curses.A_REVERSE)
        
        # Отрисовка разделителя между сообщениями
        stdscr.addstr(y_pos, 2, "-" * (width - 4))
        y_pos += 1
        
        drawn_messages += 1
    
    # Отрисовка строки ввода для режима ответа
    if reply_mode:
        input_y = height - 2
        stdscr.addstr(input_y, 0, "reply> ")
    
    # Отрисовка индикатора прокрутки
    if len(messages) > drawn_messages:
        # Вычисление позиции и размера ползунка
        scrollbar_height = max(1, int(content_height * drawn_messages / len(messages)))
        scrollbar_pos = min(
            content_height - scrollbar_height,
            int(start_index * content_height / len(messages))
        )
        
        for i in range(content_height):
            char = "█" if scrollbar_pos <= i < scrollbar_pos + scrollbar_height else "░"
            stdscr.addstr(i + 2, width - 2, char)
    
    # Индикатор, есть ли еще сообщения выше/ниже
    if start_index > 0:
        stdscr.addstr(2, width // 2, "▲")
    
    if start_index + drawn_messages < len(messages):
        stdscr.addstr(height - 3, width // 2, "▼")


def render_message_preview(
    stdscr: 'curses._CursesWindow',
    message: Message,
    width: int,
    y_pos: int,
    media_handler = None
) -> int:
    """
    Отрисовка предпросмотра сообщения (для режима ответа).
    
    Args:
        stdscr: Окно curses
        message: Объект сообщения
        width: Доступная ширина
        y_pos: Начальная позиция по вертикали
        media_handler: Обработчик медиа
        
    Returns:
        Новая позиция по вертикали после отрисовки
    """
    if not message:
        return y_pos
    
    # Получение информации о сообщении
    sender_name = get_sender_name(message)
    
    # Ограничение длины имени отправителя
    if len(sender_name) > width - 10:
        sender_name = sender_name[:width - 13] + "..."
    
    # Отрисовка заголовка предпросмотра
    stdscr.attron(curses.A_BOLD)
    stdscr.addstr(y_pos, 2, f"Ответ для {sender_name}")
    stdscr.attroff(curses.A_BOLD)
    y_pos += 1
    
    # Отрисовка медиа-информации, если есть
    if media_handler and hasattr(message, 'media') and message.media:
        media_info = media_handler.get_media_info(message)
        if media_info:
            media_line = media_info.get("preview_text", "[МЕДИА]")
            
            # Выделение медиа-контента цветом
            if curses.has_colors():
                stdscr.attron(curses.color_pair(3))  # Желтый цвет для медиа
                
            stdscr.addstr(y_pos, 4, media_line)
            
            if curses.has_colors():
                stdscr.attroff(curses.color_pair(3))
                
            y_pos += 1
    
    # Отрисовка текста сообщения
    text_lines = format_message_text(message, width - 8)
    for i, line in enumerate(text_lines):
        # Ограничение количества строк
        if i >= 3:
            stdscr.addstr(y_pos, 4, "...")
            y_pos += 1
            break
        
        stdscr.addstr(y_pos, 4, line)
        y_pos += 1
    
    # Отрисовка разделителя
    stdscr.addstr(y_pos, 2, "-" * (width - 4))
    y_pos += 1
    
    return y_pos