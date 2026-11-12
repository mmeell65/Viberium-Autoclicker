<div align="center">

<img src="docs/screenshots/icon.png" width="104" alt="Viberium" />

# Viberium

**Современный автокликер для Windows: тонкая настройка, макросы, горячие клавиши и две темы оформления.**

[![Website](https://img.shields.io/badge/🌐_сайт-mmeell65.github.io-5b8cff?style=flat-square)](https://mmeell65.github.io/Viberium-Autoclicker/)
[![Release](https://img.shields.io/github/v/release/mmeell65/Viberium-Autoclicker?color=5b8cff&label=релиз)](../../releases/latest)
[![Downloads](https://img.shields.io/github/downloads/mmeell65/Viberium-Autoclicker/total?color=5b8cff&label=скачиваний)](../../releases/latest)
[![Stars](https://img.shields.io/github/stars/mmeell65/Viberium-Autoclicker?color=5b8cff&label=звёзд)](../../stargazers)
[![Platform](https://img.shields.io/badge/platform-Windows%2010%20%7C%2011-0078D6?logo=windows&logoColor=white)](#системные-требования)
[![Python](https://img.shields.io/badge/python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![PySide6](https://img.shields.io/badge/PySide6-Qt%206-41CD52?logo=qt&logoColor=white)](https://doc.qt.io/qtforpython/)
[![License: MIT](https://img.shields.io/badge/license-MIT-5b8cff.svg)](LICENSE)
[![Build](https://github.com/mmeell65/Viberium-Autoclicker/actions/workflows/build.yml/badge.svg)](https://github.com/mmeell65/Viberium-Autoclicker/actions/workflows/build.yml)
[![Telegram](https://img.shields.io/badge/Telegram-канал-26A5E4?logo=telegram&logoColor=white)](https://t.me/viberium_autoclicker)

[![Скачать для Windows](https://img.shields.io/badge/%D0%A1%D0%BA%D0%B0%D1%87%D0%B0%D1%82%D1%8C_Windows-5b8cff?style=for-the-badge&logo=windows&logoColor=white)](../../releases/latest/download/Viberium-windows.zip)
[![🌐 Сайт проекта](https://img.shields.io/badge/🌐_%D1%81%D0%B0%D0%B9%D1%82-1f2a44?style=for-the-badge)](https://mmeell65.github.io/Viberium-Autoclicker/)
[![💬 Telegram-канал](https://img.shields.io/badge/💬_Telegram-26A5E4?style=for-the-badge&logo=telegram&logoColor=white)](https://t.me/viberium_autoclicker)

[Скачать](#скачать) · [Что нового](#что-нового-в-110) · [Возможности](#возможности) · [Скриншоты](#скриншоты) · [Сайт](https://mmeell65.github.io/Viberium-Autoclicker/) · [Telegram](#telegram) · [English](README.en.md)

</div>

![Viberium — автокликер мыши, тёмная тема](docs/screenshots/mouse-dark.png)

---

## Что нового в 1.1.0

- **Клавиатурный автокликер**: несколько клавиш и сочетаний одновременно, режимы «Одновременно» и «По очереди» с паузой между нажатиями.
- **Захват сочетаний** с Ctrl, Shift, Alt и Win — левые и правые модификаторы распознаются корректно.
- **Перестановка кнопок** стрелками и удаление ненужных строк.
- **Лендинг проекта**: [mmeell65.github.io/Viberium-Autoclicker](https://mmeell65.github.io/Viberium-Autoclicker/) — обзор, скриншоты и FAQ.
- **Telegram-канал** со ссылкой прямо в приложении.

[Полный список изменений](CHANGELOG.md) · [Скачать 1.1.0](../../releases/latest)

## Автокликер для Windows

Viberium — автокликер для Windows с полностью кастомным интерфейсом. Он работает с системным вводом напрямую, поэтому клики и нажатия получаются точными и плавными — без задержек браузера и лишних посредников.

Внутри — всё, что нужно для рутинных действий: кликер мыши, кликер клавиатуры, запись макросов, глобальные горячие клавиши и работа только в выбранном окне. Интерфейс на русском и английском, тёмная и светлая темы.

Проект задуман как инструмент для **своих задач на своих устройствах**: повторяющиеся клики, тестирование интерфейсов, автоматизация рутины в программах. Пожалуйста, не используйте его для нарушения правил игр и сервисов.

## Telegram

Новости, обновления и советы по Viberium — в телеграм-канале **[@viberium_autoclicker](https://t.me/viberium_autoclicker)**.

## Возможности

<table>
<tr>
<td width="50%" valign="top">

### 🖱️ Автокликер мыши
- Кнопка: **ЛКМ / ПКМ / СКМ**
- Тип клика: одинарный, двойной, тройной
- Интервал в миллисекундах + быстрые пресеты
- Случайный разброс интервала (0–100 %)
- Длительность зажатия кнопки
- Позиция: за курсором или фиксированная точка
- Разброс позиции (jitter)
- Лимит по количеству кликов и по времени
- Остановка при движении мыши
- Задержка перед стартом

### ⌨️ Автокликер клавиатуры
- Несколько клавиш и сочетаний одновременно
- Режимы: одновременное нажатие или по очереди
- Захват сочетаний с Ctrl, Shift, Alt, Win
- Перестановка кнопок и пауза между ними
- Интервал, разброс, длительность нажатия
- Лимиты и задержка перед стартом

</td>
<td width="50%" valign="top">

### 🎬 Макросы
- Запись кликов, движения мыши и клавиш
- Воспроизведение со своей скоростью
- Повторы и библиотека макросов
- Импорт и экспорт в JSON

### ⌨️🔥 Горячие клавиши
- Отдельные комбинации для мыши, клавиатуры и макросов
- Старт/стоп, удержание для работы
- Экстренный стоп — **F8**
- Сочетания с Ctrl, Alt, Shift, Win
- Боковые кнопки мыши **X1 / X2**
- Сброс комбинации кнопкой **×**

### 🪟 Целевое окно
- Работа только в выбранном окне
- Если окно не активно — клики на паузе
- Если окно не выбрано — работа везде
- Процесс не сохраняется в профилях

### 🎨 Оболочка
- Тёмная и светлая темы
- Статистика: клики, CPS, время работы
- Трей, поверх всех окон, автозапуск
- Русский и английский языки
- Профили настроек

</td>
</tr>
</table>

## Скриншоты

| Тёмная тема | Светлая тема |
|:---:|:---:|
| ![Клавиатура — тёмная](docs/screenshots/keyboard-dark.png) | ![Клавиатура — светлая](docs/screenshots/keyboard-light.png) |
| ![Макросы — тёмная](docs/screenshots/macros-dark.png) | ![Макросы — светлая](docs/screenshots/macros-light.png) |
| ![Настройки — тёмная](docs/screenshots/settings-dark.png) | ![Настройки — светлая](docs/screenshots/settings-light.png) |

## Скачать

Готовые сборки лежат в разделе **[Releases](../../releases)**.

**Прямая ссылка на последнюю сборку:**
[`Viberium-windows.zip`](../../releases/latest/download/Viberium-windows.zip) · [страница релиза](../../releases/latest) · [сайт проекта](https://mmeell65.github.io/Viberium-Autoclicker/)

1. Скачайте `Viberium-windows.zip`.
2. Распакуйте архив **целиком** в любую папку.
3. Запустите `Viberium.exe`.

> **Важно:** `Viberium.exe` и папка `_internal` должны лежать рядом. Не вытаскивайте `.exe` из архива по отдельности — приложение не запустится.

Установка не требуется. Настройки хранятся в `%APPDATA%\Viberium`.

> **SmartScreen.** При первом запуске Windows может показать предупреждение о неизвестном издателе — это нормально для неподписанных приложений. Нажмите «Подробнее» → «Выполнить в любом случае». Антивирусы могут реагировать на глобальные хуки ввода.

## Системные требования

| | |
|---|---|
| ОС | Windows 10 / 11 (64-bit) |
| Свободное место | около 100 МБ |
| Дополнительные программы | не требуются |

## Горячие клавиши

По умолчанию назначен только экстренный стоп — **F8**. Остальные комбинации вы выбираете сами на страницах «Кликер», «Клавиатура» и «Макросы».

- Комбинации работают глобально, в том числе когда окно свёрнуто в трей.
- Поддерживаются Ctrl, Alt, Shift, Win и боковые кнопки мыши X1/X2.
- Повторное нажатие на поле захвата отменяет запись и очищает комбинацию; кнопка **×** делает то же самое.

## Где ещё найти Viberium

| | |
|---|---|
| 🌐 Сайт проекта | [mmeell65.github.io/Viberium-Autoclicker](https://mmeell65.github.io/Viberium-Autoclicker/) |
| ⬇ Релизы | [GitHub Releases](../../releases/latest) |
| 💬 Telegram-канал | [@viberium_autoclicker](https://t.me/viberium_autoclicker) |
| 🗂 Каталог софта | [AlternativeTo](https://alternativeto.net/software/viberium/) |
| 🐛 Баг-репорты | [Issues](../../issues) |

## Лицензия

[MIT](LICENSE) © 2026 Viberium

## Предостережение

Программа предназначена для автоматизации своих задач на своих устройствах. Не используйте её для нарушения правил игр, сервисов или законодательства.
