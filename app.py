import streamlit as st
import pandas as pd
import os
import altair as alt
from io import BytesIO

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Stryker Pro Dashboard", layout="wide", page_icon="📊")

# --- CSS İLE GÖRSELLİK (LOGO VE RENKLER) ---
# Buraya Stryker sarısını/altın rengini entegre ediyoruz
st.markdown("""
    <style>
        .block-container {padding-top: 1rem; padding-bottom: 0rem;}
        h1 {color: #FFC107; text-align: center;}
        div.stButton > button:first-child {background-color: #FFC107; color: black;}
    </style>
""", unsafe_allow_html=True)

st.title("📦 Stryker - Inventory Intelligence")
st.markdown("---")

# --- VERİ YÜKLEME VE OKUMA ---
# Önce kullanıcı dosya yükledi mi ona bakar, yoksa GitHub'daki stok.xlsx'i okur
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
    # 1. TEMİZLİK VE TİP DÖNÜŞÜMÜ
    df.columns = df.columns.str.strip()
    
    # Gerekli başlıklar kontrolü
    gerekli = ["Location", "Quantity", "Item Code"]
    eksik = [c for c in gerekli if c not in df.columns]

    if not eksik:
        # Tipleri string yapalım ki filtrelerde hata çıkmasın
        df["Location"] = df["Location"].astype(str)
        df["Item Code"] = df["Item Code"].astype(str)

        # --- SOL MENÜ (FİLTRELER) ---
        st.sidebar.header("🔍 Smart Filters")

        # ÇOKLU SEÇİM (MULTI-SELECT) ÖZELLİĞİ
        # Lokasyonlar
        tum_lokasyonlar = sorted(list(df["Location"].unique()))
        secilen_yerler = st.sidebar.multiselect("Select Locations:", tum_lokasyonlar, default=tum_lokasyonlar[:1])
        
        # Ürünler (Seçilen lokasyona göre daraltılmış)
        if secilen_yerler:
            mevcut_urunler = df[df["Location"].isin(secilen_yerler)]["Item Code"].unique()
        else:
            mevcut_urunler = df["Item Code"].unique()
            
        secilen_urunler = st.sidebar.multiselect("Select Items:", sorted(list(mevcut_urunler)))

        # Grafik Ayarı
        show_chart = st.sidebar.toggle("Show Analytics Chart", value=True)

        # --- FİLTRELEME MOTORU ---
        df_filtered = df.copy()
        
        # Eğer lokasyon seçildiyse filtrele (Boşsa hepsi gelir)
        if secilen_yerler:
            df_filtered = df_filtered[df_filtered["Location"].isin(secilen_yerler)]
        
        # Eğer ürün seçildiyse filtrele
        if secilen_urunler:
            df_filtered = df_filtered[df_filtered["Item Code"].isin(secilen_urunler)]

        # --- KPI KARTLARI (EN ÜST) ---
        if not df_filtered.empty:
            total_qty = df_filtered["Quantity"].sum()
            total_items = df_filtered["Item Code"].nunique()
            total_locs = df_filtered["Location"].nunique()
            
            # 3'lü kolon yapısı
            kpi1, kpi2, kpi3 = st.columns(3)
            kpi1.metric("📦 Total Inventory", f"{total_qty:,.0f} Units")
            kpi2.metric("🏷️ Unique SKUs", f"{total_items} Types")
            kpi3.metric("📍 Active Locations", f"{total_locs} Locs")
            
            st.divider()

            # --- GRAFİK BÖLÜMÜ ---
            if show_chart:
                col_chart, col_empty = st.columns([2, 1]) # Grafiği sola yasla, sağ taraf boş kalsın
                
                with col_chart:
                    st.subheader("📊 Stock Distribution (Top 20)")
                    
                    # Veriyi hazırla ve Top 20 al
                    chart_data = df_filtered.groupby("Location")["Quantity"].sum().reset_index()
                    chart_data = chart_data.nlargest(20, "Quantity")

                    chart = alt.Chart(chart_data).mark_bar(
                        cornerRadius=5, color="#FFC107" # Stryker sarısına yakın renk
                    ).encode(
                        x=alt.X('Location', sort='-y', title='Location'),
                        y=alt.Y('Quantity', title=None),
                        tooltip=['Location', 'Quantity']
                    ).properties(height=350)
                    
                    st.altair_chart(chart, use_container_width=True)

            # --- GELİŞMİŞ TABLO (DATA BARS) ---
            st.subheader("📋 Detailed Inventory")
            
            # İndirme Butonu
            excel_data = excel_olustur(df_filtered)
            st.download_button(
                "📥 Download Report as Excel",
                data=excel_data,
                file_name="Stryker_Inventory_Report.xlsx",
                mime="application/vnd.ms-excel"
            )

            # Tablo Görselleştirme (Column Config)
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
                        max_value=int(df["Quantity"].max()), # En büyük değere göre çubuğu ayarlar
                    ),
                }
            )

        else:
            st.warning("⚠️ No data found based on selection.")
    else:
        st.error(f"Eksik Başlıklar: {eksik}")

else:
    st.info("👋 Veri bekleniyor... Lütfen sol menüden Excel dosyasını yükleyin veya GitHub'a 'stok.xlsx' ekleyin.")