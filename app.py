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

# --- 2. CSS İLE TASARIM AYARLARI ---
st.markdown("""
    <style>
        .stApp {background-color: #F5F7FA;}
        h1, h2, h3 {color: #2C3E50; font-family: 'Segoe UI', sans-serif;}
        
        /* Sidebar */
        [data-testid="stSidebar"] {background-color: #FFFFFF; box-shadow: 2px 0 5px rgba(0,0,0,0.05);}
        
        /* Kartlar */
        div[data-testid="stMetric"] {
            background-color: #FFFFFF; border: none; padding: 20px;
            border-radius: 12px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        
        /* Tablar */
        .stTabs [data-baseweb="tab-list"] {gap: 10px; background-color: transparent;}
        .stTabs [data-baseweb="tab"] {
            height: 50px; background-color: #FFFFFF; border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05); border: 1px solid #E0E0E0; font-weight: 600;
        }
        .stTabs [aria-selected="true"] {background-color: #FFC107 !important; color: black !important; border: none;}
        
        /* Butonlar */
        div.stButton > button {
            width: 100%; border-radius: 6px; font-weight: 600; border: 1px solid #e0e0e0;
        }
        /* Sarı Buton (Select All vb.) */
        div.stButton > button:first-child {
            # background-color: #FFC107; color: black; border: none;
        }
        /* Özel 'Export' butonu için stil */
        .export-btn button {
            background-color: #2ECC71 !important; color: white !important;
        }
    </style>
""", unsafe_allow_html=True)

# --- FONKSİYONLAR ---
def excel_olustur(df_input):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_input.to_excel(writer, index=False, sheet_name='Report')
    return output.getvalue()

# --- YENİ ÖZELLİK: DETAY MODAL PENCERESİ (DIALOG) ---
@st.dialog("📦 SKU Inspector")
def show_sku_details(item_code, df_source):
    # Seçilen ürünün verilerini süz
    item_data = df_source[df_source["Item Code"] == item_code]
    
    if not item_data.empty:
        total_stock = item_data["Quantity"].sum()
        loc_count = item_data["Location"].nunique()
        locations = item_data["Location"].unique()
        abc_class = item_data.iloc[0]["ABC Class"] if "ABC Class" in item_data.columns else "N/A"
        
        # Üst Bilgi Kartları
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Stock", f"{total_stock:,.0f}")
        c2.metric("Locations", f"{loc_count}")
        c3.metric("ABC Class", f"{abc_class}")
        
        st.markdown("---")
        
        st.write(f"**Stock Distribution for {item_code}:**")
        # Basit bir tablo gösterimi
        st.dataframe(
            item_data[["Location", "Quantity", "Status"]],
            hide_index=True,
            use_container_width=True
        )
        
        st.markdown(f"*Data retrieved at {datetime.datetime.now().strftime('%H:%M:%S')}*")
    else:
        st.error("Item details not found.")

# --- SIDEBAR (VERİ YÜKLEME & FİLTRELER) ---
# Session State
if 'selected_locs' not in st.session_state: st.session_state['selected_locs'] = []
if 'selected_items' not in st.session_state: st.session_state['selected_items'] = []

with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/c/c2/Stryker_Corporation_logo.svg/2560px-Stryker_Corporation_logo.svg.png", width=150)
    st.markdown("### Control Panel")
    
    with st.expander("📂 Data Upload", expanded=True):
        uploaded_file = st.file_uploader("Drop Daily Excel", type=["xlsx"])
    
    df = pd.DataFrame()
    if uploaded_file is not None:
        df = pd.read_excel(uploaded_file)
    elif os.path.exists('stok.xlsx'):
        df = pd.read_excel('stok.xlsx')

    with st.expander("⚙️ System Settings", expanded=False):
        threshold = st.slider("🔴 Critical Stock Limit", 0, 100, 10)

