# Retail ETL & Data Mart Pipeline

Production-grade ETL-пайплайн и аналитическое хранилище данных (DWH) для розничной торговли. Система собирает разнородные данные из 4 независимых источников, валидирует и очищает их, загружает в многослойное хранилище PostgreSQL и строит витрины данных с использованием аналитического SQL.

---

## 1. Архитектура решения

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                 ИСТОЧНИКИ                                   │
│  CSV (продажи)   JSON (товары)   PostgreSQL (клиенты)   REST API (остатки) │
└───────┬───────────────┬───────────────────┬────────────────────┬────────────┘
        │               │                   │                    │
        ▼               ▼                   ▼                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      ЕДИНЫЙ СЛОЙ ЭКСТРАКЦИИ (Extractors)                     │
│               BaseExtractor -> Csv / Json / Postgres / Rest                 │
│              - Экспоненциальный retry                                       │
│              - Фильтрация дельты (Incremental Checkpoint)                   │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                     ВАЛИДАЦИЯ И ОЧИСТКА (Transformers)                      │
│             - Pydantic контракты / Pandas & NumPy векторизация              │
│             - Дедупликация по бизнес-ключам                                 │
│             - Очистка NULL, выбросов (отрицательные цены/кол-во)            │
│             - Нормализация строк, email, категорий, дат                     │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           POSTGRESQL DWH (Слои)                             │
│                                                                             │
│  [staging]  stg_sales, stg_products, stg_customers, stg_inventory           │
│      │                                                                      │
│      ▼ (UPSERT / MERGE)                                                     │
│  [core]     dim_customers, dim_products, dim_stores                         │
│             fct_sales, fct_inventory_snapshots                              │
│             pipeline_runs, pipeline_state (Metadata & State)                │
│      │                                                                      │
│      ▼ (Аналитический SQL: CTE, Window Functions, JOIN)                     │
│  [marts]    dm_daily_sales, dm_store_sales, dm_product_sales                │
│             dm_average_check, dm_top_products, dm_inventory_balance         │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           ИНТЕРФЕЙСЫ ДОСТУПА                                │
│       CLI (argparse)        │         FastAPI (/api/v1/*)                   │
│  main.py run / seed / etc.  │  marts / pipeline triggers / mock source      │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Структура проекта

```
RetailDataPipeline/
├── data/raw/                  # Сырые файлы источников (sales.csv, products.json)
├── src/
│   ├── config.py              # Pydantic Settings (.env конфигурация)
│   ├── database.py            # SQLAlchemy Engine, Session, инициализация схем
│   ├── models/
│   │   ├── raw_schemas.py     # Pydantic-схемы входных данных
│   │   └── dwh_models.py      # SQLAlchemy ORM-модели (staging, core, metadata)
│   ├── extractors/
│   │   ├── base.py            # Базовый класс BaseExtractor с retry и ExtractionResult
│   │   ├── csv_extractor.py   # Экстрактор продаж из CSV
│   │   ├── json_extractor.py  # Экстрактор товаров из JSON
│   │   ├── postgres_extractor.py # Экстрактор клиентов из PostgreSQL (source_crm)
│   │   └── rest_extractor.py  # Экстрактор складских остатков по REST API
│   ├── transformers/
│   │   ├── base.py            # Базовый интерфейс трансформации TransformationResult
│   │   ├── sales_transformer.py      # Очистка, расчет сумм, валидация продаж
│   │   ├── products_transformer.py   # Очистка, маржинальность товаров
│   │   ├── customers_transformer.py  # Валидация email, форматирование ФИО
│   │   └── inventory_transformer.py  # Проверка остатков, уровней дозаказа
│   ├── loaders/
│   │   └── dwh_loader.py      # Загрузка в staging и идемпотентный MERGE/UPSERT в core
│   ├── marts/
│   │   ├── sql_queries.py     # SQL-скрипты витрин (CTE, оконные функции, индексы)
│   │   └── mart_builder.py    # Сервис пересчета и индексации витрин
│   ├── services/
│   │   ├── pipeline_service.py # Оркестрация ETL, аудит запусков и подсчет строк
│   │   ├── state_service.py    # Управление чекпоинтами инкрементальной загрузки
│   │   └── seeder_service.py   # Генерация реалистичных данных во все 4 источника
│   └── api/
│       ├── app.py             # Точка входа FastAPI приложения
│       └── routes/
│           ├── source_mock.py # REST API источника остатков (/api/v1/source/inventory)
│           ├── pipeline.py    # Управление запусками и история (/api/v1/pipeline/*)
│           └── marts.py       # API для аналитических витрин (/api/v1/marts/*)
├── tests/                     # Автотесты (Pytest)
│   ├── conftest.py
│   ├── test_extractors.py
│   ├── test_transformers.py
│   ├── test_pipeline.py
│   └── test_marts.py
├── docker-compose.yml         # Запуск PostgreSQL и приложения в Docker
├── Dockerfile                 # Multi-stage/Slim образ для Linux-окружения
├── requirements.txt           # Зависимости проекта
├── pyproject.toml             # Конфигурация инструментов (pytest)
├── main.py                    # CLI-интерфейс и запуск веб-сервера
└── README.md                  # Архитектурная документация
```

---

## 3. Аналитические витрины данных (SQL & Window Functions)

В схеме `marts` построены 6 витрин данных:

| Витрина | Назначение | Использованный SQL-функционал |
|---|---|---|
| `marts.dm_daily_sales` | Динамика выручки, чеков и клиентов по дням | `SUM() OVER(PARTITION BY DATE_TRUNC('month', sale_date) ORDER BY sale_date)` (нарастающий итог месяца), `LAG()` (выручка предыдущего дня), `dod_growth_pct` (темп прироста день-к-дню). |
| `marts.dm_store_sales` | Эффективность торговых точек | `DENSE_RANK() OVER(ORDER BY total_revenue DESC)` (рейтинг магазина), `100.0 * total_revenue / SUM(total_revenue) OVER()` (доля выручки точки в сети). |
| `marts.dm_product_sales` | Продажи и прибыльность товаров | `DENSE_RANK() OVER(PARTITION BY category ORDER BY total_revenue DESC)` (ранг товара в категории), расчет доли выручки в категории. |
| `marts.dm_average_check` | Анализ чеков по магазинам и дням | `CTE (order_totals)` для вычисления суммы корзины, `AVG() OVER(PARTITION BY store_id)` (средний чек по магазину), расчет отклонения дневного чека от среднего. |
| `marts.dm_top_products` | Топ-5 товаров в каждой категории | `CTE + ROW_NUMBER() OVER(PARTITION BY category ORDER BY total_revenue DESC)` с фильтрацией `WHERE rank_in_category <= 5`. |
| `marts.dm_inventory_balance` | Оборачиваемость и остатки | `DISTINCT ON` для последней ревизии склада, `CTE` скорости продаж за 30 дней, расчет дней запаса, классификация статуса (`OUT_OF_STOCK`, `CRITICAL_LOW`, `OPTIMAL`, `OVERSTOCK`), `RANK() OVER(...)`. |

### Индексы и оптимизация
- Индексы на таблице фактов: `core.fct_sales(sale_date)`, `core.fct_sales(store_id, sale_date)`, `core.fct_sales(product_id)`, `core.fct_sales(customer_id)`.
- Индексы на витринах для быстрых выборок: `marts.dm_daily_sales(sale_date)`, `marts.dm_store_sales(revenue_rank)`, `marts.dm_top_products(category, rank_in_category)`, `marts.dm_inventory_balance(stock_status)`.

---

## 4. Почему сделано именно так, а не иначе (Архитектурные решения)

### 1. Выделение схем `source_crm`, `staging`, `core`, `marts` вместо единой схемы `public`
- **Причина**: Имитация реального корпоративного DWH (Medallion Architecture: Bronze/Silver/Gold).
- **Плюсы**: Изоляция сырых данных от витрин, возможность пересоздания промежуточных слоев без блокировки аналитиков, разделение прав доступа на уровне ролей СУБД.

### 2. Единый интерфейс экстракторов (`BaseExtractor`)
- **Причина**: Полиморфизм и расширяемость. Добавление нового источника (например, Kafka или S3) сводится к созданию класса-наследника `BaseExtractor` с методом `extract()`.
- **Плюсы**: Встроенная обработка сбоев (`_execute_with_retry` с экспоненциальной задержкой) и унифицированный формат передачи (`ExtractionResult`).

### 3. Pydantic + Pandas / NumPy вместо валидации построчно
- **Причина**: Скорость и надежность. Валидация Pydantic задает строгие контракты типов данных, а Pandas и векторизованный NumPy позволяют очищать, дедуплицировать и фильтровать сотни тысяч строк за доли секунды.

### 4. Идемпотентность загрузки (`ON CONFLICT DO UPDATE`)
- **Причина**: Защита от дубликатов при повторных запусках пайплайна или частичных сбоях. Повторный запуск ETL с тем же батчем обновляет существующие записи, не создавая фантомных дублей.

### 5. Инкрементальная загрузка (Incremental Checkpoint)
- **Причина**: В таблице `core.pipeline_state` сохраняется метка последнего обновленного события (`last_extracted_at`) для каждого источника. Это исключает полную вычитку всех исторических данных при регулярном расписании.

### 6. Аудит и телеметрия (`core.pipeline_runs`)
- **Причина**: Полная прозрачность. Каждый запуск регистрирует `run_id`, тип запуска (`FULL` / `INCREMENTAL`), статус (`SUCCESS` / `FAILED`), продолжительность, число извлеченных и загруженных строк, а также детализацию по отброшенным некорректным строкам.

### 7. Гибридная роль FastAPI
- **Причина**: Предоставление как эндпоинта для внешнего источника остатков (`/api/v1/source/inventory`), так и аналитического API-шлюза для витрин и управления пайплайном без необходимости разворачивать сторонние инструменты оркестрации для локальной разработки.

---

## 5. Инструкция по запуску и использованию

### Вариант 1: Запуск через Docker Compose (Рекомендуемый)

```bash
# Сборка и запуск PostgreSQL и сервиса
docker compose up -d

# Запуск наполнения тестовыми данными
docker compose exec app python main.py seed

# Запуск полного ETL пайплайна
docker compose exec app python main.py run --type FULL

# Запуск тестов
docker compose exec app pytest -v
```

Веб-интерфейс Swagger/OpenAPI доступен по адресу: `http://localhost:8000/docs`

---

### Вариант 2: Локальный запуск (Windows / Linux)

1. **Запустить PostgreSQL** (через Docker или локальную службу):
```bash
docker compose up -d postgres
```

2. **Активировать виртуальное окружение и установить зависимости**:
```bash
# Windows
.venv\Scripts\activate
pip install -r requirements.txt

# Linux / MacOS
source .venv/bin/activate
pip install -r requirements.txt
```

3. **Сгенерировать тестовые источники (CSV, JSON, CRM в Postgres, остатки)**:
```bash
python main.py seed
```

4. **Выполнить ETL-пайплайн**:
```bash
# Полная загрузка:
python main.py run --type FULL

# Инкрементальная загрузка:
python main.py run --type INCREMENTAL
```

5. **Посмотреть историю запусков**:
```bash
python main.py history --limit 10
```

6. **Запустить API сервер**:
```bash
python main.py serve
```

7. **Запустить тесты (20 тестов Pytest)**:
```bash
pytest -v
```

---

## 6. Примеры работы с REST API

- `POST /api/v1/pipeline/run` — запуск пайплайна (`{"run_type": "INCREMENTAL"}` или `{"run_type": "FULL"}`)
- `GET /api/v1/pipeline/history` — история и метрики выполненных загрузок
- `GET /api/v1/source/inventory?limit=50&updated_after=2026-01-01T00:00:00` — эндпоинт внешнего источника остатков
- `GET /api/v1/marts/daily-sales` — витрина дневных продаж и темпов прироста
- `GET /api/v1/marts/store-sales` — витрина продаж по магазинам и их долей в выручке сети
- `GET /api/v1/marts/product-sales` — витрина продаж по товарам
- `GET /api/v1/marts/average-check` — витрина среднего чека и отклонений
- `GET /api/v1/marts/top-products` — топ-5 товаров в каждой категории
- `GET /api/v1/marts/inventory-balance` — витрина товарных остатков со статусами запасов
