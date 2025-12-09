import streamlit as st
import pandas as pd
import os
import altair as alt
from io import BytesIO

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Stryker Inventory Dashboard", layout="wide", page_icon="📦")

# --- CSS İLE PREMIUM TASARIM ---
st.markdown("""
    <style>
        .block-container {padding-top: 1.5rem; padding-bottom: 1rem;}
        h1, h2, h3 {color: #C29B0C;} 
        div.stButton > button:first-child {
            background-color: #FFC107; 
            color: black; 
            border-radius: 8px; 
            border: none;
            font-weight: bold;
        }
        .stTabs [data-baseweb="tab-list"] {gap: 8px;}
        .stTabs [data-baseweb="tab"] {
            height: 45px; 
            background-color: #ffffff; 
            border-radius: 6px; 
            border: 1px solid #e0e0e0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }
        .stTabs [aria-selected="true"] {
            background-color: #FFC107; 
            color: black; 
            font-weight: bold;
            border: none;
        }
        div[data-testid="stMetric"] {
            background-color: #ffffff;
            border: 1px solid #f0f0f0;
            padding: 15px;
            border-radius: 10px;
            box-shadow: 2px 2px 8px rgba(0,0,0,0.05);
            text-align: center;
        }
    </style>
""", unsafe_allow_html=True)

# --- BAŞLIK ---
col_logo, col_title = st.columns([1, 6])
with col_title:
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
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_input.to_excel(writer, index=False, sheet_name='Report')
    return output.getvalue()

# --- ANA PROGRAM ---
if not df.empty:
    df.columns = df.columns.str.strip()
    
    gerekli = ["Location", "Quantity", "Item Code"]
    eksik = [c for c in gerekli if c not in df.columns]

    if not eksik:
        # Veri Tipi Dönüşümleri
        df["Location"] = df["Location"].astype(str)
        df["Item Code"] = df["Item Code"].astype(str)
        df["Quantity"] = pd.to_numeric(df["Quantity"], errors='coerce').fillna(0)

        # --- SOL MENÜ FİLTRELERİ ---
        st.sidebar.header("🔍 Filter Settings")
        st.sidebar.markdown("---")
        
        # 1. Lokasyon Seçimi
        tum_lokasyonlar = sorted(list(df["Location"].unique()))
        secilen_yerler = st.sidebar.multiselect("Select Locations:", tum_lokasyonlar)
        
        # Lokasyona göre ürünleri daralt
        if secilen_yerler:
            mevcut_urunler = df[df["Location"].isin(secilen_yerler)]["Item Code"].unique()
        else:
            mevcut_urunler = df["Item Code"].unique()
            
        # 2. Ürün Seçimi
        secilen_urunler = st.sidebar.multiselect("Select Items:", sorted(list(mevcut_urunler)))
        
        st.sidebar.markdown("---")
        
        # --- YENİ EKLENEN ARAMA KISMI ---
        st.sidebar.markdown("**Deep Search**")
        col_search, col_btn = st.sidebar.columns([4, 1])
        
        with col_search:
            search_term = st.text_input("Arama", placeholder="Kod veya Lokasyon ara...", label_visibility="collapsed")
        
        with col_btn:
            # Butona basılması veya Enter'a basılması text_input ile tetiklenir
            search_clicked = st.button("🔎", use_container_width=True)

        # --- FİLTRELEME MANTIĞI ---
        df_filtered = df.copy()
        
        # Sidebar filtrelerini uygula
        if secilen_yerler: 
            df_filtered = df_filtered[df_filtered["Location"].isin(secilen_yerler)]
        if secilen_urunler: 
            df_filtered = df_filtered[df_filtered["Item Code"].isin(secilen_urunler)]
            
        # Arama kutusu doluysa filtrele (Hem Item Code hem Location içinde arar)
        if search_term:
            df_filtered = df_filtered[
                df_filtered["Item Code"].str.contains(search_term, case=False, na=False) |
                df_filtered["Location"].str.contains(search_term, case=False, na=False)
            ]

        # --- DASHBOARD GÖSTERİMİ ---
        if not df_filtered.empty:
            
            tab1, tab2 = st.tabs(["📊 Executive Dashboard", "📋 Detailed Inventory"])

            # TAB 1: GRAFİKLER
            with tab1:
                st.markdown("### 🚀 Key Performance Indicators")
                total_qty = df_filtered["Quantity"].sum()
                total_items = df_filtered["Item Code"].nunique()
                total_locs = df_filtered["Location"].nunique()
                
                kpi1, kpi2, kpi3 = st.columns(3)
                kpi1.metric("📦 Total Inventory", f"{total_qty:,.0f}")
                kpi2.metric("🏷️ Unique SKUs", f"{total_items}")
                kpi3.metric("📍 Active Locations", f"{total_locs}")
                
                st.markdown("---")
                st.markdown("### 📈 Stock Overview (Top 20 Locations)")
                
                chart_data = df_filtered.groupby("Location")["Quantity"].sum().reset_index()
                chart_data = chart_data.nlargest(20, "Quantity")

                chart = alt.Chart(chart_data).mark_bar(
                    cornerRadius=6, color="#FFC107", size=30
                ).encode(
                    x=alt.X('Location', sort='-y', title='Location Code'),
                    y=alt.Y('Quantity', title='Quantity Units'),
                    tooltip=['Location', 'Quantity']
                ).properties(height=450).configure_axis(grid=False)
                
                st.altair_chart(chart, use_container_width=True)

            # TAB 2: DETAYLI TABLO
            with tab2:
                col_header, col_btn = st.columns([4, 1])
                col_header.markdown("### 📋 Detailed Stock List")
                
                excel_data = excel_olustur(df_filtered)
                col_btn.download_button(
                    "📥 Download Excel",
                    data=excel_data,
                    file_name="Stryker_Inventory_Report.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )

                max_stok = int(df["Quantity"].max())
                if max_stok == 0: max_stok = 1 

                st.dataframe(
                    df_filtered,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Location": st.column_config.TextColumn("Location", help="Warehouse Location"),
                        "Item Code": st.column_config.TextColumn("SKU Code", help="Product Item Code"),
                        "Quantity": st.column_config.ProgressColumn(
                            "Stock Level",
                            format="%d",
                            min_value=0,
                            max_value=max_stok,
                        ),
                    }
                )

        else:
            st.warning(f"⚠️ '{search_term}' için veri bulunamadı. Lütfen filtreleri kontrol edin.")
    else:
        st.error(f"Missing Headers: {eksik}")
else:
    st.info("👋 Welcome! Please upload your 'stok.xlsx' file to start.")