import streamlit as st
import pandas as pd
import altair as alt
from io import BytesIO
import datetime
import os
import time

# --- SAYFA YAPILANDIRMASI ---
st.set_page_config(page_title="Stock Control Intelligence", layout="wide", page_icon="🧠")

DATA_FILE_PATH = "master_stryker_data.xlsx"

# --- CSS (RENKLİ BUTONLAR VE TABLO DÜZENİ) ---
st.markdown("""
    <style>
        .stApp {background-color: #F4F6F9;}

        /* 1. KPI KARTLARI (BEYAZ KUTU + SARI ŞERİT) */
        div[data-testid="stMetric"] {
            background-color: #ffffff !important; 
            border: 1px solid #e0e0e0 !important; 
            border-left: 8px solid #FFC107 !important; 
            padding: 15px !important; 
            border-radius: 8px !important;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05) !important;
        }
        div[data-testid="stMetric"] label { color: #444 !important; font-weight: 600 !important; }
        div[data-testid="stMetric"] div[data-testid="stMetricValue"] { color: #000 !important; font-weight: 700 !important; }

        /* 2. ALERT CENTER BUTONLARI (AGRESİF RENKLENDİRME) */

        /* KIRMIZI BUTON */
        div[data-testid="column"]:nth-of-type(1) .stButton button {
            background-color: #d32f2f !important;
            color: white !important;
            border: none !important;
            border-left: 10px solid #b71c1c !important;
            border-radius: 8px !important;
            height: 100px !important;
            box-shadow: 0 4px 6px rgba(0,0,0,0.2) !important;
        }
        div[data-testid="column"]:nth-of-type(1) .stButton button:hover {
            background-color: #c62828 !important; transform: scale(1.02);
        }
        div[data-testid="column"]:nth-of-type(1) .stButton button p {
            color: white !important; font-size: 24px !important; font-weight: 800 !important;
        }

        /* TURUNCU BUTON */
        div[data-testid="column"]:nth-of-type(2) .stButton button {
            background-color: #f57c00 !important;
            color: white !important;
            border: none !important;
            border-left: 10px solid #e65100 !important;
            border-radius: 8px !important;
            height: 100px !important;
            box-shadow: 0 4px 6px rgba(0,0,0,0.2) !important;
        }
        div[data-testid="column"]:nth-of-type(2) .stButton button:hover {
            background-color: #ef6c00 !important; transform: scale(1.02);
        }
        div[data-testid="column"]:nth-of-type(2) .stButton button p {
            color: white !important; font-size: 24px !important; font-weight: 800 !important;
        }

        /* GRİ BUTON */
        div[data-testid="column"]:nth-of-type(3) .stButton button {
            background-color: #616161 !important;
            color: white !important;
            border: none !important;
            border-left: 10px solid #212121 !important;
            border-radius: 8px !important;
            height: 100px !important;
            box-shadow: 0 4px 6px rgba(0,0,0,0.2) !important;
        }
        div[data-testid="column"]:nth-of-type(3) .stButton button:hover {
            background-color: #424242 !important; transform: scale(1.02);
        }
        div[data-testid="column"]:nth-of-type(3) .stButton button p {
            color: white !important; font-size: 24px !important; font-weight: 800 !important;
        }

        /* 3. DİĞER AYARLAR */
        thead th {background-color: #f0f2f6 !important; color: #31333F !important; font-size: 14px !important;}
        .stTabs [aria-selected="true"] {border-bottom: 3px solid #FFC107 !important;}

        /* İndirme Butonu (Küçük Yeşil) */
        .stDownloadButton button {
            border: 1px solid #28a745 !important; 
            color: #28a745 !important; 
            background-color: white !important;
            font-size: 14px !important;
            padding: 5px 15px !important;
            height: auto !important;
        }
        div[data-testid="stForm"] button {background-color: #FFC107 !important; color: black !important; border: none !important;}
    </style>
""", unsafe_allow_html=True)

if 'alert_filter_state' not in st.session_state:
    st.session_state.alert_filter_state = 'all'


