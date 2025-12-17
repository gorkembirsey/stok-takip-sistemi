import streamlit as st
import pandas as pd
import altair as alt
from io import BytesIO

# --- SAYFA YAPILANDIRMASI ---
# Sayfa sekmesinde görünen isim güncellendi
st.set_page_config(page_title="Stock Control Intelligence", layout="wide", page_icon="📦")

# --- CSS AYARLARI (GÖRSELLİK BURADA) ---
st.markdown("""
    <style>
        .stApp {background-color: #F5F7FA;}

        /* Tablo Başlıklarını (Header) Renklendirme */
        thead tr th:first-child {display:none}
        thead th {
            background-color: #FFC107 !important; /* Stryker Gold */
            color: black !important;
            font-size: 14px !important;
            text-align: center !important;
        }

        /* Tablo Satırları (Zebra Efekti) */
        tbody tr:nth-of-type(odd) {
            background-color: #ffffff;
        }
        tbody tr:nth-of-type(even) {
            background-color: #fffdf0; /* Çok hafif sarımsı */
        }

        /* Tab Sekmeleri */
        .stTabs [data-baseweb="tab-list"] {gap: 10px;}
        .stTabs [data-baseweb="tab"] {height: 45px; background-color: white; border-radius: 5px; font-weight: bold; border: 1px solid #ddd;}
        .stTabs [aria-selected="true"] {background-color: #FFC107 !important; color: black !important; border-color: #FFC107 !important;}

        /* KPI Kartları */
        div[data-testid="stMetric"] {background-color: #ffffff; border-radius: 10px; padding: 15px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); border-left: 5px solid #FFC107;}
    </style>
""", unsafe_allow_html=True)

# --- YAN MENÜ ---
with st.sidebar:
    st.image(
        "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c2/Stryker_Corporation_logo.svg/2560px-Stryker_Corporation_logo.svg.png",
        width=150)
    st.header("📂 Veri Girişi")
    uploaded_file = st.file_uploader("Günlük Excel Dosyası", type=["xlsx"])

    st.markdown("---")
    st.header("🔍 Gelişmiş Arama")
    search_query = st.text_input("Arama Yap:", placeholder="Item No, Description, PO veya Lokasyon...")
    st.caption("Not: Bu alana yazdığınız kelime tüm sütunlarda (Kod, Açıklama, Sipariş No vb.) aranır.")

    if search_query:
        st.info(f"Aranan Kelime: **{search_query}**")
        if st.button("Temizle"):
            st.rerun()

