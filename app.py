import streamlit as st
import pandas as pd
import os
import altair as alt
from io import BytesIO
import datetime

# --- 1. SAYFA YAPILANDIRMASI ---
st.set_page_config(
    page_title="Inventory Intelligence",
    layout="wide",
    page_icon="📦",
    initial_sidebar_state="expanded"
)

# --- 2. CSS TASARIM ---
st.markdown("""
    <style>
        .stApp {background-color: #F5F7FA;}
        h1, h2, h3 {color: #2C3E50; font-family: 'Segoe UI', sans-serif;}
        [data-testid="stSidebar"] {background-color: #FFFFFF; box-shadow: 2px 0 5px rgba(0,0,0,0.05);}
        div[data-testid="stMetric"] {background-color: #FFFFFF; border: none; padding: 20px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);}
        .stTabs [data-baseweb="tab-list"] {gap: 10px; background-color: transparent;}
        .stTabs [data-baseweb="tab"] {height: 50px; background-color: #FFFFFF; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); border: 1px solid #E0E0E0; font-weight: 600;}
        .stTabs [aria-selected="true"] {background-color: #FFC107 !important; color: black !important; border: none;}
        div.stButton > button {width: 100%; border-radius: 6px; font-weight: 600; border: 1px solid #e0e0e0;}
        .export-btn button {background-color: #2ECC71 !important; color: white !important;}
    </style>
""", unsafe_allow_html=True)

# --- FONKSİYONLAR ---
def excel_olustur(df_input):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_input.to_excel(writer, index=False, sheet_name='Report')
    return output.getvalue()

# --- SKU INSPECTOR (POPUP) ---
@st.dialog("📦 SKU Inspector")
def show_sku_details(item_code, df_source, threshold_value, col_map):
    # col_map sözlüğü ile orijinal sütun isimlerine ulaşıyoruz
    c_item = col_map['item']
    c_loc = col_map['loc']
    c_qty = col_map['qty']
    c_lot = col_map['lot']

    item_data = df_source[df_source[c_item] == item_code].copy()
    
    if not item_data.empty:
        if c_lot not in item_data.columns: item_data[c_lot] = "-" 
        
        total_stock = item_data[c_qty].sum()
        unique_lots = item_data[c_lot].unique()
        lot_info = unique_lots[0] if len(unique_lots) == 1 else "Karışık (Listeye bkz.)"

        c1, c2, c3 = st.columns(3)
        c1.metric("Mevcut Stok", f"{total_stock:,.0f}")
        c2.metric("Min. Stok Seviyesi", f"{threshold_value}")
        c3.metric("Lot Bilgisi", f"{lot_info}")
        
        st.markdown("---")
        st.write(f"**Stock Distribution for {item_code}:**")
        
        # Tablo Görünümü
        item_data["Min_Level"] = threshold_value
        
        # Sadece seçilen sütunları göster
        display_cols = [c_loc, c_qty, "Min_Level", c_lot]
        display_df = item_data[display_cols].copy()
        
        # Başlıkları standartlaştırarak göster (Kullanıcı için daha anlaşılır)
        display_df.columns = ["Lokasyon", "Miktar", "Min. Seviye", "Lot"]
        
        st.dataframe(display_df, hide_index=True, use_container_width=True)
        st.caption(f"Data retrieved at {datetime.datetime.now().strftime('%H:%M:%S')}")
    else:
        st.error("Item details not found.")

# --- SIDEBAR & VERİ YÜKLEME ---
if 'selected_locs' not in st.session_state: st.session_state['selected_locs'] = []
if 'selected_items' not in st.session_state: st.session_state['selected_items'] = []

with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/c/c2/Stryker_Corporation_logo.svg/2560px-Stryker_Corporation_logo.svg.png", width=150)
    st.markdown("### Control Panel")
    
    with st.expander("📂 Data Upload", expanded=True):
        uploaded_file = st.file_uploader("Excel Dosyası Yükle", type=["xlsx"])
    
    df_raw = pd.DataFrame()
    if uploaded_file is not None:
        try:
            df_raw = pd.read_excel(uploaded_file)
        except Exception as e:
            st.error(f"Hata: {e}")
    elif os.path.exists('stok.xlsx'):
        df_raw = pd.read_excel('stok.xlsx')

    with st.expander("⚙️ System Settings", expanded=False):
        threshold = st.slider("🔴 Kritik Stok Limiti", 0, 100, 10)

