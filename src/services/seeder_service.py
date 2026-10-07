import json
import random
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List
import pandas as pd
from sqlalchemy import text
from src.config import settings
from src.database import engine, init_db_schemas


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class SeederService:
    def __init__(self):
        self.data_dir = settings.DATA_DIR / "raw"
        self.sales_path = settings.RAW_CSV_SALES_PATH
        self.products_path = settings.RAW_JSON_PRODUCTS_PATH
        self.stores = [f"STR_{i:02d}" for i in range(1, 11)]
        self.categories = ["Electronics", "Groceries", "Clothing", "Home & Kitchen", "Sports"]

    def seed_all(self) -> Dict[str, int]:
        init_db_schemas()
        self.data_dir.mkdir(parents=True, exist_ok=True)

        prod_count = self.seed_products_json()
        cust_count = self.seed_customers_postgres()
        sales_count = self.seed_sales_csv()
        inv_count = len(self.get_mock_inventory_items())

        return {
            "products_json": prod_count,
            "customers_postgres": cust_count,
            "sales_csv": sales_count,
            "inventory_records": inv_count
        }

    def seed_products_json(self) -> int:
        products = []
        base_time = utc_now() - timedelta(days=60)

        for i in range(1, 31):
            category = self.categories[(i - 1) % len(self.categories)]
            cost_price = round(random.uniform(5.0, 150.0), 2)
            retail_price = round(cost_price * random.uniform(1.3, 2.5), 2)
            products.append({
                "product_id": f"PRD_{i:03d}",
                "product_name": f"{category} Item {i}",
                "category": category,
                "brand": f"Brand {chr(65 + (i % 5))}",
                "cost_price": cost_price,
                "retail_price": retail_price,
                "is_active": True,
                "updated_at": (base_time + timedelta(days=i)).isoformat()
            })

        products.append({
            "product_id": "PRD_001",
            "product_name": "Electronics Item 1 (Duplicate Update)",
            "category": "Electronics",
            "brand": "Brand B",
            "cost_price": 50.0,
            "retail_price": 95.0,
            "is_active": True,
            "updated_at": utc_now().isoformat()
        })
        products.append({
            "product_id": "PRD_DIRTY_1",
            "product_name": "Broken Price Product",
            "category": "Electronics",
            "brand": "BadBrand",
            "cost_price": 10.0,
            "retail_price": -5.0,
            "is_active": True,
            "updated_at": utc_now().isoformat()
        })

        self.products_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.products_path, "w", encoding="utf-8") as f:
            json.dump({"products": products}, f, indent=2, ensure_ascii=False)

        return len(products)

    def seed_customers_postgres(self) -> int:
        create_table_sql = """
            CREATE TABLE IF NOT EXISTS source_crm.customers (
                id VARCHAR(64) PRIMARY KEY,
                first_name VARCHAR(100) NOT NULL,
                last_name VARCHAR(100) NOT NULL,
                email VARCHAR(255),
                phone VARCHAR(50),
                city VARCHAR(100),
                loyalty_tier VARCHAR(50),
                created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (NOW() AT TIME ZONE 'utc'),
                updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (NOW() AT TIME ZONE 'utc')
            );
            TRUNCATE TABLE source_crm.customers;
        """
        with engine.begin() as conn:
            conn.execute(text(create_table_sql))

        first_names = ["Alex", "Maria", "Dmitry", "Elena", "Ivan", "Anna", "Sergey", "Olga", "Pavel", "Natalia"]
        last_names = ["Ivanov", "Petrov", "Smirnov", "Sokolov", "Popov", "Kuznetsov", "Novikov", "Fedorov", "Morozov", "Volkov"]
        cities = ["Moscow", "Saint Petersburg", "Novosibirsk", "Yekaterinburg", "Kazan"]
        tiers = ["Bronze", "Silver", "Gold", "Platinum"]

        records = []
        base_time = utc_now() - timedelta(days=90)

        for i in range(1, 101):
            fn = random.choice(first_names)
            ln = random.choice(last_names)
            email = f"{fn.lower()}.{ln.lower()}{i}@example.com" if i % 10 != 0 else f"invalid-email-{i}"
            records.append({
                "id": f"CUST_{i:04d}",
                "first_name": fn,
                "last_name": ln,
                "email": email,
                "phone": f"+7999{i:07d}",
                "city": random.choice(cities),
                "loyalty_tier": random.choice(tiers),
                "created_at": base_time + timedelta(days=i % 60),
                "updated_at": base_time + timedelta(days=i % 60)
            })

        df = pd.DataFrame(records)
        df.to_sql(name="customers", schema="source_crm", con=engine, if_exists="append", index=False)
        return len(records)

    def seed_sales_csv(self) -> int:
        records = []
        base_date = date.today() - timedelta(days=30)
        methods = ["CARD", "CASH", "QR", "ONLINE"]

        for i in range(1, 1001):
            sale_date = base_date + timedelta(days=random.randint(0, 30))
            store_id = random.choice(self.stores)
            product_id = f"PRD_{random.randint(1, 30):03d}"
            customer_id = f"CUST_{random.randint(1, 100):04d}" if random.random() > 0.15 else None
            qty = random.randint(1, 5)
            unit_price = round(random.uniform(10.0, 300.0), 2)
            discount = random.choice([0.0, 0.05, 0.10, 0.15, 0.20])
            total_amount = round(qty * unit_price * (1.0 - discount), 2)

            records.append({
                "sale_id": f"SALE_{i:06d}",
                "sale_date": sale_date.isoformat(),
                "store_id": store_id,
                "product_id": product_id,
                "customer_id": customer_id,
                "quantity": qty,
                "unit_price": unit_price,
                "discount": discount,
                "total_amount": total_amount,
                "payment_method": random.choice(methods),
                "updated_at": (datetime.combine(sale_date, datetime.min.time()) + timedelta(hours=random.randint(8, 22))).isoformat()
            })

        records.append({
            "sale_id": "SALE_000001",
            "sale_date": base_date.isoformat(),
            "store_id": "STR_01",
            "product_id": "PRD_001",
            "customer_id": "CUST_0001",
            "quantity": 2,
            "unit_price": 50.0,
            "discount": 0.0,
            "total_amount": 100.0,
            "payment_method": "CARD",
            "updated_at": utc_now().isoformat()
        })
        records.append({
            "sale_id": "SALE_DIRTY_QTY",
            "sale_date": base_date.isoformat(),
            "store_id": "STR_01",
            "product_id": "PRD_001",
            "customer_id": "CUST_0001",
            "quantity": -2,
            "unit_price": 50.0,
            "discount": 0.0,
            "total_amount": 0.0,
            "payment_method": "CARD",
            "updated_at": utc_now().isoformat()
        })

        df = pd.DataFrame(records)
        self.sales_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(self.sales_path, index=False)
        return len(records)

    def get_mock_inventory_items(self, checkpoint: Any = None) -> List[Dict[str, Any]]:
        items = []
        base_time = utc_now()

        for s_idx in range(1, 11):
            store_id = f"STR_{s_idx:02d}"
            for p_idx in range(1, 31):
                product_id = f"PRD_{p_idx:03d}"
                qty = random.randint(0, 150)
                reorder = random.randint(10, 30)
                restock_date = (date.today() - timedelta(days=random.randint(1, 20))).isoformat()
                upd_at = base_time - timedelta(days=random.randint(0, 5))

                if checkpoint is not None:
                    chk_dt = pd.to_datetime(checkpoint)
                    if upd_at <= chk_dt:
                        continue

                items.append({
                    "store_id": store_id,
                    "product_id": product_id,
                    "quantity_on_hand": qty,
                    "reorder_level": reorder,
                    "last_restock_date": restock_date,
                    "updated_at": upd_at.isoformat()
                })
        return items
