# AGENTS.md — Контекст для ИИ-агентов

Этот файл описывает текущее состояние проекта, принятые решения и архитектурные детали.
Обновляй его при каждом значимом изменении.

---

## Проект

**rkn-block-checker** — CLI-инструмент диагностики блокировок РКН/ТСПУ по слоям: DNS → TCP → TLS → HTTP.
Версия: `0.3.1` | Python 3.10+ | Лицензия: MIT

Точки входа:
- `python start-scan.py [флаги]` — основной способ запуска из корня проекта
- `python -m rkn_checker [флаги]` — запуск как модуль
- `rkn-check [флаги]` — если `~/.local/bin` или `%APPDATA%\Python\Scripts` в PATH

---

## Структура модулей

```
rkn_checker/
  cli.py        # argparse, точка входа main(), потоковый вывод результатов
  core.py       # оркестрация DNS → TCP → TLS → HTTP, _extract_451_reason()
  dns.py        # resolve_system(), resolve_doh() с fallback по DOH_ENDPOINTS
  network.py    # check_tcp(), check_tls() — сырые TCP и TLS-пробы
  http.py       # fetch(), looks_like_stub() — HTTP GET + детектор заглушек
  output.py     # print_header/section/result/summary — цветной CLI-отчёт
  targets.py    # WHITE_URLS, BLACK_URLS, STUB_MARKERS
  models.py     # CheckResult, Verdict, Confidence
  __main__.py   # python -m rkn_checker
start-scan.py   # удобный запуск из корня, форсирует UTF-8
```

---

## Внесённые изменения (сверх upstream v0.3.1)

### targets.py
Добавлены в `BLACK_URLS` (хостинг/CDN-провайдеры):
```python
"cloudflare", "amazon", "akamai", "aws", "ovh", "hetzner"
```

### dns.py
- Заменён один `DOH_ENDPOINT` на список `DOH_ENDPOINTS` с перебором до первого успешного.
- Добавлен парсер DNS wire-format (`_parse_dns_wire_a`) — для серверов, которые отвечают
  `application/dns-message` вместо JSON (ControlD, и др.).
- `resolve_doh()` теперь возвращает `tuple[ip, endpoint, latency_ms]` вместо просто `ip`.
- Рабочие DoH на тестовом стенде (Алматы, AS49791): `freedns.controld.com` (~1100ms),
  `dns.alidns.com` (400ms, но отдаёт 400 на некоторые запросы).
- Недоступные DoH: cloudflare, quad9, google, nextdns — TIMEOUT.

### models.py
Добавлены поля в `CheckResult`:
- `doh_endpoint: Optional[str]` — какой DoH-сервер сработал
- `doh_time_ms: Optional[float]` — задержка DoH-запроса

### core.py
- Сохраняет `doh_endpoint` и `doh_time_ms` из результата `resolve_doh()`.
- Note при успешном DoH: `DoH: <endpoint> → <ip> (<ms>ms)`.
- Добавлена `_extract_451_reason(body)` — парсит title/meta/h1/p из тела 451-ответа
  и добавляет в note человекочитаемую причину.
- Note для HTTP 451 изменён на: `HTTP 451 — сайт сообщает: недоступен по юридическим причинам (<reason>)`.

### output.py
- `_label_for()` переписана: каждый вердикт содержит русское пояснение в скобках:
  - `TLS DPI (DPI режет по SNI в TLS)`
  - `TIMEOUT (IP заблокирован / нет маршрута)`
  - `DNS_BLOCK (провайдер подменяет DNS)`
  - `TCP_RESET (провайдер рвёт TCP-соединение)`
  - `HTTP_STUB (провайдер подставляет заглушку)`
  - `DOWN (сервер недоступен)`
- Ширина колонки verdict увеличена с 22 до 42 символов, разделитель расширен до 88.

### cli.py
- В `main()` добавлен `sys.stdout.reconfigure(encoding="utf-8")` для Windows (cp1252).

### start-scan.py (новый файл)
- Удобный скрипт-обёртка в корне проекта.
- Тоже форсирует UTF-8 (на случай запуска без cli.py).

---

## Известные особенности и ограничения

- **IPv4 only** — проект намеренно не поддерживает IPv6.
- **DNS mismatch** — на CDN-сайтах (Cloudflare, Akamai) системный и DoH DNS часто отдают
  разные IP из одного пула. Это норма, не обязательно признак подмены.
- **DoH задержка** — freedns.controld.com стабильно работает, но медленно (~1с).
  Задержка DoH не влияет на вердикт, влияет только на общее время скана.
- **cp1252 в PowerShell** — при пайпинге (`| Select-String` и др.) кодировка ломается.
  Нужно: `[Console]::OutputEncoding = [System.Text.Encoding]::UTF8` перед запуском.
- **Тесты** — все сетевые вызовы в тестах замоканы. После изменения сигнатуры
  `resolve_doh()` (теперь возвращает тройку) — проверь моки в `tests/`.

---

## Триггеры обновления этого файла

- Каждые 2-3 крупных изменения в сессии.
- После смены архитектуры модуля.
- После найденной ошибки с зафиксированным способом избежать повторения.
- Перед завершением длинной многоэтапной задачи.