# --- VERİ İŞLEME ---
@st.cache_data(show_spinner=False)
def load_and_process_data(file_path, mtime):
    try:
        xls = pd.read_excel(file_path, sheet_name=None)
        sheets = {k.strip(): v for k, v in xls.items()}
        today = datetime.datetime.now()

        def clean_df(df):
            if df.empty: return df
            df.columns = df.columns.str.strip()
            cols_map = {}
            for c in df.columns:
                if c in ['Item Number', 'Material', 'Item Code', 'Ordered Item Number']:
                    cols_map[c] = 'Item No'
            if cols_map: df.rename(columns=cols_map, inplace=True)
            if 'Item No' in df.columns: df['Item No'] = df['Item No'].astype(str).str.strip()
            return df

        def date_fmt(df, cols):
            for col in cols:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col], errors='coerce')
                    df[col] = df[col].dt.strftime('%d.%m.%Y').fillna('')
            return df

        # --- SEKMELER ---
        df_gen = sheets.get("General", pd.DataFrame())
        df_gen = clean_df(df_gen)

        item_franchise_map = {}
        if not df_gen.empty and 'Franchise Description' in df_gen.columns and 'Item No' in df_gen.columns:
            temp_map = df_gen[['Item No', 'Franchise Description']].drop_duplicates(subset=['Item No'])
            item_franchise_map = dict(zip(temp_map['Item No'], temp_map['Franchise Description']))

        df_out = sheets.get("Stock Out", pd.DataFrame())
        df_out = clean_df(df_out)
        if not df_out.empty:
            if 'Franchise Description' not in df_out.columns and 'Item No' in df_out.columns:
                df_out['Franchise Description'] = df_out['Item No'].map(item_franchise_map)

        df_venlo = sheets.get("Venlo Orders", pd.DataFrame())
        df_venlo = clean_df(df_venlo)
        if not df_venlo.empty:
            if 'Franchise Description' not in df_venlo.columns and 'Item No' in df_venlo.columns:
                df_venlo['Franchise Description'] = df_venlo['Item No'].map(item_franchise_map)
            df_venlo = date_fmt(df_venlo, ['Line Creation Date', 'ETA', 'Request Date', 'Line Promise Date'])

        df_yolda = sheets.get("Yoldaki İthalatlar", pd.DataFrame())
        df_yolda = clean_df(df_yolda)
        if not df_yolda.empty:
            if 'Franchise Description' not in df_yolda.columns and 'Item No' in df_yolda.columns:
                df_yolda['Franchise Description'] = df_yolda['Item No'].map(item_franchise_map)
            df_yolda = date_fmt(df_yolda, ['Shipment Date', 'ETA'])

        df_konsinye = sheets.get("Konsinye Stok Raporu", pd.DataFrame())
        df_konsinye = clean_df(df_konsinye)
        if not df_konsinye.empty:
            if 'Franchise Description' not in df_konsinye.columns and 'Item No' in df_konsinye.columns:
                df_konsinye['Franchise Description'] = df_konsinye['Item No'].map(item_franchise_map)
            if 'Expire Date' in df_konsinye.columns:
                df_konsinye['Expire Date'] = pd.to_datetime(df_konsinye['Expire Date'], errors='coerce').dt.strftime(
                    '%d.%m.%Y').fillna('')

        df_stok = sheets.get("Stok", pd.DataFrame())
        df_stok = clean_df(df_stok)
        if not df_stok.empty:
            if 'Franchise Description' not in df_stok.columns and 'Item No' in df_stok.columns:
                df_stok['Franchise Description'] = df_stok['Item No'].map(item_franchise_map)

            # ADET (Sayıya çevir, 0'la doldur)
            if 'Qty On Hand' in df_stok.columns:
                df_stok['Qty On Hand'] = pd.to_numeric(df_stok['Qty On Hand'], errors='coerce').fillna(0)

            # SITE (Tam sayı yap, stringe çevir, .0 at)
            if 'Site' in df_stok.columns:
                df_stok['Site'] = pd.to_numeric(df_stok['Site'], errors='coerce').fillna(0).astype(int).astype(
                    str).replace('0', '')

            if 'Expire' in df_stok.columns:
                df_stok['Expire_Obj'] = pd.to_datetime(df_stok['Expire'], errors='coerce')
                df_stok['Days_To_Expire'] = (df_stok['Expire_Obj'] - today).dt.days
                df_stok['Expire Date'] = df_stok['Expire_Obj'].dt.strftime('%d.%m.%Y').fillna('')

                def calc_risk(d):
                    if pd.isna(d): return "⚪ Bilinmiyor"
                    if d < 180:
                        return "🔴 Kritik (<6 Ay)"
                    elif d < 365:
                        return "🟠 Riskli (6-12 Ay)"
                    elif d >= 365:
                        return "🟢 Güvenli (>12 Ay)"
                    return "⚪ Bilinmiyor"

                df_stok['Risk Durumu'] = df_stok['Days_To_Expire'].apply(calc_risk)
            else:
                df_stok['Risk Durumu'] = "⚪ Tarih Yok"
                df_stok['Expire Date'] = ""

        all_franchises = sorted([x for x in list(set(item_franchise_map.values())) if str(x) != 'nan'])

        return {
            "General": df_gen, "Stok": df_stok, "Venlo": df_venlo,
            "Yolda": df_yolda, "Out": df_out, "Konsinye": df_konsinye,
            "Franchises": all_franchises
        }

    except Exception as e:
        return None


