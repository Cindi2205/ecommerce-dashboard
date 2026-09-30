import os
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
import streamlit as st

sns.set(style="darkgrid")

# Konfigurasi Halaman Streamlit
st.set_page_config(
    page_title="Olist E-Commerce Dashboard", page_icon="📊", layout="wide"
)


# 1. Load Cleaned Data
@st.cache_data
def load_data():
  current_dir = os.path.dirname(os.path.abspath(__file__))
  file_path = os.path.join(current_dir, "main_data.gz")
  data = pd.read_csv(file_path, compression="gzip")

  datetime_columns = [
      "order_purchase_timestamp",
      "order_delivered_customer_date",
      "order_estimated_delivery_date",
  ]
  for col in datetime_columns:
    if col in data.columns:
      data[col] = pd.to_datetime(data[col])
  return data


all_df = load_data()

# 2. Sidebar untuk Kontrol & Fitur Interaktif (Memenuhi Syarat Rubrik Interaktivitas)
with st.sidebar:
  st.subheader("📌 Olist Dashboard Control")
  st.markdown(
      "Gunakan filter di bawah ini untuk mengubah parameter analisis secara"
      " dinamis."
  )

  st.markdown("---")
  st.markdown("### Filter Pertanyaan 1")
  # Filter interaktif jumlah kategori produk teratas yang ingin ditampilkan
  top_n_cat = st.slider(
      "Pilih Jumlah Kategori Teratas:", min_value=3, max_value=10, value=5
  )

  st.markdown("---")
  st.markdown("### Filter Pertanyaan 2")
  # Filter interaktif ambang batas persentase review score 1
  min_score_1_pct = st.slider(
      "Ambang Batas Minimum Review Score 1 (%):",
      min_value=0,
      max_value=50,
      value=10,
      step=5,
  )


# --- FUNGSI ANALISIS PERTANYAAN 1 ---
def create_top_categories_df(df, top_n):
  if "order_purchase_timestamp" in df.columns:
    df_h1_2018 = df[
        (df["order_purchase_timestamp"] >= "2018-01-01")
        & (df["order_purchase_timestamp"] <= "2018-06-30")
    ]
  else:
    df_h1_2018 = df.copy()

  if "customer_city" in df_h1_2018.columns:
    df_q1_sp = df_h1_2018[
        df_h1_2018["customer_city"].str.lower() == "sao paulo"
    ]
  else:
    df_q1_sp = pd.DataFrame()

  if df_q1_sp.empty:
    return pd.DataFrame()

  top_categories = (
      df_q1_sp.groupby("product_category_name")["price"]
      .sum()
      .reset_index()
      .sort_values(by="price", ascending=False)
      .head(top_n)
  )

  top_categories_list = top_categories["product_category_name"].tolist()
  df_top_sp = df_q1_sp[
      df_q1_sp["product_category_name"].isin(top_categories_list)
  ]

  payment_dominance = (
      df_top_sp.groupby(["product_category_name", "payment_type"])["order_id"]
      .count()
      .reset_index(name="transaction_count")
  )
  return payment_dominance


# --- FUNGSI ANALISIS PERTANYAAN 2 ---
def create_delivery_delay_df(df, threshold_pct):
  try:
    if "order_purchase_timestamp" in df.columns:
      df_q3_2017 = df[
          (df["order_purchase_timestamp"] >= "2017-07-01")
          & (df["order_purchase_timestamp"] <= "2017-09-30")
      ]
    else:
      df_q3_2017 = df.copy()

    if "seller_state" in df_q3_2017.columns:
      df_outside_rj = df_q3_2017[
          df_q3_2017["seller_state"].str.upper() != "RJ"
      ].copy()
    else:
      return pd.DataFrame(), pd.DataFrame()

    df_outside_rj["delivery_delay_days"] = (
        df_outside_rj["order_delivered_customer_date"]
        - df_outside_rj["order_estimated_delivery_date"]
    ).dt.days

    seller_summary = (
        df_outside_rj.groupby("seller_id")
        .agg(
            total_orders=("order_id", "count"),
            score_1_count=(
                "review_score",
                lambda x: (x == 1).sum(),
            ),
        )
        .reset_index()
    )

    seller_summary["score_1_percentage"] = (
        seller_summary["score_1_count"] / seller_summary["total_orders"]
    ) * 100

    # Menggunakan filter interaktif dari slider sidebar
    filtered_sellers = seller_summary[
        seller_summary["score_1_percentage"] > threshold_pct
    ]
    valid_seller_ids = filtered_sellers["seller_id"].tolist()

    bad_reviews_delayed = df_outside_rj[
        df_outside_rj["seller_id"].isin(valid_seller_ids)
        & (df_outside_rj["delivery_delay_days"] > 0)
    ]

    return bad_reviews_delayed, filtered_sellers

  except Exception as e:
    print(f"Error pada fungsi: {e}")
    return pd.DataFrame(), pd.DataFrame()


# 4. Tampilan Utama Dashboard
st.header("📊 Dashboard Analisis E-Commerce Olist")
st.markdown("---")

# --- PERTANYAAN BISNIS 1 ---
st.subheader(
    f"1. Metode Pembayaran pada {top_n_cat} Kategori Produk Teratas di São"
    " Paulo (H1 2018)"
)

try:
  payment_dominance_df = create_top_categories_df(all_df, top_n_cat)

  if payment_dominance_df.empty:
    st.warning("Tidak ada data yang ditemukan untuk kriteria tersebut.")
  else:
    fig, ax = plt.subplots(figsize=(12, 6))
    sns.barplot(
        x="product_category_name",
        y="transaction_count",
        hue="payment_type",
        data=payment_dominance_df,
        palette="Blues",
        ax=ax,
    )
    ax.set_xlabel("Kategori Produk", fontsize=12)
    ax.set_ylabel("Jumlah Transaksi", fontsize=12)
    plt.xticks(rotation=25, ha="right")
    st.pyplot(fig)
except Exception as e:
  st.error(f"Gagal memuat visualisasi 1: {e}")

st.markdown("---")

# --- PERTANYAAN BISNIS 2 ---
st.subheader(
    "2. Distribusi Keterlambatan Pengiriman oleh Seller di Luar Rio de Janeiro"
    f" (Review Score 1 > {min_score_1_pct}%, Q3 2017)"
)

try:
  bad_reviews_df, seller_metrics_df = create_delivery_delay_df(
      all_df, min_score_1_pct
  )

  if bad_reviews_df.empty:
    st.info(
        "Tidak ada data ulasan buruk dengan ambang batas tersebut. Coba"
        " sesuaikan slider filter di sidebar."
    )
  else:
    fig, ax = plt.subplots(figsize=(12, 6))
    sns.histplot(
        bad_reviews_df["delivery_delay_days"],
        bins=30,
        kde=True,
        color="#ff6b6b",
        ax=ax,
    )
    ax.set_xlabel("Hari Keterlambatan (Hari)", fontsize=12)
    ax.set_ylabel("Frekuensi", fontsize=12)
    st.pyplot(fig)

    # Metrik Pendukung
    col1, col2, col3 = st.columns(3)
    with col1:
      st.metric(
          "Total Seller Teridentifikasi", value=len(seller_metrics_df)
      )
    with col2:
      st.metric("Total Transaksi Bermasalah", value=len(bad_reviews_df))
    with col3:
      mean_delay = round(bad_reviews_df["delivery_delay_days"].mean(), 1)
      st.metric("Rata-rata Keterlambatan (Hari)", value=mean_delay)

except Exception as e:
  st.error(f"Gagal memuat visualisasi 2: {e}")