# --- SÜTUN EŞLEŞTİRME (EN ÖNEMLİ KISIM) ---
df = pd.DataFrame()
column_mapping = {}

if not df_raw.empty:
    # Boşlukları temizle
    df_raw.columns = df_raw.columns.str.strip()
    columns = list(df_raw.columns)
    
    st.sidebar.markdown("---")
    st.sidebar.success("✅ Dosya Yüklendi! Lütfen sütunları eşleştirin:")
    
    with st.sidebar.expander("🔄 Sütun Eşleştirme (Mapping)", expanded=True):
        # Akıllı seçim (Default değerleri tahmin etmeye çalışıyoruz)
        idx_loc = next((i for i, c in enumerate(columns) if "loc" in c.lower() or "yer" in c.lower() or "depo" in c.lower()), 0)
        idx_qty = next((i for i, c in enumerate(columns) if "qty" in c.lower() or "mik" in c.lower() or "adet" in c.lower() or "stok" in c.lower()), 1 if len(columns)>1 else 0)
        idx_sku = next((i for i, c in enumerate(columns) if "sku" in c.lower() or "kod" in c.lower() or "item" in c.lower() or "malzeme" in c.lower()), 2 if len(columns)>2 else 0)
        idx_lot = next((i for i, c in enumerate(columns) if "lot" in c.lower() or "batch" in c.lower() or "parti" in c.lower()), 0)

        col_loc = st.selectbox("📍 Lokasyon Sütunu:", columns, index=idx_loc)
        col_qty = st.selectbox("📦 Miktar (Adet) Sütunu:", columns, index=idx_qty)
        col_sku = st.selectbox("🏷️ Ürün Kodu (SKU) Sütunu:", columns, index=idx_sku)
        
        has_lot = st.checkbox("Lot / Batch Bilgisi Var mı?", value=("lot" in [c.lower() for c in columns]))
        col_lot = None
        if has_lot:
            col_lot = st.selectbox("🔢 Lot Sütunu:", columns, index=idx_lot)
        
        # Seçimleri Kaydet
        column_mapping = {
            'loc': col_loc,
            'qty': col_qty,
            'item': col_sku,
            'lot': col_lot if has_lot else 'Sanal_Lot'
        }

    # --- VERİ HAZIRLIĞI ---
    df = df_raw.copy()
    
    # Veri tiplerini ayarla
    df[col_loc] = df[col_loc].astype(str)
    df[col_sku] = df[col_sku].astype(str)
    df[col_qty] = pd.to_numeric(df[col_qty], errors='coerce').fillna(0)
    
    if has_lot and col_lot:
        df[col_lot] = df[col_lot].astype(str)
    else:
        df['Sanal_Lot'] = "-" # Lot yoksa sanal oluştur
    
    # Status
    df["Status"] = df[col_qty].apply(lambda x: "🔴 Critical" if x <= threshold else "🟢 Healthy")

# --- HEADER ---
col_title, col_actions = st.columns([6, 1.5])
with col_title:
    st.title("Inventory Intelligence")