# --- İNDİRME ---
def convert_full_report(dfs_dict):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        for sheet_name, df in dfs_dict.items():
            if isinstance(df, pd.DataFrame) and not df.empty:
                cols_drop = ['Expire_Obj', 'Days_To_Expire', 'Expire']
                temp_df = df.drop(columns=[c for c in cols_drop if c in df.columns], errors='ignore')
                temp_df.to_excel(writer, sheet_name=sheet_name[:30], index=False)
    return output.getvalue()


def convert_df_single(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        cols_drop = ['Expire_Obj', 'Days_To_Expire', 'Expire']
        temp_df = df.drop(columns=[c for c in cols_drop if c in df.columns], errors='ignore')
        temp_df.to_excel(writer, index=False)
    return output.getvalue()


def reset_filters():
    st.session_state.franchise_key = []
    st.session_state.dynamic_val_key = []
    st.session_state.search_key = ""
    st.session_state.alert_filter_state = 'all'


# --- YAN MENÜ ---
with st.sidebar:
    st.image(
        "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c2/Stryker_Corporation_logo.svg/2560px-Stryker_Corporation_logo.svg.png",
        width=150)
    with st.expander("🔒 Yönetici Girişi"):
        password = st.text_input("Şifre", type="password")
        if password == "stryker2025":
            uploaded_file = st.file_uploader("Dosya Yükle", type=["xlsx"])
            if uploaded_file is not None:
                with open(DATA_FILE_PATH, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                    f.flush()
                    os.fsync(f.fileno())
                load_and_process_data.clear()
                st.toast("Veri Başarıyla Güncellendi!")
                time.sleep(1)
                st.rerun()
    st.markdown("---")

# --- VERİ YÜKLEME ---
processed_data = {}
if os.path.exists(DATA_FILE_PATH):
    mtime = os.path.getmtime(DATA_FILE_PATH)
    mod_time = datetime.datetime.fromtimestamp(mtime).strftime('%d.%m.%Y %H:%M')
    st.sidebar.caption(f"📅 Veri Tarihi: {mod_time}")

    data_bundle = load_and_process_data(DATA_FILE_PATH, mtime)
    if data_bundle is None:
        st.error("⚠️ Dosya okunamadı. Lütfen yönetici panelinden dosyayı tekrar yükleyin.")
        st.stop()
    else:
        processed_data = data_bundle
else:
    st.info("👋 Sistemde veri yok. Lütfen yönetici girişi yapıp dosya yükleyin.")
    st.stop()

df_gen = processed_data["General"]
df_stok = processed_data["Stok"]
df_venlo = processed_data["Venlo"]
df_yolda = processed_data["Yolda"]
df_out = processed_data["Out"]
df_konsinye = processed_data["Konsinye"]
all_franchises = processed_data["Franchises"]

# --- FİLTRE PANELİ ---
st.sidebar.header("🎯 Filtre Paneli")
st.sidebar.button("Filtreleri Temizle", on_click=reset_filters, type="secondary")

with st.sidebar.form("filter_form"):
    selected_franchises = st.multiselect("İş Birimi (Franchise):", options=all_franchises, placeholder="Tümü",
                                         key="franchise_key")
    st.markdown("---")
    filterable_columns = ['Item No', 'Location', 'Customer PO', 'Order Number', 'Item Description', 'Risk Durumu',
                          'Site']
    selected_filter_col = st.selectbox("1. Kriter Seçin:", filterable_columns)
    unique_values = set()
    for d in [df_gen, df_stok, df_venlo, df_yolda, df_out, df_konsinye]:
        if not d.empty and selected_filter_col in d.columns:
            unique_values.update(d[selected_filter_col].dropna().astype(str).unique())
    selected_dynamic_values = st.multiselect(f"2. {selected_filter_col} Değerleri:",
                                             options=sorted(list(unique_values)), placeholder="Çoklu seçim yapın...",
                                             key="dynamic_val_key")
    st.markdown("---")
    search_query = st.text_input("🔍 Global Arama:", placeholder="Herhangi bir veri...", key="search_key")
    submitted = st.form_submit_button("🚀 FİLTRELERİ UYGULA")


def fast_filter(df):
    if df.empty: return df
    mask = pd.Series(True, index=df.index)
    if selected_franchises and 'Franchise Description' in df.columns:
        mask &= df['Franchise Description'].isin(selected_franchises)
    if selected_dynamic_values and selected_filter_col in df.columns:
        mask &= df[selected_filter_col].astype(str).isin(selected_dynamic_values)
    if search_query:
        str_cols = df.select_dtypes(include=['object', 'string']).columns
        if len(str_cols) > 0:
            search_mask = df[str_cols].apply(
                lambda x: x.astype(str).str.contains(search_query, case=False, na=False)).any(axis=1)
            mask &= search_mask
    return df[mask]


f_gen = fast_filter(df_gen)
f_stok = fast_filter(df_stok)
f_venlo = fast_filter(df_venlo)
f_yolda = fast_filter(df_yolda)
f_out = fast_filter(df_out)
f_konsinye = fast_filter(df_konsinye)

st.sidebar.markdown("---")
if not f_stok.empty or not f_gen.empty:
    full_data = {"General": f_gen, "Stok": f_stok, "Venlo": f_venlo, "Yolda": f_yolda, "Stock Out": f_out,
                 "Konsinye": f_konsinye}
    st.sidebar.download_button("📊 Tüm Raporu İndir", data=convert_full_report(full_data),
                               file_name=f"Rapor_{datetime.date.today()}.xlsx")

# --- DASHBOARD ---
st.title("Stock Control Intelligence")
if submitted: st.info("✅ Filtreler Uygulandı")

c1, c2, c3, c4 = st.columns(4)
c1.metric("📦 Toplam Stok", f"{f_stok['Qty On Hand'].sum() if not f_stok.empty else 0:,.0f}")
c2.metric("🌍 Bekleyen Sipariş", f"{f_venlo['Ordered Qty Order UOM'].sum() if not f_venlo.empty else 0:,.0f}")
c3.metric("🚢 Yoldaki Ürün", f"{f_yolda['Qty Shipped'].sum() if not f_yolda.empty else 0:,.0f}")
c4.metric("📊 Listelenen Kalem", f"{len(f_gen)}")

st.markdown("###")

tab1, tab2, tab3, tab4, tab5, tab6, tab_alert = st.tabs([
    "📋 General", "📍 Stok (Depo)", "🌍 Venlo Orders", "🚚 Yoldaki İthalatlar", "🚨 Stock Out", "💼 Konsinye Stok",
    "🔔 Alert Center"
])

# 1. GENERAL
with tab1:
    if not f_gen.empty:
        st.dataframe(f_gen, use_container_width=True, hide_index=True,
                     column_config={"SS Coverage (W/O Consignment)": st.column_config.NumberColumn(format="%.1f%%")})
    else:
        st.info("Veri yok.")

# 2. STOK (Depo) - Temiz Liste
with tab2:
    if not f_stok.empty:
        c1, c2 = st.columns([1, 1])
        with c1:
            if 'Location' in f_stok.columns:
                loc_summ = f_stok.groupby('Location')['Qty On Hand'].sum().reset_index().sort_values('Qty On Hand',
                                                                                                     ascending=False).head(
                    12)
                chart = alt.Chart(loc_summ).mark_bar(color='#FFC107').encode(x=alt.X('Location', sort='-y'),
                                                                             y='Qty On Hand').properties(height=400)
                st.altair_chart(chart, use_container_width=True)
        with c2:
            st.markdown("##### 📝 Detaylı Stok Listesi")
            cols_hide = ['Risk Durumu', 'Expire', 'Expire_Obj', 'Days_To_Expire', 'Franchise Description']
            cols_show = [c for c in f_stok.columns if c not in cols_hide]
            # Adet Tam Sayı
            st.dataframe(f_stok[cols_show].style.format({"Qty On Hand": "{:.0f}"}), use_container_width=True,
                         hide_index=True)
    else:
        st.warning("Veri yok.")

with tab3:
    if not f_venlo.empty:
        st.dataframe(f_venlo, use_container_width=True, hide_index=True)
    else:
        st.info("Veri yok.")

with tab4:
    if not f_yolda.empty:
        st.dataframe(f_yolda, use_container_width=True, hide_index=True)
    else:
        st.info("Veri yok.")

# 5. STOCK OUT
with tab5:
    if not f_out.empty:
        st.dataframe(f_out, use_container_width=True, hide_index=True,
                     column_config={"SS Coverage (W/O Consignment)": st.column_config.NumberColumn(format="%.1f%%")})
    else:
        st.success("Sorun yok.")

# 6. KONSİNYE
with tab6:
    if not f_konsinye.empty:
        st.dataframe(f_konsinye, use_container_width=True, hide_index=True)
    else:
        st.info("Konsinye verisi yok.")

# 7. ALERT CENTER (SIRALAMA DÜZELTİLDİ + RENKLER)
with tab_alert:
    st.markdown("#### ⚠️ Operasyonel Risk Paneli")

    red_risk = f_stok[f_stok['Risk Durumu'] == "🔴 Kritik (<6 Ay)"] if not f_stok.empty else pd.DataFrame()
    orange_risk = f_stok[f_stok['Risk Durumu'] == "🟠 Riskli (6-12 Ay)"].shape[0] if not f_stok.empty else 0
    stock_out_count = len(f_out)


    def set_critical():
        st.session_state.alert_filter_state = 'critical' if st.session_state.alert_filter_state != 'critical' else 'all'


    def set_risky():
        st.session_state.alert_filter_state = 'risky' if st.session_state.alert_filter_state != 'risky' else 'all'


    def set_stockout():
        st.session_state.alert_filter_state = 'stockout' if st.session_state.alert_filter_state != 'stockout' else 'all'


    b1, b2, b3 = st.columns(3)
    label_red = f"Kritik Stok (<6 Ay)\n\n{len(red_risk)}"
    label_orange = f"Riskli Stok (6-12 Ay)\n\n{orange_risk}"
    label_gray = f"Stock Out\n\n{stock_out_count}"

    with b1:
        st.button(label_red, use_container_width=True, on_click=set_critical, key="btn_red")
    with b2:
        st.button(label_orange, use_container_width=True, on_click=set_risky, key="btn_orange")
    with b3:
        st.button(label_gray, use_container_width=True, on_click=set_stockout, key="btn_gray")

    st.markdown("---")

    current_filter = st.session_state.alert_filter_state
    display_df = pd.DataFrame()
    title_text = "Risk Analiz Tablosu"

    if current_filter == 'critical':
        display_df = red_risk
        title_text = "🔴 Kritik Stok Listesi (<6 Ay)"
    elif current_filter == 'risky':
        display_df = f_stok[f_stok['Risk Durumu'] == "🟠 Riskli (6-12 Ay)"]
        title_text = "🟠 Riskli Stok Listesi (6-12 Ay)"
    elif current_filter == 'stockout':
        display_df = f_out
        title_text = "📉 Stock Out Listesi"
    else:
        display_df = f_stok.sort_values("Days_To_Expire") if not f_stok.empty else pd.DataFrame()

    c_head, c_btn = st.columns([6, 1])
    c_head.markdown(f"##### {title_text}")
    if not display_df.empty:
        c_btn.download_button("📥 Raporu İndir", data=convert_df_single(display_df),
                              file_name=f"{current_filter}_Rapor.xlsx")

    if not display_df.empty:
        if current_filter == 'stockout':
            st.dataframe(display_df, use_container_width=True, hide_index=True,
                         column_config={
                             "SS Coverage (W/O Consignment)": st.column_config.NumberColumn(format="%.1f%%")})
        else:
            # GİZLENECEK SÜTUNLAR
            cols_hide = ['Expire', 'Expire_Obj', 'Days_To_Expire', 'Franchise Description']
            available_cols = [c for c in display_df.columns if c not in cols_hide]

            # --- İSTENEN SÜTUN SIRALAMASI ---
            # Item No, Qty On Hand, UM, Location, Lot/Serial Ref, Expire Date, Risk Durumu, Site
            desired_order = ['Item No', 'Qty On Hand', 'UM', 'Location', 'Lot/Serial Ref', 'Expire Date', 'Risk Durumu',
                             'Site']
            final_cols = [c for c in desired_order if c in available_cols] + [c for c in available_cols if
                                                                              c not in desired_order]
            final_df_view = display_df[final_cols]


            def style_rows(row):
                if 'Risk Durumu' in row:
                    val = str(row['Risk Durumu'])
                    if "🔴" in val:
                        return ['background-color: #ffebee; color: #b71c1c'] * len(row)
                    elif "🟠" in val:
                        return ['background-color: #fff3e0; color: #e65100'] * len(row)
                    elif "🟢" in val:
                        return ['background-color: #e8f5e9; color: #1b5e20'] * len(row)
                return [''] * len(row)


            # Adet Tam Sayı
            st.dataframe(
                final_df_view.style.apply(style_rows, axis=1).format({"Qty On Hand": "{:.0f}"}),
                use_container_width=True,
                hide_index=True
            )
    else:
        if current_filter != 'all': st.warning("Bu kategoride veri bulunamadı.")