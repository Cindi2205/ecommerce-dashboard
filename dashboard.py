import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
import streamlit as st

sns.set(style="darkgrid")

# 1. Load Cleaned Data (main_data.csv)
@st.cache_data
def load_data():
  data = pd.read_csv("main_data.csv")
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


# 2. Helper Functions untuk Menyiapkan Dataframe Dashboard (Mandiri & Sesuai Periode Soal)
def create_top_categories_df(df):
  # Filter spesifik H1 2018 (Januari - Juni 2018)
  if "order_purchase_timestamp" in df.columns:
    df_h1_2018 = df[
        (df["order_purchase_timestamp"] >= "2018-01-01")
        & (df["order_purchase_timestamp"] <= "2018-06-30")
    ]
  else:
    df_h1_2018 = df.copy()

  # Filter kota São Paulo
  if "customer_city" in df_h1_2018.columns:
    df_q1_sp = df_h1_2018[
        df_h1_2018["customer_city"].str.lower() == "sao paulo"
    ]
  else:
    df_q1_sp = pd.DataFrame()

  if df_q1_sp.empty:
    return pd.DataFrame()

  top_5_categories = (
      df_q1_sp.groupby("product_category_name")["price"]
      .sum()
      .reset_index()
      .sort_values(by="price", ascending=False)
      .head(5)
  )

  top_categories_list = top_5_categories["product_category_name"].tolist()
  df_top5_sp = df_q1_sp[
      df_q1_sp["product_category_name"].isin(top_categories_list)
  ]

  payment_dominance = (
      df_top5_sp.groupby(["product_category_name", "payment_type"])["order_id"]
      .count()
      .reset_index(name="transaction_count")
  )
  return payment_dominance


def create_delivery_delay_df(df):
  try:
    # Filter spesifik Q3 2017 (Juli - September 2017)
    if "order_purchase_timestamp" in df.columns:
      df_q3_2017 = df[
          (df["order_purchase_timestamp"] >= "2017-07-01")
          & (df["order_purchase_timestamp"] <= "2017-09-30")
      ]
    else:
      df_q3_2017 = df.copy()

    # Filter seller di luar Rio de Janeiro (!= 'RJ')
    if "seller_state" in df_q3_2017.columns:
      df_outside_rj = df_q3_2017[
          df_q3_2017["seller_state"].str.upper() != "RJ"
      ].copy()
    else:
      return pd.DataFrame(), pd.DataFrame()

    # Hitung selisih hari keterlambatan pengiriman
    df_outside_rj["delivery_delay_days"] = (
        df_outside_rj["order_delivered_customer_date"]
        - df_outside_rj["order_estimated_delivery_date"]
    ).dt.days

    # Agregasi per-seller untuk menghitung proporsi review score 1 secara akurat
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

    # Filter seller dengan proporsi review score 1 > 20%
    filtered_sellers = seller_summary[
        seller_summary["score_1_percentage"] > 20
    ]
    valid_seller_ids = filtered_sellers["seller_id"].tolist()

    # Filter transaksi akhir berdasarkan seller valid dan benar-benar terlambat (> 0 hari)
    bad_reviews_delayed = df_outside_rj[
        df_outside_rj["seller_id"].isin(valid_seller_ids)
        & (df_outside_rj["delivery_delay_days"] > 0)
    ]

    return bad_reviews_delayed, filtered_sellers

  except Exception as e:
    print(f"Error pada fungsi: {e}")
    return pd.DataFrame(), pd.DataFrame()


# 3. Sidebar (Informasi / Kontrol Umum)
with st.sidebar:
  st.subheader("📌 Olist Dashboard Control")
  st.markdown(
      "Dashboard ini menampilkan analisis berdasarkan kriteria bisnis spesifik"
      " (H1 2018 & Q3 2017)."
  )
  st.info("Periode waktu dikunci otomatis sesuai instruksi pertanyaan.")

# 4. Tampilan Utama Dashboard
st.header("📊 Dashboard Analisis E-Commerce Olist")
st.markdown("---")

# --- PERTANYAAN BISNIS 1 ---
st.subheader("1. Kategori Produk Teratas & Metode Pembayaran di São Paulo")

try:
  payment_dominance_df = create_top_categories_df(all_df)

  if payment_dominance_df.empty:
    st.warning("Tidak ada data yang ditemukan untuk kriteria São Paulo H1 2018.")
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
    ax.set_title(
        "Metode Pembayaran pada 5 Kategori Produk Teratas di São Paulo (H1"
        " 2018)",
        fontsize=14,
        fontweight="bold",
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
    "2. Distribusi Keterlambatan Pengiriman terhadap Ulasan Buruk (Score 1 >"
    " 20%) di Luar Rio de Janeiro"
)

try:
  bad_reviews_df, seller_metrics_df = create_delivery_delay_df(all_df)

  if bad_reviews_df.empty:
    st.info(
        "Tidak ada data ulasan buruk karena keterlambatan pada filter seller"
        " luar RJ di Q3 2017."
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
    ax.set_title(
        "Distribusi Hari Keterlambatan untuk Ulasan Score 1 (Diluar RJ, Q3"
        " 2017)",
        fontsize=14,
        fontweight="bold",
    )
    ax.set_xlabel("Hari Keterlambatan (Hari)", fontsize=12)
    ax.set_ylabel("Frekuensi", fontsize=12)
    st.pyplot(fig)

    # Metrik Pendukung
    col1, col2, col3 = st.columns(3)
    with col1:
      st.metric(
          "Total Seller Teridentifikasi (>20%)",
          value=len(seller_metrics_df),
      )
    with col2:
      total_bad_delayed = len(bad_reviews_df)
      st.metric("Total Transaksi Bermasalah", value=total_bad_delayed)
    with col3:
      mean_delay = round(bad_reviews_df["delivery_delay_days"].mean(), 1)
      st.metric("Rata-rata Keterlambatan (Hari)", value=mean_delay)

except Exception as e:
  st.error(f"Gagal memuat visualisasi 2: {e}")
