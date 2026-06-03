import pandas as pd
import matplotlib.pyplot as plt
from sqlalchemy import create_engine

# ============================================================================
# 1. ПОДКЛЮЧЕНИЕ К БАЗЕ ДАННЫХ
# ============================================================================

print("=" * 70)
print("📊 АНАЛИЗ БАЗЫ ДАННЫХ (products, prices, suppliers)")
print("=" * 70)

try:
    engine = create_engine("postgresql+psycopg2://postgres:student@localhost:5435/student_task")
    connection = engine.connect()
    print("✅ Подключение к базе данных установлено")
except Exception as e:
    print(f"❌ Ошибка подключения: {e}")
    raise SystemExit

# ============================================================================
# 2. ИЗВЛЕЧЕНИЕ ДАННЫХ
# ============================================================================

print("\n📂 Загрузка данных...")

# Запрос 1: средняя цена по категориям
df_categories = pd.read_sql("""
    SELECT 
        p.category,
        ROUND(AVG(pr.price)::numeric, 2) AS avg_price,
        COUNT(pr.price) AS total_products,
        MIN(pr.price) AS min_price,
        MAX(pr.price) AS max_price
    FROM products p
    JOIN prices pr ON p.id = pr.product_id
    GROUP BY p.category
    ORDER BY avg_price DESC
""", connection)

# Запрос 2: статистика по поставщикам (исправлен JOIN)
df_suppliers = pd.read_sql("""
    SELECT 
        s.name AS supplier,
        COUNT(pr.price) AS product_count,
        ROUND(AVG(pr.price)::numeric, 2) AS avg_price
    FROM suppliers s
    JOIN products p ON s.product_id = p.id
    JOIN prices pr ON p.id = pr.product_id
    GROUP BY s.name
    ORDER BY product_count DESC
""", connection)

# Запрос 3: все цены для анализа распределения
df_prices = pd.read_sql("SELECT price FROM prices", connection)

# Запрос 4: продукты без цен (аномалии)
df_missing = pd.read_sql("""
    SELECT p.name AS product, p.category
    FROM products p
    LEFT JOIN prices pr ON p.id = pr.product_id
    WHERE pr.price IS NULL
    ORDER BY p.category, p.name
""", connection)

connection.close()
print("✅ Данные загружены, соединение закрыто\n")

# ============================================================================
# 3. РАСЧЁТ СТАТИСТИЧЕСКИХ МЕТРИК
# ============================================================================

print("📈 Статистические метрики:")
print("-" * 50)

mean_price = df_prices['price'].mean()
median_price = df_prices['price'].median()
std_price = df_prices['price'].std()
q1 = df_prices['price'].quantile(0.25)
q3 = df_prices['price'].quantile(0.75)

print(f"  • Средняя цена:                  {mean_price:,.2f} ₽")
print(f"  • Медиана цен:                   {median_price:,.2f} ₽")
print(f"  • Стандартное отклонение:        {std_price:,.2f} ₽")
print(f"  • Q1 (25%):                      {q1:,.2f} ₽")
print(f"  • Q3 (75%):                      {q3:,.2f} ₽")
print(f"  • Межквартильный размах (IQR):   {q3 - q1:,.2f} ₽")
print(f"  • Минимальная цена:              {df_prices['price'].min():,.2f} ₽")
print(f"  • Максимальная цена:             {df_prices['price'].max():,.2f} ₽")

overall_avg = df_categories['avg_price'].mean()
print(f"  • Средняя цена по категориям:    {overall_avg:,.2f} ₽")

total_products = df_categories['total_products'].sum()
print(f"  • Всего товаров с ценами:        {total_products}")
print(f"  • Товаров без цен (аномалия):    {len(df_missing)}")

print("\n")

# ============================================================================
# 4. ПОСТРОЕНИЕ ГРАФИКОВ
# ============================================================================

plt.rcParams['font.family'] = 'DejaVu Sans'
plt.rcParams['figure.dpi'] = 130

fig, axes = plt.subplots(2, 2, figsize=(14, 10))
fig.suptitle('📊 Анализ базы данных: товары, цены, поставщики', fontsize=14, fontweight='bold')