# --- VERİ HAZIRLIĞI ---
if not df.empty:
    df.columns = df.columns.str.strip()
    # Veri Tipleme
    df["Location"] = df["Location"].astype(str)
    df["Item Code"] = df["Item Code"].astype(str)
    df["Quantity"] = pd.to_numeric(df["Quantity"], errors='coerce').fillna(0)
    
    # ABC ve Status Hesapla (Global olarak, modal için lazım)
    df_sorted = df.sort_values("Quantity", ascending=False)
    df_sorted["Cum_Sum"] = df_sorted["Quantity"].cumsum()
    df_sorted["Cum_Perc"] = 100 * df_sorted["Cum_Sum"] / df_sorted["Quantity"].sum()
    def get_class(x): return "A" if x <= 80 else "B" if x <= 95 else "C"
    df["ABC Class"] = df_sorted["Cum_Perc"].apply(get_class)
    df["Status"] = df["Quantity"].apply(lambda x: "🔴 Critical" if x <= threshold else "🟢 Healthy")

# --- HEADER & AKSİYON BUTONLARI (TOP BAR) ---
# Başlık ve Butonu yan yana koyuyoruz
col_title, col_actions = st.columns([6, 1.5]) # Oranları ayarlayabilirsin

with col_title:
    st.title("Inventory Intelligence")

