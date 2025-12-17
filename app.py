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
            background-color: #ffffff !important; border: 1px solid #e0e0e0;
            border-left: 8px solid #FFC107 !important; padding: 15px; border-radius: 8px;
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

        /* İNDİRME BUTONU STİLİ */
        .stDownloadButton button {
            width: 100%; border: 1px solid #28a745; color: #28a745;
        }
        .stDownloadButton button:hover {
            background-color: #28a745; color: white;
        }
    </style>
""", unsafe_allow_html=True)


# --- EXCEL İNDİRME FONKSİYONU (TEK SAYFA) ---
def convert_df_single(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()


# --- EXCEL İNDİRME FONKSİYONU (TÜM RAPOR - MULTI SHEET) ---
def convert_full_report(dfs_dict):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        for sheet_name, df in dfs_dict.items():
            # Excel sheet isimleri 31 karakteri geçemez
            safe_name = sheet_name[:30]
            df.to_excel(writer, sheet_name=safe_name, index=False)
    return output.getvalue()


# --- YAN MENÜ ---
with st.sidebar:
    st.image(
        "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c2/Stryker_Corporation_logo.svg/2560px-Stryker_Corporation_logo.svg.png",
        width=150)
    st.header("📂 Veri Girişi")
    uploaded_file = st.file_uploader("Günlük Excel Dosyası", type=["xlsx"])

    # Filtreler İçin Yer Tutucu
    st.markdown("---")
    filter_placeholder = st.container()

    # İndirme Butonu İçin Yer Tutucu
    st.markdown("---")
    download_placeholder = st.container()

# --- ANA PROGRAM ---
if uploaded_file:
    try:
        xls = pd.read_excel(uploaded_file, sheet_name=None)
        sheets = {k.strip(): v for k, v in xls.items()}

        # --- 1. VERİ HAZIRLIĞI VE EŞLEŞTİRME ---
        target_col = 'SS Coverage (W/O Consignment)'
        today = datetime.datetime.now()

        # GENERAL
        df_gen = sheets.get("General", pd.DataFrame())
        if not df_gen.empty:
            df_gen.columns = df_gen.columns.str.strip()
            if 'Item No' in df_gen.columns: df_gen['Item No'] = df_gen['Item No'].astype(str).str.strip()
            if target_col in df_gen.columns:
                df_gen[target_col] = pd.to_numeric(df_gen[target_col], errors='coerce') * 100

        # FRANCHISE HARİTASI OLUŞTUR (Item No -> Franchise)
        item_franchise_map = {}
        if not df_gen.empty and 'Franchise Description' in df_gen.columns:
            temp_map = df_gen[['Item No', 'Franchise Description']].drop_duplicates(subset=['Item No'])
            item_franchise_map = dict(zip(temp_map['Item No'], temp_map['Franchise Description']))


        # DİĞER TABLOLARI OKU VE FRANCHISE EŞLEŞTİR

        # Helper: Eşleştirme Fonksiyonu
        def process_df(sheet_name, id_col, rename_to='Item No'):
            df = sheets.get(sheet_name, pd.DataFrame())
            if not df.empty:
                df.columns = df.columns.str.strip()
                if id_col in df.columns:
                    df.rename(columns={id_col: rename_to}, inplace=True)
                    df[rename_to] = df[rename_to].astype(str).str.strip()
                    # Franchise Eşleştirme
                    if 'Franchise Description' not in df.columns:
                        df['Franchise Description'] = df[rename_to].map(item_franchise_map)
            return df


        df_out = process_df("Stock Out", 'Item No')
        if not df_out.empty and target_col in df_out.columns:
            df_out[target_col] = pd.to_numeric(df_out[target_col], errors='coerce') * 100

        df_venlo = process_df("Venlo Orders", 'Item Code')
        df_yolda = process_df("Yoldaki İthalatlar", 'Ordered Item Number')

        df_stok = process_df("Stok", 'Item Number')
        if not df_stok.empty and 'Qty On Hand' in df_stok.columns:
            df_stok['Qty On Hand'] = pd.to_numeric(df_stok['Qty On Hand'], errors='coerce').fillna(0)

        # STOK: Risk Analizi Ekle
        if not df_stok.empty:
            if 'Expire' in df_stok.columns:
                df_stok['Expire_Obj'] = pd.to_datetime(df_stok['Expire'], errors='coerce')
                df_stok['Days_To_Expire'] = (df_stok['Expire_Obj'] - today).dt.days
                df_stok['Expire Date'] = df_stok['Expire_Obj'].dt.date


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

        # --- 2. FİLTRELEME (SIDEBAR) ---
        with filter_placeholder:
            st.header("🎯 Filtreler")

            # Franchise Multiselect
            all_franchises = sorted(list(set(item_franchise_map.values()))) if item_franchise_map else []
            # 'nan' değerleri temizle
            all_franchises = [x for x in all_franchises if str(x) != 'nan']

            selected_franchises = st.multiselect("İş Birimi (Franchise):", options=all_franchises, placeholder="Tümü")

            st.markdown("---")
            search_query = st.text_input("🔍 Global Arama:", placeholder="Herhangi bir veri...")


        # --- 3. FİLTRE MOTORU ---
        def apply_filters(df):
            if df.empty: return df
            temp_df = df.copy()

            # 1. Franchise Filtresi
            if selected_franchises and 'Franchise Description' in temp_df.columns:
                temp_df = temp_df[temp_df['Franchise Description'].isin(selected_franchises)]

            # 2. Arama Filtresi
            if search_query:
                mask = pd.Series([False] * len(temp_df))
                for col in temp_df.columns:
                    mask = mask | temp_df[col].astype(str).str.lower().str.contains(search_query.lower(), regex=False,
                                                                                    na=False)
                temp_df = temp_df[mask]

            return temp_df


        # Filtreleri Uygula
        f_gen = apply_filters(df_gen)
        f_stok = apply_filters(df_stok)
        f_venlo = apply_filters(df_venlo)
        f_yolda = apply_filters(df_yolda)
        f_out = apply_filters(df_out)

        # --- 4. İNDİRME BUTONU (SIDEBAR) ---
        with download_placeholder:
            if not f_stok.empty or not f_gen.empty:
                full_report_data = {
                    "General": f_gen,
                    "Stok Detay": f_stok,
                    "Venlo Orders": f_venlo,
                    "Yoldaki": f_yolda,
                    "Stock Out": f_out
                }
                full_excel = convert_full_report(full_report_data)
                st.download_button(
                    label="📊 Tüm Raporu İndir (Excel)",
                    data=full_excel,
                    file_name=f"Stok_Raporu_Full_{datetime.date.today()}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

        # --- 5. DASHBOARD GÖRÜNÜMÜ ---
        st.title("Stock Control Intelligence")

        if selected_franchises:
            st.info(f"📂 Filtre: **{', '.join(selected_franchises)}**")

        # KPI KARTLARI
        qty_hand = f_stok['Qty On Hand'].sum() if not f_stok.empty else 0
        qty_order = f_venlo['Ordered Qty Order UOM'].sum() if not f_venlo.empty else 0
        qty_ship = f_yolda['Qty Shipped'].sum() if not f_yolda.empty else 0

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("📦 Toplam Stok", f"{qty_hand:,.0f}")
        c2.metric("🌍 Bekleyen Sipariş", f"{qty_order:,.0f}")
        c3.metric("🚢 Yoldaki Ürün", f"{qty_ship:,.0f}")
        c4.metric("📊 Listelenen Kalem", f"{len(f_gen)}")

        st.markdown("###")

        # SEKMELER
        tab1, tab2, tab3, tab4, tab5, tab_alert = st.tabs([
            "📋 General", "📍 Stok (Depo)", "🌍 Venlo Orders", "🚚 Yoldaki İthalatlar", "🚨 Stock Out", "🔔 Alert Center"
        ])

        with tab1:  # General
            if not f_gen.empty:
                st.dataframe(f_gen, use_container_width=True, hide_index=True,
                             column_config={
                                 "SS Coverage (W/O Consignment)": st.column_config.NumberColumn("SS Coverage",
                                                                                                format="%.1f%%")})
            else:
                st.info("Veri yok.")

        with tab2:  # Stok
            if not f_stok.empty:
                c_chart, c_data = st.columns([1, 1])
                with c_chart:
                    if 'Location' in f_stok.columns:
                        loc_summ = f_stok.groupby('Location')['Qty On Hand'].sum().reset_index().sort_values(
                            'Qty On Hand', ascending=False).head(12)
                        st.markdown("##### 🏆 En Yoğun 12 Lokasyon")
                        chart_stok = alt.Chart(loc_summ).mark_bar(color='#FFC107').encode(
                            x=alt.X('Location', sort='-y', title='Lokasyon'), y='Qty On Hand',
                            tooltip=['Location', 'Qty On Hand']
                        ).properties(height=400)
                        st.altair_chart(chart_stok, use_container_width=True)
                with c_data:
                    st.markdown("##### 📝 Detaylı Stok Listesi")
                    hidden = ['Expire', 'Expire_Obj', 'Days_To_Expire', 'Risk Durumu', 'Franchise Description']
                    cols = [c for c in f_stok.columns if c not in hidden]
                    if 'Expire Date' in cols:
                        # Reorder to put Expire Date near Quantities
                        reordered = ['Item No', 'Location', 'Qty On Hand', 'Expire Date'] + [x for x in cols if
                                                                                             x not in ['Item No',
                                                                                                       'Location',
                                                                                                       'Qty On Hand',
                                                                                                       'Expire Date']]
                        st.dataframe(f_stok[reordered], use_container_width=True, hide_index=True)
                    else:
                        st.dataframe(f_stok[cols], use_container_width=True, hide_index=True)
            else:
                st.warning("Veri yok.")

        with tab3:  # Venlo
            if not f_venlo.empty:
                st.dataframe(f_venlo, use_container_width=True, hide_index=True)
            else:
                st.info("Veri yok.")

        with tab4:  # Yolda
            if not f_yolda.empty:
                st.dataframe(f_yolda, use_container_width=True, hide_index=True)
            else:
                st.info("Veri yok.")

        with tab5:  # Stock Out
            if not f_out.empty:
                st.dataframe(f_out, use_container_width=True, hide_index=True,
                             column_config={
                                 "SS Coverage (W/O Consignment)": st.column_config.NumberColumn("SS Coverage",
                                                                                                format="%.1f%%")})
            else:
                st.success("Sorun yok.")

        with tab_alert:  # Alert Center (Son)
            st.markdown("#### ⚠️ Operasyonel Risk Paneli")

            # Risk Sayıları (Filtrelenmiş veriden hesaplanır)
            red_risk = f_stok[f_stok['Risk Durumu'] == "🔴 Kritik (<6 Ay)"] if not f_stok.empty else pd.DataFrame()
            count_red = len(red_risk)
            count_orange = f_stok[f_stok['Risk Durumu'] == "🟠 Riskli (6-12 Ay)"].shape[0] if not f_stok.empty else 0
            count_out = len(f_out)

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

            c_table, c_down = st.columns([4, 1])
            with c_table:
                st.markdown("##### 🕵️‍♂️ Risk Analiz Tablosu")
            with c_down:
                if not red_risk.empty:
                    st.write("")
                    risk_excel = convert_df_single(
                        red_risk[['Item No', 'Location', 'Qty On Hand', 'Expire Date', 'Franchise Description']])
                    st.download_button("📥 Kritik Listeyi İndir", data=risk_excel, file_name="Kritik_Riskler.xlsx",
                                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

            if not f_stok.empty:
                df_sorted = f_stok.sort_values(by="Days_To_Expire", ascending=True)


                def style_rows(row):
                    val = str(row['Risk Durumu'])
                    if "🔴" in val:
                        return ['background-color: #ffebee; color: #b71c1c'] * len(row)
                    elif "🟠" in val:
                        return ['background-color: #fff3e0; color: #e65100'] * len(row)
                    elif "🟢" in val:
                        return ['background-color: #e8f5e9; color: #1b5e20'] * len(row)
                    return [''] * len(row)


                show_cols = ["Item No", "Location", "Qty On Hand", "Expire Date", "Risk Durumu",
                             "Franchise Description"]
                valid = [c for c in show_cols if c in df_sorted.columns]
                st.dataframe(df_sorted[valid].style.apply(style_rows, axis=1), use_container_width=True,
                             hide_index=True)
            else:
                st.info("Risk verisi yok.")

    except Exception as e:
        st.error(f"Hata: {e}")
else:
    st.info("👆 Lütfen Excel dosyasını yükleyin.")