# ----- ГРАФИК 1: Средняя цена по категориям (горизонтальная) -----
categories_sorted = df_categories.sort_values('avg_price')
colors = plt.cm.RdYlGn(categories_sorted['avg_price'] / categories_sorted['avg_price'].max())

bars1 = axes[0, 0].barh(categories_sorted['category'], categories_sorted['avg_price'], 
                        color=colors, edgecolor='white', height=0.6)

for bar, val in zip(bars1, categories_sorted['avg_price']):
    axes[0, 0].text(bar.get_width() + 500, bar.get_y() + bar.get_height()/2,
                    f'{val:,.0f} ₽', va='center', fontsize=9, fontweight='bold')

axes[0, 0].axvline(overall_avg, color='blue', linestyle='--', linewidth=2, 
                   label=f'Среднее: {overall_avg:,.0f} ₽')
axes[0, 0].set_xlabel('Средняя цена (₽)', fontsize=11)
axes[0, 0].set_title('💰 Средняя цена по категориям', fontsize=13, fontweight='bold')
axes[0, 0].legend(loc='lower right')
axes[0, 0].grid(axis='x', alpha=0.3)

# ----- ГРАФИК 2: Поставщики -----
if len(df_suppliers) > 0:
    top_suppliers = df_suppliers.head(10)
    bars2 = axes[0, 1].bar(top_suppliers['supplier'], top_suppliers['product_count'],
                           color='#5cb85c', edgecolor='white', alpha=0.85, linewidth=1.5)

    for bar in bars2:
        axes[0, 1].text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.3,
                        str(int(bar.get_height())), ha='center', fontsize=9, fontweight='bold')

    axes[0, 1].set_ylabel('Количество товаров', fontsize=11)
    axes[0, 1].set_title('🏭 Топ поставщиков по количеству товаров', fontsize=13, fontweight='bold')
    axes[0, 1].set_xticklabels(top_suppliers['supplier'], rotation=45, ha='right', fontsize=8)
    axes[0, 1].grid(axis='y', alpha=0.3)
else:
    axes[0, 1].text(0.5, 0.5, 'Нет данных о поставщиках', ha='center', va='center', transform=axes[0, 1].transAxes)
    axes[0, 1].set_title('🏭 Поставщики', fontsize=13, fontweight='bold')

# ----- ГРАФИК 3: Распределение цен (гистограмма) -----
axes[1, 0].hist(df_prices['price'], bins=20, color='#f0ad4e', edgecolor='white', alpha=0.85, linewidth=1.5)

axes[1, 0].axvline(mean_price, color='blue', linestyle='-', linewidth=2, 
                   label=f'Среднее: {mean_price:,.0f} ₽')
axes[1, 0].axvline(median_price, color='red', linestyle='--', linewidth=2, 
                   label=f'Медиана: {median_price:,.0f} ₽')

stats_text = f'📐 Статистика:\nСреднее: {mean_price:,.0f} ₽\nМедиана: {median_price:,.0f} ₽\nСт. откл.: {std_price:,.0f} ₽\nQ1: {q1:,.0f} ₽\nQ3: {q3:,.0f} ₽'
axes[1, 0].text(0.95, 0.95, stats_text, transform=axes[1, 0].transAxes, fontsize=9,
                va='top', ha='right', bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.9))

axes[1, 0].set_xlabel('Цена (₽)', fontsize=11)
axes[1, 0].set_ylabel('Количество товаров', fontsize=11)
axes[1, 0].set_title('📊 Распределение цен на товары', fontsize=13, fontweight='bold')
axes[1, 0].legend(loc='upper left', fontsize=9)
axes[1, 0].grid(axis='y', alpha=0.3)

# ----- ГРАФИК 4: Доля товаров по категориям (круговая) -----
colors_pie = ['#ff6b6b', '#4ecdc4', '#45b7d1', '#96ceb4', '#ffeaa7', '#dfe6e9']
wedges, texts, autotexts = axes[1, 1].pie(df_categories['total_products'],
                                           labels=df_categories['category'],
                                           autopct='%1.1f%%',
                                           colors=colors_pie[:len(df_categories)],
                                           startangle=90,
                                           explode=(0.02,) * len(df_categories),
                                           shadow=True)