with col_actions:
    if not df.empty:
        st.markdown('<div class="export-btn">', unsafe_allow_html=True)
        excel_data = excel_olustur(df)
        st.download_button(
            label="📥 Export All Data",
            data=excel_data,
            file_name=f"Inventory_Report_{datetime.date.today()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
        st.markdown('</div>', unsafe_allow_html=True)

st.markdown("---")

# --- ANA PROGRAM ---
if not df.empty:
    # Değişken İsimlerini Kolaylaştırma
    c_loc = column_mapping['loc']
    c_qty = column_mapping['qty']
    c_item = column_mapping['item']
    
    with st.sidebar.expander("🔍 Akıllı Filtreler", expanded=True):
        st.markdown(f"**📍 Filtre: {c_loc}**")
        tum_lokasyonlar = sorted(list(df[c_loc].unique()))
        
        c1, c2 = st.columns([1, 1])
        if c1.button("Tümünü Seç", key="loc_all"):
            st.session_state['selected_locs'] = tum_lokasyonlar
            st.rerun()
        if c2.button("Temizle", key="loc_clear"):
            st.session_state['selected_locs'] = []
            st.rerun()
            
        secilen_yerler = st.multiselect("Lokasyon Seç:", tum_lokasyonlar, default=st.session_state['selected_locs'], label_visibility="collapsed", key='loc_multiselect')
        
        if secilen_yerler:
            mevcut_urunler = df[df[c_loc].isin(secilen_yerler)][c_item].unique()
        else:
            mevcut_urunler = df[c_item].unique()
        
        st.markdown("---")
        st.markdown(f"**🏷️ Filtre: {c_item}**")
        
        c3, c4 = st.columns([1, 1])
        if c3.button("Tümünü Seç", key="item_all"):
            st.session_state['selected_items'] = sorted(list(mevcut_urunler))
            st.rerun()
        if c4.button("Temizle", key="item_clear"):
            st.session_state['selected_items'] = []
            st.rerun()
            
        valid_defaults = [x for x in st.session_state['selected_items'] if x in mevcut_urunler]
        secilen_urunler = st.multiselect("Ürün Seç:", sorted(list(mevcut_urunler)), default=valid_defaults, label_visibility="collapsed", key='item_multiselect')
        
        st.markdown("---")
        search_term = st.text_input("Deep Search", placeholder="Ara...", help="Kod veya Lokasyon ara")

    # Filtreleme
    df_filtered = df.copy()
    if secilen_yerler: df_filtered = df_filtered[df_filtered[c_loc].isin(secilen_yerler)]
    if secilen_urunler: df_filtered = df_filtered[df_filtered[c_item].isin(secilen_urunler)]
    if search_term:
        df_filtered = df_filtered[
            df_filtered[c_item].str.contains(search_term, case=False, na=False) |
            df_filtered[c_loc].str.contains(search_term, case=False, na=False)
        ]

    if not df_filtered.empty:
        tab1, tab2 = st.tabs(["📊 Executive Dashboard", "📋 Master Data List"])

        with tab1:
            total_qty = df_filtered[c_qty].sum()
            total_sku = df_filtered[c_item].nunique()
            total_loc = df_filtered[c_loc].nunique()
            critical_count = df_filtered[df_filtered[c_qty] <= threshold].shape[0]

            k1, k2, k3, k4 = st.columns(4)
            k1.metric("📦 Total Stock", f"{total_qty:,.0f}")
            k2.metric("🏷️ Unique SKUs", f"{total_sku}")
            k3.metric("📍 Locations", f"{total_loc}")
            k4.metric("🚨 Critical Items", f"{critical_count}", delta="-Action Needed" if critical_count > 0 else "OK", delta_color="inverse")
            
            st.markdown("###")
            st.markdown(f"##### 📈 Top 15 Locations by Volume ({c_loc})")
            
            # Dinamik Grafik
            chart_data = df_filtered.groupby(c_loc)[c_qty].sum().reset_index().nlargest(15, c_qty)
            bar_chart = alt.Chart(chart_data).mark_bar(cornerRadius=5, color="#FFC107").encode(
                x=alt.X(c_loc, sort='-y', title=None), 
                y=alt.Y(c_qty, title='Quantity'), 
                tooltip=[c_loc, c_qty]
            ).properties(height=350)
            st.altair_chart(bar_chart, use_container_width=True)

        with tab2:
            st.markdown("### Detailed Inventory Report")
            col_sel, col_btn = st.columns([3, 1])
            with col_sel:
                item_to_inspect = st.selectbox("🔍 Inspect Specific SKU details:", ["Select an SKU..."] + sorted(list(df_filtered[c_item].unique())))
            with col_btn:
                st.write("") 
                st.write("")
                if st.button("Open Details", use_container_width=True):
                    if item_to_inspect != "Select an SKU...":
                        # Mapping bilgisini de gönderiyoruz
                        show_sku_details(item_to_inspect, df, threshold, column_mapping)
                    else:
                        st.warning("Please select an SKU first.")
            
            max_stok = int(df[c_qty].max()) if not df.empty else 100
            
            # Dataframe gösterimi (Dinamik sütun isimleriyle)
            st.dataframe(
                df_filtered,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Status": st.column_config.TextColumn("Status", width="small"),
                    c_loc: st.column_config.TextColumn("Location"),
                    c_item: st.column_config.TextColumn("Item Code"),
                    c_qty: st.column_config.ProgressColumn("On Hand", format="%d", min_value=0, max_value=max_stok),
                }
            )
    else:
        st.warning("⚠️ Sonuç bulunamadı.")
else:
    st.info("👋 Hoşgeldiniz. Lütfen Excel dosyanızı yükleyin ve sol menüden sütunları eşleştirin.")