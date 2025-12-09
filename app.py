import streamlit as st
import pandas as pd
import os
import altair as alt
from io import BytesIO

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Stryker Inventory Dashboard", layout="wide", page_icon="📊")

# --- CSS İLE STRYKER TEMASI VE SEKME AYARLARI ---
st.markdown("""
    <style>
        .block-container {padding-top: 1rem; padding-bottom: 0rem;}
        h1 {color: #FFC107; text-align: center;}
        div.stButton > button:first-child {background-color: #FFC107; color: black;}
        
        /* Sekme (Tab) Tasarımı */
        .stTabs [data-baseweb="tab-list"] {gap: 10px;}
        .stTabs [data-baseweb="tab"] {height: 50px; white-space: pre-wrap; background-color: #f0f2f6; border-radius: 4px 4px 0px 0px;}
        .stTabs [aria-selected="true"] {background-color: #FFC107; color: black; font-weight: bold;}
    </style>
""", unsafe_allow_html=True)

st.title("📦 Stryker - Inventory Intelligence")
st.markdown("---")

# --- VERİ YÜKLEME ---
def verileri_yukle():
    st.sidebar.header("📂 Data Source")
    uploaded_file = st.sidebar.file_uploader("Upload Daily Excel", type=["xlsx"])
    
    if uploaded_file is not None:
        return pd.read_excel(uploaded_file)
    elif os.path.exists('stok.xlsx'):
        return pd.read_excel('stok.xlsx')
    else:
        return pd.DataFrame()

df = verileri_yukle()

# --- EXCEL İNDİRME FONKSİYONU ---
def excel_olustur(df_input):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_input.to_excel(writer, index=False, sheet_name='Report')
    return output.getvalue()

# --- ANA PROGRAM ---
if not df.empty:
    # 1. Temizlik ve Formatlama
    df.columns = df.columns.str.strip()
    
    gerekli = ["Location", "Quantity", "Item Code"]
    eksik = [c for c in gerekli if c not in df.columns]

    if not eksik:
        # Veri tiplerini ayarla
        df["Location"] = df["Location"].astype(str)
        df["Item Code"] = df["Item Code"].astype(str)
        
        # Quantity sütununu sayıya çevir (Hata varsa 0 yap)
        df["Quantity"] = pd.to_numeric(df["Quantity"], errors='coerce').fillna(0)

        # --- SOL MENÜ (FİLTRELER) ---
        st.sidebar.header("🔍 Filter Settings")

        # Lokasyon Seçimi
        tum_lokasyonlar = sorted(list(df["Location"].unique()))
        secilen_yerler = st.sidebar.multiselect("Select Locations:", tum_lokasyonlar) # Varsayılan boş (hepsi)
        
        # Ürün Seçimi (Akıllı Filtre)
        if secilen_yerler:
            mevcut_urunler = df[df["Location"].isin(secilen_yerler)]["Item Code"].unique()
        else:
            mevcut_urunler = df["Item Code"].unique()
            
        secilen_urunler = st.sidebar.multiselect("Select Items:", sorted(list(mevcut_urunler)))

        # --- FİLTRELEME MOTORU ---
        df_filtered = df.copy()
        
        if secilen_yerler:
            df_filtered = df_filtered[df_filtered["Location"].isin(secilen_yerler)]
        
        if secilen_urunler:
            df_filtered = df_filtered[df_filtered["Item Code"].isin(secilen_urunler)]

        if not df_filtered.empty:
            
            # --- SEKMELİ YAPI (TABS) BAŞLANGICI ---
            tab1, tab2 = st.tabs(["📊 Dashboard", "📋 Detaylı Liste"])

            # ----------------------------------
            # SEKME 1: DASHBOARD (Özet ve Grafik)
            # ----------------------------------
            with tab1:
                # KPI Kartları
                total_qty = df_filtered["Quantity"].sum()
                total_items = df_filtered["Item Code"].nunique()
                total_locs = df_filtered["Location"].nunique()
                
                kpi1, kpi2, kpi3 = st.columns(3)
                kpi1.metric("📦 Total Inventory", f"{total_qty:,.0f} Units")
                kpi2.metric("🏷️ Unique SKUs", f"{total_items} Types")
                kpi3.metric("📍 Active Locations", f"{total_locs} Locs")
                
                st.divider()
                st.subheader("📊 Stock Distribution (Top 20 Locations)")
                
                # Grafik Verisi (En çok stoğu olan ilk 20 depo)
                chart_data = df_filtered.groupby("Location")["Quantity"].sum().reset_index()
                chart_data = chart_data.nlargest(20, "Quantity")

                chart = alt.Chart(chart_data).mark_bar(
                    cornerRadius=5, color="#FFC107"
                ).encode(
                    x=alt.X('Location', sort='-y', title='Location'),
                    y=alt.Y('Quantity', title='Quantity'),
                    tooltip=['Location', 'Quantity']
                ).properties(height=400)
                
                st.altair_chart(chart, use_container_width=True)

            # ----------------------------------
            # SEKME 2: DETAYLI LİSTE (Tablo ve İndirme)
            # ----------------------------------
            with tab2:
                col_header, col_btn = st.columns([3, 1])
                col_header.subheader("📋 Detailed Inventory List")
                
                # İndirme Butonu
                excel_data = excel_olustur(df_filtered)
                col_btn.download_button(
                    "📥 Download Excel",
                    data=excel_data,
                    file_name="Stryker_Inventory_Report.xlsx",
                    mime="application/vnd.ms-excel",
                    use_container_width=True
                )

                # Gelişmiş Tablo (Progress Bar ile)
                st.dataframe(
                    df_filtered,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Location": st.column_config.TextColumn("Location", help="Depo Konumu"),
                        "Item Code": st.column_config.TextColumn("SKU Code", help="Ürün Kodu"),
                        "Quantity": st.column_config.ProgressColumn(
                            "Stock Level",
                            help="Mevcut Stok Adedi",
                            format="%d",
                            min_value=0,
                            max_value=int(df["Quantity"].max()),
                        ),
                    }
                )

        else:
            st.warning("⚠️ No data found based on selection.")
    else:
        st.error(f"Eksik Başlıklar: {eksik}")

else:
    st.info("👋 Veri bekleniyor... Lütfen sol menüden Excel dosyasını yükleyin.")