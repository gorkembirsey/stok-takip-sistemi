import streamlit as st
import pandas as pd
import altair as alt
from io import BytesIO

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Stryker Stok Yönetim Paneli", layout="wide", page_icon="📦")

# --- CSS (Görsel Düzenlemeler) ---
st.markdown("""
    <style>
        .stApp {background-color: #F5F7FA;}
        /* Tabların görünümünü iyileştir */
        .stTabs [data-baseweb="tab-list"] {
            gap: 10px;
        }
        .stTabs [data-baseweb="tab"] {
            height: 50px;
            white-space: pre-wrap;
            background-color: #FFFFFF;
            border-radius: 5px;
            border: 1px solid #E0E0E0;
            font-weight: 600;
        }
        .stTabs [aria-selected="true"] {
            background-color: #FFC107 !important;
            color: black !important;
            border-color: #FFC107 !important;
        }
    </style>
""", unsafe_allow_html=True)


# --- EXCEL İNDİRME ---
def convert_df(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()


# --- YAN MENÜ (SIDEBAR) ---
with st.sidebar:
    st.image(
        "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c2/Stryker_Corporation_logo.svg/2560px-Stryker_Corporation_logo.svg.png",
        width=150)
    st.header("📂 Kontrol Paneli")

    # Dosya Yükleme
    uploaded_file = st.file_uploader("Günlük Excel Dosyasını Yükle", type=["xlsx"])

    st.markdown("---")

    # Arama Kutusu
    st.header("🔍 Ürün Arama")
    search_query = st.text_input("Item No Giriniz:", placeholder="Örn: 0001052001")

    if search_query:
        st.info(f"Filtrelenen Ürün: **{search_query}**")
        if st.button("Aramayı Temizle"):
            st.rerun()

# --- ANA PROGRAM ---
if uploaded_file:
    try:
        # Excel'in tüm sayfalarını oku
        xls = pd.read_excel(uploaded_file, sheet_name=None)

        # Sayfa İsimlerini Standartlaştır (Boşlukları sil)
        sheets = {k.strip(): v for k, v in xls.items()}

        # --- VERİ HAZIRLIĞI VE EŞLEŞTİRME ---
        # 1. GENERAL
        df_gen = sheets.get("General", pd.DataFrame())

        # 2. STOCK OUT
        df_out = sheets.get("Stock Out", pd.DataFrame())

        # 3. VENLO ORDERS (Item Code -> Item No)
        df_venlo = sheets.get("Venlo Orders", pd.DataFrame())
        if not df_venlo.empty:
            df_venlo.columns = df_venlo.columns.str.strip()
            # Eğer Item Code varsa adını Item No yap ki arama çalışsın
            df_venlo.rename(columns={'Item Code': 'Item No'}, inplace=True)

        # 4. YOLDAKİ İTHALATLAR (Ordered Item Number -> Item No)
        df_yolda = sheets.get("Yoldaki İthalatlar", pd.DataFrame())
        if not df_yolda.empty:
            df_yolda.columns = df_yolda.columns.str.strip()
            df_yolda.rename(columns={'Ordered Item Number': 'Item No'}, inplace=True)

        # 5. STOK (Item Number -> Item No)
        df_stok = sheets.get("Stok", pd.DataFrame())
        if not df_stok.empty:
            df_stok.columns = df_stok.columns.str.strip()
            df_stok.rename(columns={'Item Number': 'Item No'}, inplace=True)

        # --- GLOBAL FİLTRELEME ---
        # Arama kutusuna bir şey yazıldıysa TÜM tabloları süzüyoruz
        if search_query:
            if not df_gen.empty: df_gen = df_gen[
                df_gen['Item No'].astype(str).str.contains(search_query, case=False, na=False)]
            if not df_out.empty: df_out = df_out[
                df_out['Item No'].astype(str).str.contains(search_query, case=False, na=False)]
            if not df_venlo.empty: df_venlo = df_venlo[
                df_venlo['Item No'].astype(str).str.contains(search_query, case=False, na=False)]
            if not df_yolda.empty: df_yolda = df_yolda[
                df_yolda['Item No'].astype(str).str.contains(search_query, case=False, na=False)]
            if not df_stok.empty: df_stok = df_stok[
                df_stok['Item No'].astype(str).str.contains(search_query, case=False, na=False)]

        # --- BAŞLIK VE KPI ---
        st.title("📊 Stryker Entegre Stok Takibi")

        # Özet Kartlar (Filtrelenmiş veriye göre hesaplanır)
        col1, col2, col3, col4 = st.columns(4)

        qty_total = pd.to_numeric(df_stok['Qty On Hand'], errors='coerce').sum() if not df_stok.empty else 0
        venlo_total = pd.to_numeric(df_venlo['Ordered Qty'], errors='coerce').sum() if not df_venlo.empty else 0
        yolda_total = pd.to_numeric(df_yolda['Qty Shipped'], errors='coerce').sum() if not df_yolda.empty else 0
        sku_count = df_gen['Item No'].nunique() if not df_gen.empty else 0

        col1.metric("📦 Mevcut Stok", f"{qty_total:,.0f}")
        col2.metric("🌍 Venlo Sipariş", f"{venlo_total:,.0f}")
        col3.metric("🚢 Yoldaki Ürün", f"{yolda_total:,.0f}")
        col4.metric("🏷️ Ürün Çeşidi", f"{sku_count}")

        st.markdown("---")

        # --- SEKMELİ YAPI (TABS) ---
        # İşte istediğiniz özellik: Her sayfa ayrı bir tab
        tab_gen, tab_stok, tab_venlo, tab_yolda, tab_out = st.tabs([
            "📋 General (Genel)",
            "📍 Stok Detay (Depo)",
            "🌍 Venlo Orders",
            "🚚 Yoldaki İthalatlar",
            "🚨 Stock Out"
        ])

        # 1. GENERAL TAB
        with tab_gen:
            st.subheader("Genel Ürün Bilgileri")
            if not df_gen.empty:
                # Güvenlik stoğu analizi grafiği
                if 'Warehouse Stock' in df_gen.columns and 'Sfty Stock' in df_gen.columns:
                    st.markdown("##### 📉 Stok vs Güvenlik Stoğu Analizi")
                    chart_data = df_gen[['Item No', 'Warehouse Stock', 'Sfty Stock']].melt('Item No', var_name='Tip',
                                                                                           value_name='Adet')

                    chart = alt.Chart(chart_data.head(40)).mark_bar().encode(
                        x=alt.X('Item No', sort='-y'),
                        y='Adet',
                        color='Tip',
                        tooltip=['Item No', 'Tip', 'Adet']
                    ).properties(height=350)
                    st.altair_chart(chart, use_container_width=True)

                st.dataframe(df_gen, use_container_width=True, hide_index=True)
            else:
                st.warning("Veri bulunamadı.")

        # 2. STOK DETAY TAB
        with tab_stok:
            st.subheader("Lokasyon Bazlı Stok")
            if not df_stok.empty:
                col_chart, col_data = st.columns([1, 2])

                with col_chart:
                    if 'Location' in df_stok.columns:
                        st.markdown("##### 📍 Lokasyon Dağılımı")
                        loc_summ = df_stok.groupby('Location')['Qty On Hand'].sum().reset_index()
                        loc_chart = alt.Chart(loc_summ).mark_bar(color="#FFC107").encode(
                            x=alt.X('Location', sort='-y'),
                            y='Qty On Hand',
                            tooltip=['Location', 'Qty On Hand']
                        ).properties(height=400)
                        st.altair_chart(loc_chart, use_container_width=True)

                with col_data:
                    st.dataframe(df_stok, use_container_width=True, hide_index=True)
            else:
                st.warning("Veri bulunamadı.")

        # 3. VENLO TAB
        with tab_venlo:
            st.subheader("Venlo Sipariş Listesi")
            if not df_venlo.empty:
                st.dataframe(df_venlo, use_container_width=True, hide_index=True)
            else:
                st.info("Kriterlere uygun sipariş yok.")

        # 4. YOLDAKİ TAB
        with tab_yolda:
            st.subheader("Yoldaki İthalatlar (Gümrük/Sevkiyat)")
            if not df_yolda.empty:
                if 'ETA' in df_yolda.columns:
                    df_yolda['ETA'] = pd.to_datetime(df_yolda['ETA'], errors='coerce').dt.date
                st.dataframe(df_yolda, use_container_width=True, hide_index=True)
            else:
                st.info("Yolda ürün yok.")

        # 5. STOCK OUT TAB
        with tab_out:
            st.subheader("Stock Out (Kritik) Listesi")
            if not df_out.empty:
                st.error("⚠️ Aşağıdaki ürünler Stock Out durumundadır:")
                st.dataframe(df_out, use_container_width=True, hide_index=True)
            else:
                st.success("Harika! Stock Out olan ürün yok.")

    except Exception as e:
        st.error(f"Excel okunurken bir hata oluştu: {e}")
else:
    st.info("👆 Lütfen günlük Excel dosyanızı yükleyin. 5 sayfa otomatik ayrıştırılacaktır.")