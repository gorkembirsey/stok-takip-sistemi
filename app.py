import streamlit as st
import pandas as pd
import altair as alt
from io import BytesIO
import datetime

# --- SAYFA YAPILANDIRMASI ---
st.set_page_config(page_title="Stock Control Intelligence", layout="wide", page_icon="🧠")

# --- CSS AYARLARI ---
st.markdown("""
    <style>
        .stApp {background-color: #F4F6F9;}

        /* ALERT KUTUCUKLARI */
        .alert-card {
            padding: 20px; border-radius: 10px; color: white; font-weight: bold;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-bottom: 20px; text-align: center;
        }
        .bg-red {background-color: #d32f2f; border-left: 10px solid #b71c1c;}
        .bg-orange {background-color: #f57c00; border-left: 10px solid #e65100;}
        .bg-gray {background-color: #616161; border-left: 10px solid #212121;}
        .alert-number {font-size: 32px; display: block;}
        .alert-text {font-size: 16px; opacity: 0.9;}

        /* KPI KARTLARI (Sarı Şeritli) */
        div[data-testid="stMetric"] {
            background-color: #ffffff !important;
            border: 1px solid #e0e0e0;
            border-left: 8px solid #FFC107 !important;
            padding: 15px; border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }

        /* TABLO BAŞLIKLARI */
        thead th {
            background-color: #f0f2f6 !important; color: #31333F !important;
            font-size: 14px !important; font-weight: 600 !important;
            border-bottom: 2px solid #e0e0e0 !important;
        }
        tbody tr:nth-of-type(even) {background-color: #f9f9f9;}

        /* SEKMELER */
        .stTabs [data-baseweb="tab-list"] {gap: 8px;}
        .stTabs [data-baseweb="tab"] {height: 45px; background-color: white; border-radius: 4px; font-weight: 600; border: 1px solid #ddd;}
        .stTabs [aria-selected="true"] {background-color: #fff !important; color: #000 !important; border-bottom: 4px solid #FFC107 !important;}
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
    search_query = st.text_input("Arama Yap:", placeholder="Item No, SKT, Lokasyon...")

    if search_query:
        st.info(f"Aranan: **{search_query}**")
        if st.button("Temizle"):
            st.rerun()

# --- ANA PROGRAM ---
if uploaded_file:
    try:
        xls = pd.read_excel(uploaded_file, sheet_name=None)
        sheets = {k.strip(): v for k, v in xls.items()}

        # --- 1. VERİ TEMİZLİĞİ VE HAZIRLIK ---
        target_col = 'SS Coverage (W/O Consignment)'
        today = datetime.datetime.now()

        # GENERAL
        df_gen = sheets.get("General", pd.DataFrame())
        if not df_gen.empty:
            df_gen.columns = df_gen.columns.str.strip()
            if 'Item No' in df_gen.columns: df_gen['Item No'] = df_gen['Item No'].astype(str).str.strip()
            if target_col in df_gen.columns:
                df_gen[target_col] = pd.to_numeric(df_gen[target_col], errors='coerce') * 100

        # STOCK OUT
        df_out = sheets.get("Stock Out", pd.DataFrame())
        if not df_out.empty:
            df_out.columns = df_out.columns.str.strip()
            if 'Item No' in df_out.columns: df_out['Item No'] = df_out['Item No'].astype(str).str.strip()
            if target_col in df_out.columns:
                df_out[target_col] = pd.to_numeric(df_out[target_col], errors='coerce') * 100

        # VENLO
        df_venlo = sheets.get("Venlo Orders", pd.DataFrame())
        if not df_venlo.empty:
            df_venlo.columns = df_venlo.columns.str.strip()
            df_venlo.rename(columns={'Item Code': 'Item No'}, inplace=True)
            if 'Item No' in df_venlo.columns: df_venlo['Item No'] = df_venlo['Item No'].astype(str).str.strip()

        # YOLDAKİ
        df_yolda = sheets.get("Yoldaki İthalatlar", pd.DataFrame())
        if not df_yolda.empty:
            df_yolda.columns = df_yolda.columns.str.strip()
            df_yolda.rename(columns={'Ordered Item Number': 'Item No'}, inplace=True)
            if 'Item No' in df_yolda.columns: df_yolda['Item No'] = df_yolda['Item No'].astype(str).str.strip()

        # STOK & RISK ANALİZİ
        df_stok = sheets.get("Stok", pd.DataFrame())
        if not df_stok.empty:
            df_stok.columns = df_stok.columns.str.strip()
            df_stok.rename(columns={'Item Number': 'Item No'}, inplace=True)
            if 'Item No' in df_stok.columns: df_stok['Item No'] = df_stok['Item No'].astype(str).str.strip()
            if 'Qty On Hand' in df_stok.columns: df_stok['Qty On Hand'] = pd.to_numeric(df_stok['Qty On Hand'],
                                                                                        errors='coerce').fillna(0)

            # --- 🔥 SKT VE TARİH DÜZENLEME ---
            if 'Expire' in df_stok.columns:
                # Tarih objesine çevir
                df_stok['Expire_Obj'] = pd.to_datetime(df_stok['Expire'], errors='coerce')

                # Gün farkını hesapla (Risk için)
                df_stok['Days_To_Expire'] = (df_stok['Expire_Obj'] - today).dt.days

                # Görüntülenecek Temiz Tarih (Saat Yok) - İsim Değişikliği
                df_stok['Expire Date'] = df_stok['Expire_Obj'].dt.date


                # Orijinal 'Expire' sütununu kaldırıp yenisini kullanalım
                # (İsteğe bağlı, dataframe gösteriminde seçeceğiz)

                def get_risk_score(days):
                    if pd.isna(days): return "⚪ Bilinmiyor"
                    if days < 180:
                        return "🔴 Kritik (<6 Ay)"
                    elif days < 365:
                        return "🟠 Riskli (6-12 Ay)"
                    else:
                        return "🟢 Güvenli (>12 Ay)"


                df_stok['Risk Durumu'] = df_stok['Days_To_Expire'].apply(get_risk_score)
            else:
                df_stok['Risk Durumu'] = "⚪ Tarih Yok"
                df_stok['Expire Date'] = None

        # --- 2. GELİŞMİŞ FİLTRELEME ---
        if search_query:
            sq = search_query.lower()


            def filter_df(df, cols):
                if df.empty: return df
                mask = pd.Series([False] * len(df))
                for c in cols:
                    if c in df.columns: mask |= df[c].astype(str).str.lower().str.contains(sq, na=False)
                return df[mask]


            df_gen = filter_df(df_gen, ['Item No', 'Item Description'])
            df_out = filter_df(df_out, ['Item No', 'Item Description'])
            df_venlo = filter_df(df_venlo, ['Item No', 'TP Description', 'Order Number'])
            df_stok = filter_df(df_stok, ['Item No', 'Location', 'Risk Durumu'])

        # --- 3. DASHBOARD GÖRÜNÜMÜ ---
        st.title("Stock Control Intelligence")

        # ANA KPI KARTLARI
        qty_hand = df_stok['Qty On Hand'].sum() if not df_stok.empty else 0
        qty_order = df_venlo['Ordered Qty Order UOM'].sum() if not df_venlo.empty else 0
        qty_ship = df_yolda['Qty Shipped'].sum() if not df_yolda.empty else 0

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("📦 Toplam Stok", f"{qty_hand:,.0f}")
        c2.metric("🌍 Bekleyen Sipariş", f"{qty_order:,.0f}")
        c3.metric("🚢 Yoldaki Ürün", f"{qty_ship:,.0f}")
        c4.metric("📊 Listelenen Kalem", f"{len(df_gen)}")

        st.markdown("###")

        # --- SEKMELER (Alert Center En Sonda) ---
        tab1, tab2, tab3, tab4, tab5, tab_alert = st.tabs([
            "📋 General",
            "📍 Stok (Depo)",
            "🌍 Venlo Orders",
            "🚚 Yoldaki İthalatlar",
            "🚨 Stock Out",
            "🔔 Alert Center"  # En Sona Taşındı
        ])

        # --- TAB 1: GENERAL ---
        with tab1:
            if not df_gen.empty:
                st.dataframe(df_gen, use_container_width=True, hide_index=True,
                             column_config={
                                 "SS Coverage (W/O Consignment)": st.column_config.NumberColumn("SS Coverage",
                                                                                                format="%.1f%%")})
            else:
                st.info("Veri yok.")

        # --- TAB 2: STOK (SADELEŞTİRİLDİ - ESKİ HALİ) ---
        with tab2:
            if not df_stok.empty:
                c_chart, c_data = st.columns([1, 1])

                with c_chart:
                    # Sadece Lokasyon Grafiği (Eski Hal)
                    if 'Location' in df_stok.columns:
                        loc_summ = df_stok.groupby('Location')['Qty On Hand'].sum().reset_index().sort_values(
                            'Qty On Hand', ascending=False).head(12)
                        st.markdown("##### 🏆 En Yoğun 12 Lokasyon")
                        chart_stok = alt.Chart(loc_summ).mark_bar(color='#FFC107').encode(
                            x=alt.X('Location', sort='-y', title='Lokasyon'), y='Qty On Hand',
                            tooltip=['Location', 'Qty On Hand']
                        ).properties(height=400)
                        st.altair_chart(chart_stok, use_container_width=True)

                with c_data:
                    st.markdown("##### 📝 Detaylı Stok Listesi")
                    # Sadece gerekli sütunlar, Expire Date (saatsiz) ile
                    display_cols = [c for c in df_stok.columns if
                                    c not in ['Expire', 'Expire_Obj', 'Days_To_Expire', 'Risk Durumu']]
                    # Expire Date'i öne alalım veya uygun yere
                    if 'Expire Date' in display_cols:
                        cols = ['Item No', 'Location', 'Qty On Hand', 'Expire Date'] + [c for c in display_cols if
                                                                                        c not in ['Item No', 'Location',
                                                                                                  'Qty On Hand',
                                                                                                  'Expire Date']]
                        st.dataframe(df_stok[cols], use_container_width=True, hide_index=True)
                    else:
                        st.dataframe(df_stok, use_container_width=True, hide_index=True)
            else:
                st.warning("Veri yok.")

        # --- TAB 3, 4, 5 (STANDART) ---
        with tab3:
            if not df_venlo.empty:
                st.dataframe(df_venlo, use_container_width=True, hide_index=True)
            else:
                st.info("Veri yok.")

        with tab4:
            if not df_yolda.empty:
                st.dataframe(df_yolda, use_container_width=True, hide_index=True)
            else:
                st.info("Veri yok.")

        with tab5:
            if not df_out.empty:
                st.dataframe(df_out, use_container_width=True, hide_index=True,
                             column_config={
                                 "SS Coverage (W/O Consignment)": st.column_config.NumberColumn("SS Coverage",
                                                                                                format="%.1f%%")})
            else:
                st.success("Sorun yok.")

        # --- TAB 6: ALERT CENTER (EN SONDA) ---
        with tab_alert:
            st.markdown("#### ⚠️ Operasyonel Risk Paneli")

            count_red = df_stok[df_stok['Risk Durumu'] == "🔴 Kritik (<6 Ay)"].shape[0] if not df_stok.empty else 0
            count_orange = df_stok[df_stok['Risk Durumu'] == "🟠 Riskli (6-12 Ay)"].shape[0] if not df_stok.empty else 0
            count_out = len(df_out)

            ac1, ac2, ac3 = st.columns(3)
            with ac1:
                st.markdown(
                    f"""<div class="alert-card bg-red"><span class="alert-number">{count_red}</span><span class="alert-text">Ürün SKT Riski Taşıyor (<6 Ay)</span></div>""",
                    unsafe_allow_html=True)
            with ac2:
                st.markdown(
                    f"""<div class="alert-card bg-orange"><span class="alert-number">{count_orange}</span><span class="alert-text">Ürün Yakın Takipte (6-12 Ay)</span></div>""",
                    unsafe_allow_html=True)
            with ac3:
                st.markdown(
                    f"""<div class="alert-card bg-gray"><span class="alert-number">{count_out}</span><span class="alert-text">📉 Ürün Stock Out Durumunda</span></div>""",
                    unsafe_allow_html=True)

            st.markdown("---")
            st.markdown("##### 🕵️‍♂️ Risk Analiz Tablosu")

            if not df_stok.empty:
                df_sorted = df_stok.sort_values(by="Days_To_Expire", ascending=True)


                # Renklendirme
                def style_risk_rows(row):
                    val = str(row['Risk Durumu'])
                    if "🔴" in val:
                        return ['background-color: #ffebee; color: #b71c1c'] * len(row)
                    elif "🟠" in val:
                        return ['background-color: #fff3e0; color: #e65100'] * len(row)
                    elif "🟢" in val:
                        return ['background-color: #e8f5e9; color: #1b5e20'] * len(row)
                    return [''] * len(row)


                # Expire Date (Saatsiz) kullanıyoruz
                cols_to_show = ["Item No", "Location", "Qty On Hand", "Expire Date", "Risk Durumu"]
                final_df = df_sorted[cols_to_show] if set(cols_to_show).issubset(df_sorted.columns) else df_sorted

                st.dataframe(
                    final_df.style.apply(style_risk_rows, axis=1),
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("Veri yok.")

    except Exception as e:
        st.error(f"Bir hata oluştu: {e}")
else:
    st.info("👆 Lütfen Excel dosyasını yükleyin.")