# --- ANA PROGRAM ---
if uploaded_file:
    try:
        # Excel'i Oku
        xls = pd.read_excel(uploaded_file, sheet_name=None)
        sheets = {k.strip(): v for k, v in xls.items()}

        # --- VERİ HAZIRLIĞI ---

        target_col = 'SS Coverage (W/O Consignment)'

        # 1. GENERAL SHEET
        df_gen = sheets.get("General", pd.DataFrame())
        if not df_gen.empty:
            df_gen.columns = df_gen.columns.str.strip()
            if 'Item No' in df_gen.columns: df_gen['Item No'] = df_gen['Item No'].astype(str).str.strip()
            if target_col in df_gen.columns:
                df_gen[target_col] = pd.to_numeric(df_gen[target_col], errors='coerce')
                df_gen[target_col] = (df_gen[target_col] * 100).fillna(0)

        # 2. STOCK OUT SHEET
        df_out = sheets.get("Stock Out", pd.DataFrame())
        if not df_out.empty:
            df_out.columns = df_out.columns.str.strip()
            if 'Item No' in df_out.columns: df_out['Item No'] = df_out['Item No'].astype(str).str.strip()
            if target_col in df_out.columns:
                df_out[target_col] = pd.to_numeric(df_out[target_col], errors='coerce')
                df_out[target_col] = (df_out[target_col] * 100).fillna(0)

        # 3. VENLO ORDERS SHEET
        df_venlo = sheets.get("Venlo Orders", pd.DataFrame())
        if not df_venlo.empty:
            df_venlo.columns = df_venlo.columns.str.strip()
            df_venlo.rename(columns={'Item Code': 'Item No'}, inplace=True)
            if 'Item No' in df_venlo.columns: df_venlo['Item No'] = df_venlo['Item No'].astype(str).str.strip()

        # 4. YOLDAKİ İTHALATLAR SHEET
        df_yolda = sheets.get("Yoldaki İthalatlar", pd.DataFrame())
        if not df_yolda.empty:
            df_yolda.columns = df_yolda.columns.str.strip()
            df_yolda.rename(columns={'Ordered Item Number': 'Item No'}, inplace=True)
            if 'Item No' in df_yolda.columns: df_yolda['Item No'] = df_yolda['Item No'].astype(str).str.strip()

        # 5. STOK SHEET
        df_stok = sheets.get("Stok", pd.DataFrame())
        if not df_stok.empty:
            df_stok.columns = df_stok.columns.str.strip()
            df_stok.rename(columns={'Item Number': 'Item No'}, inplace=True)
            if 'Item No' in df_stok.columns: df_stok['Item No'] = df_stok['Item No'].astype(str).str.strip()
            if 'Qty On Hand' in df_stok.columns: df_stok['Qty On Hand'] = pd.to_numeric(df_stok['Qty On Hand'],
                                                                                        errors='coerce').fillna(0)

        # --- GELİŞMİŞ FİLTRELEME (MULTI-SEARCH) ---
        if search_query:
            sq = search_query.lower()


            def filter_df(df, cols_to_search):
                if df.empty: return df
                mask = pd.Series([False] * len(df))
                for col in cols_to_search:
                    if col in df.columns:
                        mask = mask | df[col].astype(str).str.lower().str.contains(sq, na=False)
                return df[mask]


            df_gen = filter_df(df_gen, ['Item No', 'Item Description'])
            df_out = filter_df(df_out, ['Item No', 'Item Description'])
            df_venlo = filter_df(df_venlo, ['Item No', 'TP Description', 'Customer PO', 'Order Number'])
            df_yolda = filter_df(df_yolda, ['Item No', 'Item Description', 'Order No'])
            df_stok = filter_df(df_stok, ['Item No', 'Location'])

        # --- DASHBOARD GÖRÜNÜMÜ ---

        # 1. Başlık Güncellemesi
        st.title("Stock Control Intelligence")

        # KPI Kartları
        qty_hand = df_stok['Qty On Hand'].sum() if not df_stok.empty else 0
        qty_order = df_venlo[
            'Ordered Qty Order UOM'].sum() if not df_venlo.empty and 'Ordered Qty Order UOM' in df_venlo.columns else 0
        qty_ship = df_yolda['Qty Shipped'].sum() if not df_yolda.empty and 'Qty Shipped' in df_yolda.columns else 0

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("📦 Depo Stoğu", f"{qty_hand:,.0f}")
        col2.metric("🌍 Venlo Sipariş", f"{qty_order:,.0f}")
        col3.metric("🚢 Yoldaki Miktar", f"{qty_ship:,.0f}")
        col4.metric("🚨 Kritik Ürün", f"{len(df_out)}")

        st.markdown("###")

        # --- SEKMELER ---
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📋 General",
            "📍 Stok (Depo)",
            "🌍 Venlo Orders",
            "🚚 Yoldaki İthalatlar",
            "🚨 Stock Out"
        ])

        # TAB 1: GENERAL
        with tab1:
            if not df_gen.empty:
                st.dataframe(
                    df_gen,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "SS Coverage (W/O Consignment)": st.column_config.NumberColumn(
                            "SS Coverage (W/O Consignment)",
                            format="%.1f%%"
                        )
                    }
                )
            else:
                st.info("Veri yok.")

        # TAB 2: STOK
        with tab2:
            if not df_stok.empty:
                col_chart, col_data = st.columns([1, 1])

                with col_chart:
                    if 'Location' in df_stok.columns and 'Qty On Hand' in df_stok.columns:
                        # Grafik (İlk 12)
                        loc_summ = df_stok.groupby('Location')['Qty On Hand'].sum().reset_index()
                        loc_summ = loc_summ.sort_values('Qty On Hand', ascending=False).head(12)

                        st.markdown("##### 🏆 En Yoğun 12 Lokasyon")
                        chart_stok = alt.Chart(loc_summ).mark_bar(color='#FFC107').encode(
                            x=alt.X('Location', sort='-y', title='Lokasyon'),
                            y=alt.Y('Qty On Hand', title='Miktar'),
                            tooltip=['Location', 'Qty On Hand']
                        ).properties(height=400)
                        st.altair_chart(chart_stok, use_container_width=True)

                with col_data:
                    st.markdown("##### 📝 Detaylı Stok Listesi")
                    st.dataframe(df_stok, use_container_width=True, hide_index=True)
            else:
                st.warning("Veri yok.")

        # TAB 3: VENLO
        with tab3:
            if not df_venlo.empty:
                st.dataframe(df_venlo, use_container_width=True, hide_index=True)
            else:
                st.info("Veri yok.")

        # TAB 4: YOLDAKİ
        with tab4:
            if not df_yolda.empty:
                st.dataframe(df_yolda, use_container_width=True, hide_index=True)
            else:
                st.info("Veri yok.")

        # TAB 5: STOCK OUT
        with tab5:
            if not df_out.empty:
                st.error("Kritik Ürün Listesi")
                st.dataframe(
                    df_out,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "SS Coverage (W/O Consignment)": st.column_config.NumberColumn(
                            "SS Coverage (W/O Consignment)",
                            format="%.1f%%"
                        )
                    }
                )
            else:
                st.success("Kritik ürün yok.")

    except Exception as e:
        st.error(f"Hata: {e}")

else:
    st.info("👆 Lütfen Excel dosyasını yükleyin.")