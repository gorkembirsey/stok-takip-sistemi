import streamlit as st
import pandas as pd
import altair as alt
from io import BytesIO
import datetime
import os

# --- SAYFA YAPILANDIRMASI ---
st.set_page_config(page_title="Stock Control Intelligence", layout="wide", page_icon="🧠")

# --- SABİT DOSYA YOLU ---
DATA_FILE_PATH = "master_stryker_data.xlsx"

# --- CSS AYARLARI ---
st.markdown("""
    <style>
        .stApp {background-color: #F4F6F9;}
        .alert-card {padding: 20px; border-radius: 10px; color: white; font-weight: bold; box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-bottom: 20px; text-align: center;}
        .bg-red {background-color: #d32f2f; border-left: 10px solid #b71c1c;}
        .bg-orange {background-color: #f57c00; border-left: 10px solid #e65100;}
        .bg-gray {background-color: #616161; border-left: 10px solid #212121;}
        .alert-number {font-size: 32px; display: block;}
        .alert-text {font-size: 16px; opacity: 0.9;}
        div[data-testid="stMetric"] {background-color: #ffffff !important; border: 1px solid #e0e0e0; border-left: 8px solid #FFC107 !important; padding: 15px; border-radius: 8px;}
        thead th {background-color: #f0f2f6 !important; color: #31333F !important; font-size: 14px !important; font-weight: 600 !important; border-bottom: 2px solid #e0e0e0 !important;}
        tbody tr:nth-of-type(even) {background-color: #f9f9f9;}
        .stTabs [data-baseweb="tab-list"] {gap: 8px;}
        .stTabs [data-baseweb="tab"] {height: 45px; background-color: white; border-radius: 4px; font-weight: 600; border: 1px solid #ddd;}
        .stTabs [aria-selected="true"] {background-color: #fff !important; color: #000 !important; border-bottom: 4px solid #FFC107 !important;}
        .stDownloadButton button {width: 100%; border: 1px solid #28a745; color: #28a745;}
        .stDownloadButton button:hover {background-color: #28a745; color: white;}
    </style>
""", unsafe_allow_html=True)


