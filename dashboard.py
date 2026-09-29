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
    try:
        # Membaca data mentah dari direktori utama
        orders_df = pd.read_csv("orders_dataset.csv")
        order_items_df = pd.read_csv("order_items_dataset.csv")
        sellers_df = pd.read_csv("sellers_dataset.csv")
        order_reviews_df = pd.read_csv("order_reviews_dataset.csv")
        
        # Menggabungkan dataframe yang dibutuhkan
        df_q2_merged = orders_df.merge(order_items_df, on='order_id', how='inner') \
            .merge(sellers_df, on='seller_id', how='inner') \
            .merge(order_reviews_df, on='order_id', how='inner')
        
        # Memastikan kolom datetime dikonversi
        df_q2_merged['order_delivered_customer_date'] = pd.to_datetime(df_q2_merged['order_delivered_customer_date'])
        df_q2_merged['order_estimated_delivery_date'] = pd.to_datetime(df_q2_merged['order_estimated_delivery_date'])
        
        # Filter seller di luar Rio de Janeiro (RJ)
        df_outside_rj = df_q2_merged[df_q2_merged['seller_state'].str.upper() != 'RJ'].copy()
        
        # Menghitung selisih hari keterlambatan
        df_outside_rj['delivery_delay_days'] = (df_outside_rj['order_delivered_customer_date'] - df_outside_rj['order_estimated_delivery_date']).dt.days

        # Filter ulasan buruk (score 1) dan yang benar-benar terlambat (> 0 hari)
        bad_reviews_delayed = df_outside_rj[(df_outside_rj['review_score'] == 1) & (df_outside_rj['delivery_delay_days'] > 0)]
        
        return bad_reviews_delayed
        
    except Exception as e:
        # Jika ada file yang belum ter-upload atau error, kembalikan dataframe kosong agar tidak crash
        print(f"Error pada fungsi: {e}")
        return pd.DataFrame()

# 2. Load Cleaned Data (main_data.csv)
@st.cache_data
def load_data():
    data = pd.read_csv("main_data.csv")
    datetime_columns = ["order_purchase_timestamp", "order_delivered_customer_date", "order_estimated_delivery_date"]
    for col in datetime_columns:
        if col in data.columns:
            data[col] = pd.to_datetime(data[col])
    return data

all_df = load_data()

# 3. Sidebar (Filter Rentang Waktu)
with st.sidebar:
    st.subheader("Filter Dashboard Olist")
    
    if "order_purchase_timestamp" in all_df.columns:
    min_date = all_df["order_purchase_timestamp"].min()
    max_date = all_df["order_purchase_timestamp"].max()

    start_date, end_date = st.sidebar.date_input(
        label="Rentang Waktu",
        min_value=min_date, 
        max_value=max_date,
        value=[min_date, max_date]
    )
        
        main_df = all_df[(all_df["order_purchase_timestamp"].dt.date >= start_date) & 
                         (all_df["order_purchase_timestamp"].dt.date <= end_date)]
    else:
        main_df = all_df

# 4. Tampilan Utama Dashboard
st.header('Dashboard Analisis E-Commerce Olist')

# --- PERTANYAAN BISNIS 1 ---
st.subheader('1. Kategori Produk Teratas & Metode Pembayaran di São Paulo')

try:
    payment_dominance_df = create_top_categories_df(main_df)
    
    if payment_dominance_df.empty:
        st.warning("Tidak ada data yang ditemukan untuk filter ini.")
    else:
        fig, ax = plt.subplots(figsize=(12, 6))
        sns.barplot(
            x="product_category_name", 
            y="transaction_count", 
            hue="payment_type", 
            data=payment_dominance_df, 
            palette="Blues",
            ax=ax
        )
        ax.set_title("Metode Pembayaran pada 5 Kategori Produk Teratas di São Paulo", fontsize=14, fontweight='bold')
        ax.set_xlabel("Kategori Produk", fontsize=12)
        ax.set_ylabel("Jumlah Transaksi", fontsize=12)
        plt.xticks(rotation=25, ha='right')
        st.pyplot(fig)
except Exception as e:
    st.error(f"Gagal memuat visualisasi 1: {e}")

# --- PERTANYAAN BISNIS 2 ---
st.subheader('2. Distribusi Keterlambatan Pengiriman terhadap Ulasan Buruk (Score 1) di Luar Rio de Janeiro')

try:
    bad_reviews_df = create_delivery_delay_df(main_df)
    
    if bad_reviews_df.empty:
        st.info("Tidak ada data ulasan buruk karena keterlambatan pada rentang waktu/filter ini.")
    else:
        fig, ax = plt.subplots(figsize=(12, 6))
        sns.histplot(
            bad_reviews_df['delivery_delay_days'], 
            bins=30, 
            kde=True, 
            color="#ff6b6b", 
            ax=ax
        )
        ax.set_title("Distribusi Hari Keterlambatan untuk Ulasan Score 1 (Diluar RJ)", fontsize=14, fontweight='bold')
        ax.set_xlabel("Hari Keterlambatan (Hari)", fontsize=12)
        ax.set_ylabel("Frekuensi", fontsize=12)
        st.pyplot(fig)
        
        # Metrik Pendukung
        col1, col2 = st.columns(2)
        with col1:
            total_bad_delayed = len(bad_reviews_df)
            st.metric("Total Ulasan Buruk Karena Terlambat", value=total_bad_delayed)
        with col2:
            mean_delay = round(bad_reviews_df['delivery_delay_days'].mean(), 1)
            st.metric("Rata-rata Keterlambatan (Hari)", value=mean_delay)

except Exception as e:
    st.error(f"Gagal memuat visualisasi 2: {e}")
