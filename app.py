import streamlit as st
import pandas as pd
import altair as alt
from io import BytesIO

# --- SAYFA YAPILANDIRMASI ---
st.set_page_config(page_title="Stryker Entegre Stok Sistemi", layout="wide", page_icon="🏢")

# --- CSS AYARLARI ---
st.markdown("""
    <style>
        .stApp {background-color: #F5F7FA;}
        .stTabs [data-baseweb="tab-list"] {gap: 10px;}
        .stTabs [data-baseweb="tab"] {height: 50px; background-color: white; border-radius: 5px; font-weight: bold;}
        .stTabs [aria-selected="true"] {background-color: #FFC107 !important; color: black !important;}
        div[data-testid="stMetric"] {background-color: #ffffff; border-radius: 10px; padding: 15px; box-shadow: 0 2px 5px rgba(0,0,0,0.05);}
    </style>
""", unsafe_allow_html=True)

# --- YAN MENÜ ---
with st.sidebar:
    st.image(
        "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c2/Stryker_Corporation_logo.svg/2560px-Stryker_Corporation_logo.svg.png",
        width=150)
    st.header("📂 Veri Girişi")
    uploaded_file = st.file_uploader("Günlük Stok Raporu (Excel)", type=["xlsx"])

    st.markdown("---")
    st.header("🔍 Ürün Arama")
    search_query = st.text_input("Item No Giriniz:", placeholder="Örn: 68334061E")

    if search_query:
        st.info(f"Filtrelenen: **{search_query}**")
        if st.button("Temizle"):
            st.rerun()

