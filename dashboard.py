import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
import streamlit as st

# Load data utama yang sudah disimpan dari notebook
@st.cache_data
def load_data():
  # Pastikan file main_data.csv berada di folder yang sama dengan dashboard.py
  df = pd.read_csv('main_data.gz', compression='gzip')

  # Konversi kolom tanggal jika diperlukan
  df['order_purchase_timestamp'] = pd.to_datetime(
      df['order_purchase_timestamp']
  )
  df['order_delivered_customer_date'] = pd.to_datetime(
      df['order_delivered_customer_date']
  )
  df['order_estimated_delivery_date'] = pd.to_datetime(
      df['order_estimated_delivery_date']
  )
  return df


df_main = load_data()

# Judul Dashboard
st.title('Dashboard Analisis E-Commerce Olist')
st.markdown(
    'Visualisasi data berdasarkan pertanyaan bisnis analisis performa'
    ' penjualan dan logistik.'
)

# Sidebar untuk navigasi atau informasi
st.sidebar.header('Navigasi & Filter')
analysis_choice = st.sidebar.selectbox(
    'Pilih Analisis:',
    [
        'Top 5 Kategori & Metode Pembayaran (Sao Paulo)',
        'Analisis Keterlambatan & Ulasan Buruk (Non-RJ)',
    ],
)

if analysis_choice == 'Top 5 Kategori & Metode Pembayaran (Sao Paulo)':
  st.subheader(
      'Metode Pembayaran pada 5 Kategori Produk Teratas (Sao Paulo)'
  )

  # Filter data sesuai dengan logic di notebook Anda
  df_sp = df_main[df_main['customer_city'].str.lower() == 'sao paulo']

  # Ambil Top 5 Kategori berdasarkan Total Price
  top_5_cat = (
      df_sp.groupby('product_category_name')['price']
      .sum()
      .reset_index()
      .sort_values(by='price', ascending=False)
      .head(5)
  )

  top_cat_list = top_5_cat['product_category_name'].tolist()
  df_top5_sp = df_sp[df_sp['product_category_name'].isin(top_cat_list)]

  # Agregasi untuk visualisasi pembayaran
  payment_dominance = (
      df_top5_sp.groupby(['product_category_name', 'payment_type'])['order_id']
      .count()
      .reset_index(name='transaction_count')
  )

  # Visualisasi menggunakan Seaborn / Matplotlib di Streamlit
  fig, ax = plt.subplots(figsize=(10, 6))
  sns.barplot(
      data=payment_dominance,
      x='product_category_name',
      y='transaction_count',
      hue='payment_type',
      ax=ax,
  )
  plt.xticks(rotation=45, ha='right')
  plt.xlabel('Kategori Produk')
  plt.ylabel('Jumlah Transaksi')
  plt.title('Dominasi Metode Pembayaran pada Top 5 Kategori di Sao Paulo')
  st.pyplot(fig)

elif analysis_choice == 'Analisis Keterlambatan & Ulasan Buruk (Non-RJ)':
  st.subheader('Rata-rata Keterlambatan Pengiriman & Ulasan Buruk (Seller Non-RJ)')

  # Hitung ulang / filter berdasarkan kriteria di notebook
  df_main['delivery_delay_days'] = (
      df_main['order_delivered_customer_date']
      - df_main['order_estimated_delivery_date']
  ).dt.days

  # Filter seller state selain RJ
  if 'seller_state' in df_main.columns:
    df_non_rj = df_main[df_main['seller_state'].str.upper() != 'RJ']
  else:
    df_non_rj = df_main  # Fallback jika kolom belum merge sempurna di main_data

  bad_reviews_delayed = df_non_rj[
      (df_non_rj['review_score'] == 1) & (df_non_rj['delivery_delay_days'] > 0)
  ]

  total_reviews_outside = len(df_non_rj)
  total_score1_delayed = len(bad_reviews_delayed)
  percentage_score1 = (
      (total_score1_delayed / total_reviews_outside) * 100
      if total_reviews_outside > 0
      else 0
  )
  mean_delay_days = bad_reviews_delayed['delivery_delay_days'].mean()

  # Tampilkan Metric Cards di Streamlit
  col1, col2 = st.columns(2)
  with col1:
    st.metric(
        label='Persentase Ulasan Buruk (Score 1) karena Terlambat',
        value=f'{percentage_score1:.2f}%',
    )
  with col2:
    st.metric(
        label='Rata-rata Selisih Keterlambatan',
        value=f'{mean_delay_days:.2f} Hari',
    )

  # Visualisasi tambahan distribusi hari keterlambatan
  fig, ax = plt.subplots(figsize=(8, 4))
  sns.histplot(
      bad_reviews_delayed['delivery_delay_days'].dropna(),
      bins=30,
      kde=True,
      color='red',
      ax=ax,
  )
  plt.xlabel('Hari Keterlambatan')
  plt.ylabel('Frekuensi Ulasan Skor 1')
  plt.title(
      'Distribusi Waktu Keterlambatan Pengiriman dengan Ulasan Buruk (Non-RJ)'
  )
  st.pyplot(fig)