for autotext in autotexts:
    autotext.set_fontsize(10)
    autotext.set_fontweight('bold')

axes[1, 1].set_title('📦 Доля товаров по категориям', fontsize=13, fontweight='bold')

# ============================================================================
# 5. АНОМАЛИИ
# ============================================================================

iqr = q3 - q1
lower_bound = q1 - 1.5 * iqr
upper_bound = q3 + 1.5 * iqr
outliers = df_prices[(df_prices['price'] < lower_bound) | (df_prices['price'] > upper_bound)]

if len(df_missing) > 0 or len(outliers) > 0:
    anomaly_text = f"⚠ АНОМАЛИИ: {len(df_missing)} товаров без цен, {len(outliers)} цен-выбросов"
    fig.text(0.5, 0.01, anomaly_text, ha='center', fontsize=10, color='#8b0000',
             bbox=dict(boxstyle='round', facecolor='#ffe6e6', edgecolor='red'))
    
    if len(df_missing) > 0:
        print("\n⚠ Товары без цен (аномалия):")
        for _, row in df_missing.iterrows():
            print(f"   • {row['product']} (категория: {row['category']})")
    
    if len(outliers) > 0:
        print(f"\n⚠ Цены-выбросы (аномалия) — {len(outliers)} шт.:")
        print(f"   • Нижняя граница: {lower_bound:,.0f} ₽")
        print(f"   • Верхняя граница: {upper_bound:,.0f} ₽")
        print(f"   • Диапазон аномальных цен: {outliers['price'].min():,.0f} - {outliers['price'].max():,.0f} ₽")
else:
    anomaly_text = "✅ Аномалии не обнаружены"
    fig.text(0.5, 0.01, anomaly_text, ha='center', fontsize=11, color='#2ecc71',
             bbox=dict(boxstyle='round', facecolor='#e8f8f5', edgecolor='green'))

# ============================================================================
# 6. СОХРАНЕНИЕ
# ============================================================================

plt.tight_layout()
OUTPUT_FILE = "products_analysis.png"
plt.savefig(OUTPUT_FILE, bbox_inches='tight', dpi=150)
print(f"\n✅ График сохранён: {OUTPUT_FILE}")

plt.show()

# ============================================================================
# 7. ВЫВОДЫ
# ============================================================================

print("\n" + "=" * 70)
print("📝 ВЫВОДЫ ПО КАЖДОМУ ГРАФИКУ")
print("=" * 70)

print("\n📊 ГРАФИК 1 (Средняя цена по категориям):")
print(f"   → Самая дорогая категория: {df_categories.loc[df_categories['avg_price'].idxmax(), 'category']} "
      f"({df_categories['avg_price'].max():,.0f} ₽)")
print(f"   → Самая дешёвая категория: {df_categories.loc[df_categories['avg_price'].idxmin(), 'category']} "
      f"({df_categories['avg_price'].min():,.0f} ₽)")

if len(df_suppliers) > 0:
    print("\n📊 ГРАФИК 2 (Поставщики):")
    print(f"   → Поставщик с наибольшим количеством товаров: {df_suppliers.iloc[0]['supplier']} "
          f"({df_suppliers.iloc[0]['product_count']} товаров)")

print("\n📊 ГРАФИК 3 (Распределение цен):")
print(f"   → Средняя цена: {mean_price:,.0f} ₽, Медиана: {median_price:,.0f} ₽")
print(f"   → Стандартное отклонение: {std_price:,.0f} ₽ (разброс цен значительный)")

print("\n📊 ГРАФИК 4 (Доля товаров по категориям):")
print("   → Распределение товаров по категориям показывает ассортиментную структуру")
for _, row in df_categories.iterrows():
    print(f"   → {row['category']}: {row['total_products']} товаров")

print("\n" + "=" * 70)
print("✅ АНАЛИЗ ЗАВЕРШЁН")
print("=" * 70)