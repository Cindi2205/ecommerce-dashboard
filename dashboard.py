import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

sns.set(style='dark')

# 1. Helper Functions untuk Menyiapkan Dataframe Dashboard

def create_top_categories_df(df):
    df_q1_sp = df[df['customer_city'].str.lower() == 'sao paulo']
    top_5_categories = df_q1_sp.groupby('product_category_name')['price'].sum().reset_index() \
        .sort_values(by='price', ascending=False).head(5)
    
    top_categories_list = top_5_categories['product_category_name'].tolist()
    df_top5_sp = df_q1_sp[df_q1_sp['product_category_name'].isin(top_categories_list)]
    
    payment_dominance = df_top5_sp.groupby(['product_category_name', 'payment_type'])['order_id'].count().reset_index(name='transaction_count')
    return payment_dominance

def create_delivery_delay_df(df):
    # Memastikan kolom datetime
    df['order_delivered_customer_date'] = pd.to_datetime(df['order_delivered_customer_date'])
    df['order_estimated_delivery_date'] = pd.to_datetime(df['order_estimated_delivery_date'])
    
    df_q2_merged = df.merge(pd.read_csv("data/order_items_dataset.csv"), on='order_id', how='inner') \
        .merge(pd.read_csv("data/sellers_dataset.csv"), on='seller_id', how='inner') \
        .merge(pd.read_csv("data/order_reviews_dataset.csv"), on='order_id', how='inner')

    df_outside_rj = df_q2_merged[df_q2_merged['seller_state'].str.upper() != 'RJ'].copy()
    df_outside_rj.loc[:, 'delivery_delay_days'] = (df_outside_rj['order_delivered_customer_date'] - df_outside_rj['order_estimated_delivery_date']).dt.days

    bad_reviews_delayed = df_outside_rj[(df_outside_rj['review_score'] == 1) & (df_outside_rj['delivery_delay_days'] > 0)]
    return bad_reviews_delayed

# 2. Load Cleaned Data (main_data.csv)
all_df = pd.read_csv("main_data.csv")

# Konversi kolom tanggal jika ada
datetime_columns = ["order_purchase_timestamp", "order_delivered_customer_date", "order_estimated_delivery_date"]
for col in datetime_columns:
    if col in all_df.columns:
        all_df[col] = pd.to_datetime(all_df[col])

# 3. Sidebar (Filter Rentang Waktu)
with st.sidebar:
    st.subheader("Filter Dashboard Olist")
    
    # Mengambil rentang tanggal jika kolom tersedia
    if "order_purchase_timestamp" in all_df.columns:
        min_date = all_df["order_purchase_timestamp"].min().date()
        max_date = all_df["order_purchase_timestamp"].max().date()
        
        start_date, end_date = st.date_input(
            label='Rentang Waktu',
            min_value=min_date,
            max_value=max_date,
            value=[min_date, max_date]
        )
        
        main_df = all_df[(all_df["order_purchase_timestamp"].dt.date >= start_date) & 
                         (all_df["order_purchase_timestamp"].dt.date <= end_date)]
    else:
        main_df = all_df

# 4. Tampilan Utama Dashboard
st.header('📊 Dashboard Analisis E-Commerce Olist')

# --- PERTANYAAN BISNIS 1 ---
st.subheader('1. Kategori Produk Teratas & Metode Pembayaran di São Paulo')

# Menyiapkan dataframe untuk pertanyaan 1
try:
    payment_dominance_df = create_top_categories_df(main_df)
    
    fig, ax = plt.subplots(figsize=(12, 6))
    sns.barplot(
        x="product_category_name", 
        y="transaction_count", 
        hue="payment_type", 
        data=payment_dominance_df, 
        palette="Blues",
        ax=ax
    )
    ax.set_title("Metode Pembayaran pada 5 Kategori Produk Teratas di São Paulo", fontsize=16)
    ax.set_xlabel("Kategori Produk", fontsize=12)
    ax.set_ylabel("Jumlah Transaksi", fontsize=12)
    plt.xticks(rotation=45)
    st.pyplot(fig)
except Exception as e:
    st.error(f"Gagal memuat visualisasi 1: {e}")

# --- PERTANYAAN BISNIS 2 ---
st.subheader('2. Distribusi Keterlambatan Pengiriman terhadap Ulasan Buruk (Score 1) di Luar Rio de Janeiro')

try:
    bad_reviews_df = create_delivery_delay_df(main_df)
    
    fig, ax = plt.subplots(figsize=(12, 6))
    sns.histplot(
        bad_reviews_df['delivery_delay_days'], 
        bins=30, 
        kde=True, 
        color="#ff6b6b", 
        ax=ax
    )
    ax.set_title("Distribusi Hari Keterlambatan untuk Ulasan Score 1 (Diluar RJ)", fontsize=16)
    ax.set_xlabel("Hari Keterlambatan (Hari)", fontsize=12)
    ax.set_ylabel("Frekuensi", fontsize=12)
    st.pyplot(fig)
    
    # Metrik Pendukung
    col1, col2 = st.columns(2)
    with col1:
        total_bad_delayed = len(bad_reviews_df)
        st.metric("Total Ulasan Buruk Karena Terlambat", value=total_bad_delayed)
    with col2:
        mean_delay = round(bad_reviews_df['delivery_delay_days'].mean(), 1) if not bad_reviews_df.empty else 0
        st.metric("Rata-rata Keterlambatan (Hari)", value=mean_delay)

except Exception as e:
    st.error(f"Gagal memuat visualisasi 2: {e}")