# --- İNDİRME FONKSİYONLARI ---
def convert_df_single(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()


def convert_full_report(dfs_dict):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        for sheet_name, df in dfs_dict.items():
            safe_name = sheet_name[:30]
            df.to_excel(writer, sheet_name=safe_name, index=False)
    return output.getvalue()


# --- YAN MENÜ ---
with st.sidebar:
    st.image(
        "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c2/Stryker_Corporation_logo.svg/2560px-Stryker_Corporation_logo.svg.png",
        width=150)

    with st.expander("🔒 Yönetici Girişi"):
        password = st.text_input("Şifre", type="password")
        if password == "stryker2025":
            uploaded_file = st.file_uploader("Günlük Excel Dosyasını Yükle", type=["xlsx"])
            if uploaded_file is not None:
                with open(DATA_FILE_PATH, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                st.toast("✅ Veri güncellendi!", icon="💾")
                st.rerun()

    st.markdown("---")
    filter_placeholder = st.container()
    st.markdown("---")
    download_placeholder = st.container()

# --- DOSYA KONTROLÜ ---
if os.path.exists(DATA_FILE_PATH):
    current_file = DATA_FILE_PATH
    mod_time = datetime.datetime.fromtimestamp(os.path.getmtime(DATA_FILE_PATH)).strftime('%d.%m.%Y %H:%M')
    st.sidebar.caption(f"📅 Son Güncelleme: {mod_time}")
else:
    st.info("👋 Sistemde veri yok. Lütfen yönetici girişi yapıp dosya yükleyin.")
    st.stop()


# --- YARDIMCI: TARİH FORMATLAYICI (GG.AA.YYYY) ---
def format_turkish_date(df, columns):
    """Verilen sütunları GG.AA.YYYY formatına çevirir ve saati siler."""
    for col in columns:
        if col in df.columns:
            # Önce datetime objesine çevir (Hataları yoksay)
            df[col] = pd.to_datetime(df[col], errors='coerce')
            # Sonra istenen string formatına çevir (GG.AA.YYYY)
            df[col] = df[col].dt.strftime('%d.%m.%Y')
            # NaT (Hatalı tarih) olanları boş bırak veya tire koy
            df[col] = df[col].fillna('')
    return df


# --- ANA PROGRAM ---
if current_file:
    try:
        xls = pd.read_excel(current_file, sheet_name=None)
        sheets = {k.strip(): v for k, v in xls.items()}

        # --- VERİ HAZIRLIĞI ---
        target_col = 'SS Coverage (W/O Consignment)'
        today = datetime.datetime.now()

        # GENERAL
        df_gen = sheets.get("General", pd.DataFrame())
        if not df_gen.empty:
            df_gen.columns = df_gen.columns.str.strip()
            if 'Item No' in df_gen.columns: df_gen['Item No'] = df_gen['Item No'].astype(str).str.strip()
            if target_col in df_gen.columns:
                df_gen[target_col] = pd.to_numeric(df_gen[target_col], errors='coerce') * 100

        # MAPPING
        item_franchise_map = {}
        if not df_gen.empty and 'Franchise Description' in df_gen.columns:
            temp_map = df_gen[['Item No', 'Franchise Description']].drop_duplicates(subset=['Item No'])
            item_franchise_map = dict(zip(temp_map['Item No'], temp_map['Franchise Description']))


        # DİĞER TABLOLAR
        def process_df(sheet_name, id_col, rename_to='Item No'):
            df = sheets.get(sheet_name, pd.DataFrame())
            if not df.empty:
                df.columns = df.columns.str.strip()
                if id_col in df.columns:
                    df.rename(columns={id_col: rename_to}, inplace=True)
                    df[rename_to] = df[rename_to].astype(str).str.strip()
                    if 'Franchise Description' not in df.columns:
                        df['Franchise Description'] = df[rename_to].map(item_franchise_map)
            return df


        df_out = process_df("Stock Out", 'Item No')
        if not df_out.empty and target_col in df_out.columns:
            df_out[target_col] = pd.to_numeric(df_out[target_col], errors='coerce') * 100

        # --- VENLO (Tarih Formatlama Dahil) ---
        df_venlo = process_df("Venlo Orders", 'Item Code')
        # İstenen Tarih Sütunları
        venlo_date_cols = ['Line Creation Date', 'ETA', 'Request Date', 'Line Promise Date']
        df_venlo = format_turkish_date(df_venlo, venlo_date_cols)

        # --- YOLDAKİ (Tarih Formatlama Dahil) ---
        df_yolda = process_df("Yoldaki İthalatlar", 'Ordered Item Number')
        # İstenen Tarih Sütunları
        yolda_date_cols = ['Shipment Date', 'ETA']
        df_yolda = format_turkish_date(df_yolda, yolda_date_cols)

        # --- STOK (Tarih Formatlama Dahil) ---
        df_stok = process_df("Stok", 'Item Number')
        if not df_stok.empty:
            if 'Qty On Hand' in df_stok.columns:
                df_stok['Qty On Hand'] = pd.to_numeric(df_stok['Qty On Hand'], errors='coerce').fillna(0)

            # Risk Analizi ve Tarih Formatlama
            if 'Expire' in df_stok.columns:
                # Hesaplama için önce orijinal datetime tutuyoruz
                df_stok['Expire_Obj'] = pd.to_datetime(df_stok['Expire'], errors='coerce')
                df_stok['Days_To_Expire'] = (df_stok['Expire_Obj'] - today).dt.days

                # Görüntüleme için GG.AA.YYYY yapıyoruz
                df_stok['Expire Date'] = df_stok['Expire_Obj'].dt.strftime('%d.%m.%Y').fillna('')


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
                df_stok['Expire Date'] = ""

        # --- SIDEBAR FİLTRELERİ ---
        with filter_placeholder:
            st.header("🎯 Gelişmiş Filtreleme")

            all_franchises = sorted(list(set(item_franchise_map.values()))) if item_franchise_map else []
            all_franchises = [x for x in all_franchises if str(x) != 'nan']
            selected_franchises = st.multiselect("İş Birimi (Franchise):", options=all_franchises, placeholder="Tümü")

            st.markdown("---")
            st.markdown("#### ⚡ Çoklu Veri Seçimi")

            filterable_columns = ['Item No', 'Location', 'Customer PO', 'Order Number', 'Item Description',
                                  'Risk Durumu']
            selected_filter_col = st.selectbox("1. Kriter Seçin:", filterable_columns)

            unique_values = set()
            all_dfs = [df_gen, df_stok, df_venlo, df_yolda, df_out]
            for d in all_dfs:
                if not d.empty and selected_filter_col in d.columns:
                    unique_values.update(d[selected_filter_col].dropna().astype(str).unique())

            sorted_values = sorted(list(unique_values))
            selected_dynamic_values = st.multiselect(
                f"2. {selected_filter_col} Seçin/Yapıştırın:",
                options=sorted_values,
                placeholder="Çoklu seçim yapın..."
            )

            st.markdown("---")
            search_query = st.text_input("🔍 Global Arama:", placeholder="Herhangi bir veri...")


        # --- FİLTRE MOTORU ---
        def apply_filters(df):
            if df.empty: return df
            temp_df = df.copy()
            if selected_franchises and 'Franchise Description' in temp_df.columns:
                temp_df = temp_df[temp_df['Franchise Description'].isin(selected_franchises)]
            if selected_dynamic_values and selected_filter_col in temp_df.columns:
                temp_df = temp_df[temp_df[selected_filter_col].astype(str).isin(selected_dynamic_values)]
            if search_query:
                mask = pd.Series([False] * len(temp_df))
                for col in temp_df.columns:
                    mask = mask | temp_df[col].astype(str).str.lower().str.contains(search_query.lower(), regex=False,
                                                                                    na=False)
                temp_df = temp_df[mask]
            return temp_df


        f_gen = apply_filters(df_gen)
        f_stok = apply_filters(df_stok)
        f_venlo = apply_filters(df_venlo)
        f_yolda = apply_filters(df_yolda)
        f_out = apply_filters(df_out)

        # --- İNDİRME ---
        with download_placeholder:
            if not f_stok.empty or not f_gen.empty:
                full_report_data = {
                    "General": f_gen, "Stok Detay": f_stok, "Venlo Orders": f_venlo,
                    "Yoldaki": f_yolda, "Stock Out": f_out
                }
                full_excel = convert_full_report(full_report_data)
                st.download_button(
                    label="📊 Raporu İndir (Excel)",
                    data=full_excel,
                    file_name=f"Stryker_Rapor_{datetime.date.today()}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

        # --- DASHBOARD ---
        st.title("Stock Control Intelligence")

        filters_applied = []
        if selected_franchises: filters_applied.append(f"Franchise ({len(selected_franchises)})")
        if selected_dynamic_values: filters_applied.append(f"{selected_filter_col} ({len(selected_dynamic_values)})")
        if search_query: filters_applied.append(f"Arama: {search_query}")

        if filters_applied:
            st.info(f"📂 Aktif Filtreler: **{' + '.join(filters_applied)}**")

        # KPI
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
                st.dataframe(f_gen, use_container_width=True, hide_index=True, column_config={
                    "SS Coverage (W/O Consignment)": st.column_config.NumberColumn("SS Coverage", format="%.1f%%")})
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
                st.dataframe(f_out, use_container_width=True, hide_index=True, column_config={
                    "SS Coverage (W/O Consignment)": st.column_config.NumberColumn("SS Coverage", format="%.1f%%")})
            else:
                st.success("Sorun yok.")

        with tab_alert:  # Alert Center
            st.markdown("#### ⚠️ Operasyonel Risk Paneli")
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
        st.error(f"Sistem Hatası: {e}")