import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
import streamlit as st

# Konfigurasi halaman Streamlit
st.set_page_config(
    page_title="Dashboard Analisis E-Commerce Olist", layout="wide"
)


# Load data utama dengan penanganan format .gz atau .csv secara otomatis
@st.cache_data
def load_data():
  try:
    # Mencoba membaca file .gz terlebih dahulu
    df = pd.read_csv("main_data.gz", compression="gzip")
  except FileNotFoundError:
    try:
      # Fallback jika penilai menggunakan nama .csv
      df = pd.read_csv("main_data.csv")
    except FileNotFoundError:
      st.error(
          "File dataset (`main_data.gz` atau `main_data.csv`) tidak ditemukan di"
          " folder dashboard!"
      )
      return pd.DataFrame()

  # Konversi kolom tanggal
  date_columns = [
      "order_purchase_timestamp",
      "order_delivered_customer_date",
      "order_estimated_delivery_date",
  ]
  for col in date_columns:
    if col in df.columns:
      df[col] = pd.to_datetime(df[col], errors="coerce")

  return df


df_main = load_data()

# Judul Dashboard
st.title("Dashboard Analisis E-Commerce Olist")
st.markdown(
    "Visualisasi data berdasarkan pertanyaan bisnis analisis performa "
    "penjualan dan logistik."
)

if df_main.empty:
  st.stop()

# --- SIDEBAR & FILTER ---
st.sidebar.header("Navigasi & Filter")
analysis_choice = st.sidebar.selectbox(
    "Pilih Analisis:",
    [
        "Top 5 Kategori & Metode Pembayaran (Sao Paulo)",
        "Analisis Keterlambatan & Ulasan Buruk (Non-RJ)",
    ],
)

# Jika ingin menambahkan filter rentang waktu global yang aman:
st.sidebar.markdown("---")
st.sidebar.subheader("Filter Tambahan")
min_date = df_main["order_purchase_timestamp"].min().date()
max_date = df_main["order_purchase_timestamp"].max().date()

# Menggunakan rentang waktu default sesuai data keseluruhan
date_range = st.sidebar.date_input(
    "Rentang Waktu", value=(min_date, max_date), min_value=min_date, max_value=max_date
)

# Filter dataframe berdasarkan rentang waktu sidebar (jika dipilih 2 tanggal)
if len(date_range) == 2:
  start_date, end_date = date_range
  df_filtered = df_main[
      (df_main["order_purchase_timestamp"].dt.date >= start_date)
      & (df_main["order_purchase_timestamp"].dt.date <= end_date)
  ]
else:
  df_filtered = df_main.copy()


# --- ANALISIS 1 ---
if analysis_choice == "Top 5 Kategori & Metode Pembayaran (Sao Paulo)":
  st.subheader("Metode Pembayaran pada 5 Kategori Produk Teratas (Sao Paulo)")

  required_q1 = [
      "customer_city",
      "product_category_name",
      "price",
      "payment_type",
      "order_id",
  ]
  missing_q1 = [col for col in required_q1 if col not in df_filtered.columns]

  if missing_q1:
    st.error(f"Kolom berikut tidak ditemukan di dataset: {missing_q1}")
  else:
    df_sp = df_filtered[
        df_filtered["customer_city"].str.lower() == "sao paulo"
    ].copy()

    if df_sp.empty:
      st.warning(
          "Tidak ada data untuk kota Sao Paulo pada rentang waktu yang dipilih."
      )
    else:
      top_5_cat = (
          df_sp.groupby("product_category_name")["price"]
          .sum()
          .reset_index()
          .sort_values(by="price", ascending=False)
          .head(5)
      )

      top_cat_list = top_5_cat["product_category_name"].tolist()
      df_top5_sp = df_sp[df_sp["product_category_name"].isin(top_cat_list)]

      payment_dominance = (
          df_top5_sp.groupby(["product_category_name", "payment_type"])["order_id"]
          .count()
          .reset_index(name="transaction_count")
      )

      fig, ax = plt.subplots(figsize=(10, 6))
      sns.barplot(
          data=payment_dominance,
          x="product_category_name",
          y="transaction_count",
          hue="payment_type",
          ax=ax,
      )
      plt.xticks(rotation=45, ha="right")
      plt.xlabel("Kategori Produk")
      plt.ylabel("Jumlah Transaksi")
      plt.title("Dominasi Metode Pembayaran pada Top 5 Kategori di Sao Paulo")
      st.pyplot(fig)


