import sqlite3
import pandas as pd

print("Чтение CSV файла...")
# Указываем правильную кодировку для символов фунта £
df = pd.read_csv('online_retail_II.csv', encoding='ISO-8859-1')

print("Очистка данных...")
# 1. Убираем пустые Customer ID
df = df.dropna(subset=['Customer ID'])

# 2. Убираем возвраты и нулевые цены
df = df[(df['Quantity'] > 0) & (df['Price'] > 0)]

# 3. Убираем чеки отмен (начинаются с C)
df = df[~df['Invoice'].astype(str).str.startswith('C')]

# Приводим типы
df['Customer ID'] = df['Customer ID'].astype(int)
df['InvoiceDate'] = pd.to_datetime(df['InvoiceDate'])
df['TotalAmount'] = df['Quantity'] * df['Price']

print("Создание базы данных retail.db...")
conn = sqlite3.connect('retail.db')
df.to_sql('retail_clean', conn, if_exists='replace', index=False)
conn.close()

print(f"Готово! База retail.db успешно создана. Загружено строк: {len(df):,}")