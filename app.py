import streamlit as st
import pandas as pd
import os
import altair as alt

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Stock Tracking", layout="wide")

# Başlık
st.title("📦 Company Stock List")

# --- EXCEL OKUMA ---
def verileri_getir():
    if os.path.exists('stok.xlsx'):
        return pd.read_excel('stok.xlsx')
    else:
        return pd.DataFrame()

df = verileri_getir()

# --- EKRAN TASARIMI ---
if not df.empty:
    # 1. Temizlik
    df.columns = df.columns.str.strip()

    # 2. Başlık Kontrolü
    gerekli_basliklar = ["Location", "Quantity", "Item Code"]
    eksik_basliklar = [col for col in gerekli_basliklar if col not in df.columns]

    if not eksik_basliklar:
        # --- SOL MENÜ (Filtre ve Ayarlar) ---
        st.sidebar.header("🔍 Filter & Settings")
        
        # 1. Lokasyon Seçimi
        yerler = ["All"] + list(df["Location"].unique())
        secilen_yer = st.sidebar.selectbox("Select Location:", yerler)

        # 2. Ürün Seçimi
        urunler = ["All"] + list(df["Item Code"].unique())
        secilen_urun = st.sidebar.selectbox("Select Item:", urunler)
        
        # 3. Grafik Aç/Kapa
        st.sidebar.write("---") 
        grafigi_goster = st.sidebar.checkbox("📊 Show Chart", value=True) 
        
        # --- FİLTRELEME MANTIĞI ---
        gosterilecek_tablo = df

        if secilen_yer != "All":
            gosterilecek_tablo = gosterilecek_tablo[gosterilecek_tablo["Location"] == secilen_yer]
        
        if secilen_urun != "All":
            gosterilecek_tablo = gosterilecek_tablo[gosterilecek_tablo["Item Code"] == secilen_urun]

        # Grafik Başlığı
        grafik_basligi = f"📊 Stock Status: {secilen_yer} / {secilen_urun}"

        # --- SONUÇ KONTROLÜ ---
        if not gosterilecek_tablo.empty:
            
            # --- METRİKLER ---
            col1, col2 = st.columns(2)
            toplam_adet = gosterilecek_tablo["Quantity"].sum()
            cesit_sayisi = gosterilecek_tablo["Item Code"].nunique()

            col1.metric("Total Item Quantity", f"{toplam_adet} Units")
            col2.metric("Total Item Code", f"{cesit_sayisi} Types")

            # --- GELİŞMİŞ GRAFİK ---
            if grafigi_goster:
                st.divider()
                st.subheader(grafik_basligi)
                
                # Veriyi lokasyona göre grupla
                grafik_verisi = gosterilecek_tablo.groupby("Location")["Quantity"].sum().reset_index()

                chart = alt.Chart(grafik_verisi).mark_bar(
                    cornerRadiusTopLeft=10,
                    cornerRadiusTopRight=10,
                    size=60
                ).encode(
                    x=alt.X('Location', title='Location', axis=alt.Axis(labelAngle=0)),
                    y=alt.Y('Quantity', title='Quantity', scale=alt.Scale(domainMin=0)),
                    color=alt.Color('Location', legend=None),
                    # DÜZELTİLEN KISIM BURASI: 'Item Code' listeden çıkarıldı
                    tooltip=['Location', 'Quantity'] 
                ).properties(
                    height=400
                ).configure_axis(
                    grid=True,
                    labelFontSize=12,
                    titleFontSize=14
                )

                st.altair_chart(chart, use_container_width=True)

            # --- TABLO ---
            st.divider()
            st.subheader("📋 Stock List")
            st.dataframe(gosterilecek_tablo, use_container_width=True, hide_index=True)
        
        else:
            st.warning(f"⚠️ No records found for Location: **{secilen_yer}** and Item: **{secilen_urun}**")

    else:
        st.error("Error: Excel headers do not match!")
        st.warning(f"Please check your Excel file for these headers: {', '.join(gerekli_basliklar)}")

    # Yenileme Butonu
    st.sidebar.write("---")
    if st.sidebar.button("🔄 Refresh List"):
        st.rerun()

else:
    st.warning("Data not found. Please check 'stok.xlsx'.")