# --- ANALISIS 2 ---
elif analysis_choice == "Analisis Keterlambatan & Ulasan Buruk (Non-RJ)":
  st.subheader("Rata-rata Keterlambatan Pengiriman & Ulasan Buruk (Seller Non-RJ)")

  required_columns = [
      "order_purchase_timestamp",
      "order_delivered_customer_date",
      "order_estimated_delivery_date",
      "review_score",
      "seller_state",
  ]
  missing_cols = [col for col in required_columns if col not in df_main.columns]

  if missing_cols:
    st.error(
        f"Kolom berikut tidak ditemukan di dalam dataset: {missing_cols}. "
        "Pastikan tabel sellers dan reviews sudah digabungkan."
    )
  else:
    # CATATAN: Untuk pertanyaan bisnis Q3 2017, kita gunakan rentang waktu tetap (hardcode)
    # agar tidak terganggu oleh perubahan rentang waktu di sidebar.
    q3_start = "2017-07-01"
    q3_end = "2017-09-30"

    df_q3_2017 = df_main[
        (df_main["order_purchase_timestamp"] >= q3_start)
        & (df_main["order_purchase_timestamp"] <= q3_end)
    ].copy()

    if df_q3_2017.empty:
      st.warning("Tidak ada data transaksi pada rentang waktu Q3 2017.")
    else:
      # Hitung hari keterlambatan
      df_q3_2017.loc[:, "delivery_delay_days"] = (
          df_q3_2017["order_delivered_customer_date"]
          - df_q3_2017["order_estimated_delivery_date"]
      ).dt.days

      # Filter seller state selain RJ
      df_non_rj = df_q3_2017[df_q3_2017["seller_state"].str.upper() != "RJ"]

      bad_reviews_delayed = df_non_rj[
          (df_non_rj["review_score"] == 1) & (df_non_rj["delivery_delay_days"] > 0)
      ]

      total_reviews_outside = len(df_non_rj)
      total_score1_delayed = len(bad_reviews_delayed)
      percentage_score1 = (
          (total_score1_delayed / total_reviews_outside) * 100
          if total_reviews_outside > 0
          else 0
      )
      mean_delay_days = (
          bad_reviews_delayed["delivery_delay_days"].mean()
          if not bad_reviews_delayed.empty
          else 0
      )

      # Tampilkan Metric Cards
      col1, col2 = st.columns(2)
      with col1:
        st.metric(
            label="Persentase Ulasan Buruk (Score 1) karena Terlambat",
            value=f"{percentage_score1:.2f}%",
        )
      with col2:
        st.metric(
            label="Rata-rata Selisih Keterlambatan",
            value=f"{mean_delay_days:.2f} Hari",
        )

      # Visualisasi
      fig, ax = plt.subplots(figsize=(8, 4))
      sns.histplot(
          bad_reviews_delayed["delivery_delay_days"].dropna(),
          bins=30,
          kde=True,
          color="red",
          ax=ax,
      )
      plt.xlabel("Hari Keterlambatan")
      plt.ylabel("Frekuensi Ulasan Skor 1")
      plt.title(
          "Distribusi Waktu Keterlambatan Pengiriman dengan Ulasan Buruk"
          " (Q3 2017, Non-RJ)"
      )
      st.pyplot(fig)
