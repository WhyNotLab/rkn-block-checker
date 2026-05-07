# INSTRUCTION.md — Руководство пользователя

## Что это

**rkn-block-checker** диагностирует блокировки РКН/ТСПУ, проходя каждый сетевой слой отдельно:
`DNS → TCP → TLS → HTTP`. В отличие от браузера, который говорит просто «сайт недоступен»,
инструмент показывает **где именно и что сломалось** — и значит, понятно, как это обойти.

---

## Установка

**Из PyPI:**
```powershell
pip install rkn-block-checker
```

**Из исходников:**
```powershell
git clone https://github.com/MayersScott/rkn-block-checker.git
cd rkn-block-checker
pip install -e .
```

---

## Запуск

```powershell
# Из корня проекта (рекомендуется на Windows)
python start-scan.py

# Через модуль
python -m rkn_checker

# Глобальная команда (если Scripts в PATH)
rkn-check
```

### Добавить rkn-check в PATH (Windows, однократно)
```powershell
[System.Environment]::SetEnvironmentVariable(
  "PATH",
  $env:PATH + ";$env:APPDATA\Python\Python313\Scripts",
  [System.EnvironmentVariableTarget]::User
)
```

### Исправить кодировку в PowerShell (если кракозябры)
```powershell
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
python start-scan.py
```

---

## Флаги

| Флаг | Описание |
|---|---|
| `--white` | только whitelist (госсайты, банки, соцсети РФ) |
| `--black` | только blacklist (заблокированные РКН сайты) |
| `--json` | вывод в JSON вместо цветного отчёта |
| `--timeout N` | таймаут на каждый пробник в секундах (по умолчанию 5) |
| `--workers N` | размер пула потоков (по умолчанию 10) |
| `--white-file PATH` | свой список whitelist из `.txt` или `.json` |
| `--black-file PATH` | свой список blacklist из `.txt` или `.json` |
| `--no-self-info` | не показывать IP/ISP в шапке |
| `-v` / `-vv` | verbose-логирование (INFO / DEBUG) |

**Примеры:**
```powershell
python start-scan.py --black --timeout 3
python start-scan.py --white --workers 5
python start-scan.py --json | python -m json.tool
```

---

## Как читать вывод

### Шапка
```
IP:       1.2.3.4
ISP:      AS12345 ОАО Ромашка
Location: Москва, RU
```
Показывает с какого IP и провайдера идёт проверка.

### Таблица результатов

```
name          verdict                                  TCP    TLS    PLT  status
────────────────────────────────────────────────────────────────────────────────
instagram     ? TIMEOUT (IP заблокирован / нет маршрута)  -      -      -   -
  └ TCP timeout on port 443 — could be IP block...
facebook      ~ TLS DPI (DPI режет по SNI в TLS)?      62ms    -      -   -
  └ DoH: https://freedns.controld.com/dns-query → 157.240.20.1 (490ms)
  └ TLS handshake silently dropped...
gosuslugi     ✓ OK                                     38ms  77ms  1208ms  200
  └ DoH: https://freedns.controld.com/dns-query → 95.181.182.36 (460ms)
```

**Колонки:**
- **TCP** — время TCP-хендшейка на порт 443 (`-` = не дошло до этого шага)
- **TLS** — время TLS-хендшейка (`-` = обрыв на TLS или раньше)
- **PLT** — время получения HTTP-ответа
- **status** — HTTP-код ответа

### Вердикты

| Вердикт | Значение | Что делать |
|---|---|---|
| `✓ OK` | Сайт доступен | — |
| `✗ DNS_BLOCK (провайдер подменяет DNS)` | Системный DNS врёт, DoH знает правильный IP | Сменить DNS на 1.1.1.1 или использовать DoH |
| `~ TLS DPI (DPI режет по SNI в TLS)?` | TCP проходит, DPI читает SNI и рвёт TLS | VPN / ECH / ESNI |
| `✗ TCP_RESET (провайдер рвёт TCP-соединение)` | IP-уровневая блокировка | VPN / прокси |
| `✗ HTTP_STUB (провайдер подставляет заглушку)` | Провайдерская страница-заглушка | VPN / прокси |
| `? TIMEOUT (IP заблокирован / нет маршрута)` | Соединение не устанавливается | VPN / прокси |
| `· DOWN (сервер недоступен)` | DNS не резолвится нигде, сервер лежит | Ждать или проверить позже |

**Уровни уверенности:**
- `✗` (красный) — **HIGH**: два независимых сигнала подтверждают блокировку
- `~` (жёлтый) — **MEDIUM**: паттерн похож на блокировку, но возможны другие причины
- `?` (серый) — **LOW**: симптом неоднозначен

### Строки с `└`

Дополнительные детали под каждым результатом:
- `DoH: <сервер> → <ip> (<ms>)` — какой DoH сработал, какой IP вернул и за сколько
- `DNS mismatch: sys=X vs doh=Y` — системный DNS вернул другой IP (возможна подмена или CDN-ротация)
- `TLS handshake silently dropped` — TLS оборвался без RST (типичный ТСПУ)
- `TLS reset right after ClientHello` — RST после ClientHello (SNI-фильтрация)
- `HTTP 451 — сайт сообщает: ... (причина)` — сам сервер отказывает по юридическим причинам

---

## Добавить свои сайты

Отредактируй [rkn_checker/targets.py](rkn_checker/targets.py):

```python
# Добавить в BLACK_URLS
BLACK_URLS: dict[str, str] = {
    ...
    "мой-сайт": "https://example.com/",
}
```

Или передай свой список файлом:
```
# my-sites.txt — по одному URL на строку
https://example.com/
https://another.com/
```
```powershell
python start-scan.py --black-file my-sites.txt
```

---

## JSON-вывод и обработка

```powershell
# Все заблокированные
python start-scan.py --json | python -c "
import json, sys
d = json.load(sys.stdin)
for r in d['blacklist']:
    if r['verdict'] != 'OK':
        print(r['name'], r['verdict'])
"

# Только TLS DPI
python start-scan.py --json | python -c "
import json, sys
d = json.load(sys.stdin)
for r in d['blacklist']:
    if r['verdict'] == 'TLS_BLOCK':
        print(r['name'], r.get('doh_endpoint','?'), r.get('tls_error',''))
"
```

---

## DoH-серверы

Инструмент перебирает серверы по очереди и использует первый сработавший.
Текущий список (`rkn_checker/dns.py`):

| Сервер | Формат | Примечание |
|---|---|---|
| cloudflare-dns.com | JSON | часто заблокирован в РФ |
| freedns.controld.com | wire | работает, ~1с |
| dns.quad9.net | JSON | заблокирован в РФ |
| dns.google | JSON | заблокирован в РФ |
| dns.alidns.com | JSON | Alibaba, работает |
| dns.nextdns.io | JSON | иногда недоступен |

Если все DoH недоступны — вердикты по DNS-сравнению будут недостоверны,
в строках `└` появится: `DoH lookup failed — control comparison unavailable`.