# --- ANA PROGRAM ---
if uploaded_file:
    try:
        # Excel'i Oku (Tüm sayfalar)
        xls = pd.read_excel(uploaded_file, sheet_name=None)

        # Sayfa İsimlerindeki Boşlukları Temizle ("General " -> "General")
        sheets = {k.strip(): v for k, v in xls.items()}

        # --- VERİ HAZIRLIĞI VE SÜTUN STANDARTLAŞTIRMA ---

        # 1. GENERAL SHEET
        df_gen = sheets.get("General", pd.DataFrame())
        if not df_gen.empty:
            df_gen.columns = df_gen.columns.str.strip()
            # Item No zaten var, ama string yapalım garanti olsun
            if 'Item No' in df_gen.columns:
                df_gen['Item No'] = df_gen['Item No'].astype(str).str.strip()

        # 2. STOCK OUT SHEET
        df_out = sheets.get("Stock Out", pd.DataFrame())
        if not df_out.empty:
            df_out.columns = df_out.columns.str.strip()
            if 'Item No' in df_out.columns:
                df_out['Item No'] = df_out['Item No'].astype(str).str.strip()

        # 3. VENLO ORDERS SHEET (Item Code -> Item No)
        df_venlo = sheets.get("Venlo Orders", pd.DataFrame())
        if not df_venlo.empty:
            df_venlo.columns = df_venlo.columns.str.strip()
            # İsmi değiştiriyoruz
            df_venlo.rename(columns={'Item Code': 'Item No'}, inplace=True)
            if 'Item No' in df_venlo.columns:
                df_venlo['Item No'] = df_venlo['Item No'].astype(str).str.strip()

        # 4. YOLDAKİ İTHALATLAR SHEET (Ordered Item Number -> Item No)
        df_yolda = sheets.get("Yoldaki İthalatlar", pd.DataFrame())
        if not df_yolda.empty:
            df_yolda.columns = df_yolda.columns.str.strip()
            df_yolda.rename(columns={'Ordered Item Number': 'Item No'}, inplace=True)
            if 'Item No' in df_yolda.columns:
                df_yolda['Item No'] = df_yolda['Item No'].astype(str).str.strip()

        # 5. STOK SHEET (Item Number -> Item No)
        df_stok = sheets.get("Stok", pd.DataFrame())
        if not df_stok.empty:
            df_stok.columns = df_stok.columns.str.strip()
            df_stok.rename(columns={'Item Number': 'Item No'}, inplace=True)
            if 'Item No' in df_stok.columns:
                df_stok['Item No'] = df_stok['Item No'].astype(str).str.strip()

        # --- GLOBAL FİLTRELEME ---
        # Arama yapıldıysa tüm tabloları o ürüne göre daralt
        if search_query:
            if not df_gen.empty and 'Item No' in df_gen.columns:
                df_gen = df_gen[df_gen['Item No'].str.contains(search_query, case=False, na=False)]
            if not df_out.empty and 'Item No' in df_out.columns:
                df_out = df_out[df_out['Item No'].str.contains(search_query, case=False, na=False)]
            if not df_venlo.empty and 'Item No' in df_venlo.columns:
                df_venlo = df_venlo[df_venlo['Item No'].str.contains(search_query, case=False, na=False)]
            if not df_yolda.empty and 'Item No' in df_yolda.columns:
                df_yolda = df_yolda[df_yolda['Item No'].str.contains(search_query, case=False, na=False)]
            if not df_stok.empty and 'Item No' in df_stok.columns:
                df_stok = df_stok[df_stok['Item No'].str.contains(search_query, case=False, na=False)]

        # --- DASHBOARD BAŞLANGIÇ ---
        st.title("📊 Stryker 360° Stok Yönetimi")

        # KPI Kartları (Sütunlar mevcutsa hesapla)
        qty_hand = df_stok['Qty On Hand'].sum() if not df_stok.empty and 'Qty On Hand' in df_stok.columns else 0
        qty_order = df_venlo[
            'Ordered Qty Order UOM'].sum() if not df_venlo.empty and 'Ordered Qty Order UOM' in df_venlo.columns else 0
        qty_ship = df_yolda['Qty Shipped'].sum() if not df_yolda.empty and 'Qty Shipped' in df_yolda.columns else 0

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("📦 Depo Stoğu", f"{qty_hand:,.0f}")
        col2.metric("🌍 Venlo Sipariş", f"{qty_order:,.0f}")
        col3.metric("🚢 Yoldaki Miktar", f"{qty_ship:,.0f}")
        col4.metric("🚨 Kritik Ürün", f"{len(df_out)}")

        st.markdown("---")

        # --- SEKMELER (TABS) ---
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📋 General (Genel)",
            "📍 Stok (Depo)",
            "🌍 Venlo Orders",
            "🚚 Yoldaki İthalatlar",
            "🚨 Stock Out"
        ])

        # TAB 1: GENERAL
        with tab1:
            st.subheader("Genel Ürün Listesi")
            if not df_gen.empty:
                st.dataframe(df_gen, use_container_width=True, hide_index=True)
            else:
                st.info("Veri yok.")

        # TAB 2: STOK
        with tab2:
            st.subheader("Depo Lokasyon Detayları")
            if not df_stok.empty:
                # Lokasyon Grafiği
                if 'Location' in df_stok.columns and 'Qty On Hand' in df_stok.columns:
                    chart_stok = alt.Chart(df_stok).mark_bar(color='#FFC107').encode(
                        x=alt.X('Location', sort='-y', title='Lokasyon'),
                        y=alt.Y('Qty On Hand', title='Miktar'),
                        tooltip=['Location', 'Item No', 'Qty On Hand', 'Expire']
                    ).properties(height=300)
                    st.altair_chart(chart_stok, use_container_width=True)

                st.dataframe(df_stok, use_container_width=True, hide_index=True)
            else:
                st.warning("Stok verisi bulunamadı.")

        # TAB 3: VENLO
        with tab3:
            st.subheader("Venlo Açık Siparişler")
            if not df_venlo.empty:
                st.dataframe(df_venlo, use_container_width=True, hide_index=True)
            else:
                st.info("Sipariş verisi yok.")

        # TAB 4: YOLDAKİ
        with tab4:
            st.subheader("Sevkiyat / Gümrük Durumu")
            if not df_yolda.empty:
                st.dataframe(df_yolda, use_container_width=True, hide_index=True)
            else:
                st.info("Yolda ürün yok.")

        # TAB 5: STOCK OUT
        with tab5:
            st.subheader("Kritik Stok Seviyeleri")
            if not df_out.empty:
                st.error("Aşağıdaki ürünler kritik seviyededir:")
                st.dataframe(df_out, use_container_width=True, hide_index=True)
            else:
                st.success("Kritik ürün bulunmamaktadır.")

    except Exception as e:
        st.error(f"Bir hata oluştu: {e}")
        st.write("Lütfen Excel dosyanızın sayfa isimlerini ve başlıklarını kontrol ediniz.")

else:
    st.info("👆 Başlamak için Excel dosyanızı yükleyin.")