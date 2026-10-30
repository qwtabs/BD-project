import sqlite3
import json
import time


# ИМИТАЦИЯ НЕРЕЛЯЦИОННОЙ БАЗЫ ДАННЫХ (REDIS)

class MockRedis:
    def __init__(self):
        self.store = {}
        self.ttl = {}
        print("[Redis] Подключено к нереляционной БД (Key-Value)")

    def setex(self, key, seconds, value):
        self.store[key] = value
        self.ttl[key] = time.time() + seconds
        print(f"[Redis] Данные сохранены в кэш: {key} (TTL: {seconds} сек.)")

    def get(self, key):
        if key in self.store:
            if time.time() < self.ttl[key]:
                print(f"[Redis] КЭШ-ПОПАДАНИЕ (Cache Hit): {key}")
                return self.store[key]
            else:
                del self.store[key]
                print(f"[Redis] Кэш устарел (TTL истек): {key}")
        print(f"[Redis] КЭШ-ПРОМАХ (Cache Miss): {key}")
        return None


# РЕЛЯЦИОННАЯ БАЗА ДАННЫХ (POSTGRESQL/SQLITE)

def init_db():
    print("[PostgreSQL] Подключение к реляционной БД...")
    conn = sqlite3.connect('shop.db')
    cursor = conn.cursor()
    # Создаем таблицу, если ее нет
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            price REAL NOT NULL
        )
    ''')
    # Добавляем тестовые данные
    cursor.execute("INSERT OR IGNORE INTO products (id, name, price) VALUES (1, 'Ноутбук', 99990.0)")
    cursor.execute("INSERT OR IGNORE INTO products (id, name, price) VALUES (2, 'Мышка', 2500.0)")
    conn.commit()
    conn.close()

def get_product_from_db(product_id):
    print(f"[PostgreSQL] Запрос к реляционной БД для товара ID={product_id}...")
    conn = sqlite3.connect('shop.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, price FROM products WHERE id = ?", (product_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {"id": row[0], "name": row[1], "price": row[2]}
    return None


# ОСНОВНАЯ ЛОГИКА (ПАТТЕРН CACHE-ASIDE)

def get_product(product_id):
    cache_key = f"product:{product_id}"
    
    # 1. Пытаемся получить данные из нереляционной БД (Кэш)
    cached_data = redis.get(cache_key)
    if cached_data:
        return json.loads(cached_data)
    
    # 2. Если в кэше нет, идем в реляционную БД
    db_data = get_product_from_db(product_id)
    
    # 3. Если данные найдены, сохраняем их в кэш на 5 секунд
    if db_data:
        redis.setex(cache_key, 5, json.dumps(db_data))
        
    return db_data


# ЗАПУСК И ТЕСТИРОВАНИЕ

if __name__ == "__main__":
    # Инициализация
    init_db()
    redis = MockRedis()
    
    print("\n--- Запрос 1: Ноутбук (Первый раз) ---")
    print("Результат:", get_product(1))
    
    print("\n--- Запрос 2: Ноутбук (Сразу же) ---")
    
    print("Результат:", get_product(1))
    
    print("\n--- Запрос 3: Мышка (Новый товар) ---")
    print("Результат:", get_product(2))
    
    print("\n--- Ждем 6 секунд, пока кэш устареет... ---")
    time.sleep(6)
    
    print("\n--- Запрос 4: Ноутбук (После истечения TTL) ---")
    # Кэш должен устареть, и программа снова пойдет в реляционную БД
    print("Результат:", get_product(1))