with col_actions:
    if not df.empty:
        # Excel İndirme Butonu (En Tepeye Taşıdık)
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
    # --- SMART FILTERS (SIDEBAR) ---
    with st.sidebar.expander("🔍 Smart Filters", expanded=True):
        # 1. Lokasyon
        st.markdown("**📍 Filter by Location**")
        tum_lokasyonlar = sorted(list(df["Location"].unique()))
        c1, c2 = st.columns([1, 1])
        if c1.button("Select All", key="loc_all"):
            st.session_state['selected_locs'] = tum_lokasyonlar
            st.rerun()
        if c2.button("Clear", key="loc_clear"):
            st.session_state['selected_locs'] = []
            st.rerun()
        secilen_yerler = st.multiselect("Select Locations", tum_lokasyonlar, default=st.session_state['selected_locs'], label_visibility="collapsed", key='loc_multiselect')
        
        # Ürün Listesi Güncelleme
        if secilen_yerler:
            mevcut_urunler = df[df["Location"].isin(secilen_yerler)]["Item Code"].unique()
        else:
            mevcut_urunler = df["Item Code"].unique()
        
        st.markdown("---")
        
        # 2. Ürün
        st.markdown("**🏷️ Filter by Item Code**")
        c3, c4 = st.columns([1, 1])
        if c3.button("Select All", key="item_all"):
            st.session_state['selected_items'] = sorted(list(mevcut_urunler))
            st.rerun()
        if c4.button("Clear", key="item_clear"):
            st.session_state['selected_items'] = []
            st.rerun()
        
        valid_defaults = [x for x in st.session_state['selected_items'] if x in mevcut_urunler]
        secilen_urunler = st.multiselect("Select Items", sorted(list(mevcut_urunler)), default=valid_defaults, label_visibility="collapsed", key='item_multiselect')

        st.markdown("---")
        # 3. Arama
        search_term = st.text_input("Deep Search", placeholder="Type SKU or Location...", help="Global search")

    # --- FİLTRELEME UYGULA ---
    df_filtered = df.copy()
    if secilen_yerler: df_filtered = df_filtered[df_filtered["Location"].isin(secilen_yerler)]
    if secilen_urunler: df_filtered = df_filtered[df_filtered["Item Code"].isin(secilen_urunler)]
    if search_term:
        df_filtered = df_filtered[
            df_filtered["Item Code"].str.contains(search_term, case=False, na=False) |
            df_filtered["Location"].str.contains(search_term, case=False, na=False)
        ]

    # --- DASHBOARD İÇERİĞİ ---
    if not df_filtered.empty:
        
        tab1, tab2 = st.tabs(["📊 Executive Dashboard", "📋 Master Data List"])

        with tab1:
            # Metrics
            total_qty = df_filtered["Quantity"].sum()
            total_sku = df_filtered["Item Code"].nunique()
            total_loc = df_filtered["Location"].nunique()
            critical_count = df_filtered[df_filtered["Quantity"] <= threshold].shape[0]

            k1, k2, k3, k4 = st.columns(4)
            k1.metric("📦 Total Stock", f"{total_qty:,.0f}")
            k2.metric("🏷️ Unique SKUs", f"{total_sku}")
            k3.metric("📍 Locations", f"{total_loc}")
            k4.metric("🚨 Critical Items", f"{critical_count}", delta="-Action Needed" if critical_count > 0 else "OK", delta_color="inverse")
            
            st.markdown("###")

            # Charts
            c_chart1, c_chart2 = st.columns([2, 1])
            with c_chart1:
                st.markdown("##### 📈 Volume Analysis")
                chart_data = df_filtered.groupby("Location")["Quantity"].sum().reset_index().nlargest(15, "Quantity")
                bar_chart = alt.Chart(chart_data).mark_bar(cornerRadius=5, color="#FFC107").encode(
                    x=alt.X('Location', sort='-y', title=None), y=alt.Y('Quantity', title='Units'), tooltip=['Location', 'Quantity']
                ).properties(height=320)
                st.altair_chart(bar_chart, use_container_width=True)
            
            with c_chart2:
                st.markdown("##### 🍰 Inventory Mix")
                abc_counts = df_filtered["ABC Class"].value_counts().reset_index()
                abc_counts.columns = ["Class", "Count"]
                pie_chart = alt.Chart(abc_counts).mark_arc(innerRadius=60).encode(
                    theta=alt.Theta(field="Count", type="quantitative"),
                    color=alt.Color(field="Class", scale=alt.Scale(domain=['A', 'B', 'C'], range=['#2ECC71', '#F1C40F', '#E74C3C']), legend=None),
                    tooltip=["Class", "Count"]
                ).properties(height=320)
                text = pie_chart.mark_text(align='center', baseline='middle', fontSize=20, fontWeight='bold').encode(text='sum(Count)')
                st.altair_chart(pie_chart + text, use_container_width=True)

            # Heatmap
            st.markdown("### 🔥 Stock Density Heatmap")
            heatmap_data = df_filtered.nlargest(100, 'Quantity') 
            heatmap = alt.Chart(heatmap_data).mark_rect().encode(
                x=alt.X('Location:N', title='Location'),
                y=alt.Y('Item Code:N', title='Item SKU'),
                color=alt.Color('Quantity:Q', scale=alt.Scale(scheme='goldorange'), title='Qty'),
                tooltip=['Location', 'Item Code', 'Quantity', 'ABC Class']
            ).properties(height=400).configure_axis(grid=False)
            st.altair_chart(heatmap, use_container_width=True)

        with tab2:
            st.markdown("### Detailed Inventory Report")
            
            # --- YENİ ÖZELLİK: POPUP (DIALOG) TETİKLEYİCİSİ ---
            col_sel, col_btn = st.columns([3, 1])
            with col_sel:
                # Kullanıcı detay görmek istediği ürünü buradan seçer
                item_to_inspect = st.selectbox("🔍 Inspect Specific SKU details:", ["Select an SKU..."] + sorted(list(df_filtered["Item Code"].unique())))
            
            with col_btn:
                # Butonu aşağı hizalamak için boşluk
                st.write("") 
                st.write("")
                if st.button("Open Details", use_container_width=True):
                    if item_to_inspect != "Select an SKU...":
                        show_sku_details(item_to_inspect, df)
                    else:
                        st.warning("Please select an SKU first.")

            # Tablo
            max_stok = int(df["Quantity"].max()) if not df.empty else 100
            st.dataframe(
                df_filtered,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Status": st.column_config.TextColumn("Status", width="small"),
                    "ABC Class": st.column_config.TextColumn("ABC", width="small"),
                    "Location": st.column_config.TextColumn("Location"),
                    "Item Code": st.column_config.TextColumn("Item Code"),
                    "Quantity": st.column_config.ProgressColumn("On Hand", format="%d", min_value=0, max_value=max_stok),
                }
            )
    else:
        st.warning("⚠️ No results found. Try adjusting filters.")
else:
    st.info("👋 Welcome. Please upload your daily stock file.")