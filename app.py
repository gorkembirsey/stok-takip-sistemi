import streamlit as st
import pandas as pd
import os
import altair as alt
from io import BytesIO

# --- 1. SAYFA YAPILANDIRMASI ---
st.set_page_config(
    page_title="Stryker Inventory Hub",
    layout="wide",
    page_icon="📦",
    initial_sidebar_state="expanded"
)

# --- 2. CSS İLE PREMIUM TASARIM (GÖLGE, RENK, DARK/LIGHT UYUMU) ---
st.markdown("""
    <style>
        /* Ana Arka Plan */
        .stApp {
            background-color: #F5F7FA;
        }
        
        /* Başlıklar */
        h1, h2, h3 {
            color: #2C3E50;
            font-family: 'Segoe UI', sans-serif;
        }
        
        /* Sidebar Tasarımı */
        [data-testid="stSidebar"] {
            background-color: #FFFFFF;
            box-shadow: 2px 0 5px rgba(0,0,0,0.05);
        }
        
        /* Metrik Kartları (Box Shadow & Radius) */
        div[data-testid="stMetric"] {
            background-color: #FFFFFF;
            border: none;
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            transition: transform 0.2s;
        }
        div[data-testid="stMetric"]:hover {
            transform: translateY(-5px);
        }
        
        /* Tab Tasarımı */
        .stTabs [data-baseweb="tab-list"] {
            gap: 10px;
            background-color: transparent;
        }
        .stTabs [data-baseweb="tab"] {
            height: 50px;
            background-color: #FFFFFF;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            border: 1px solid #E0E0E0;
            font-weight: 600;
        }
        .stTabs [aria-selected="true"] {
            background-color: #FFC107 !important; /* Stryker Gold */
            color: black !important;
            border: none;
        }

        /* Butonlar */
        div.stButton > button:first-child {
            background-color: #FFC107;
            color: black;
            border-radius: 8px;
            border: none;
            font-weight: bold;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        /* Expander (Accordion) Başlıkları */
        .streamlit-expanderHeader {
            font-weight: bold;
            color: #34495E;
        }
    </style>
""", unsafe_allow_html=True)

# --- HEADER ---
col_logo, col_title = st.columns([0.5, 6])
with col_title:
    st.title("📦 Stryker | Inventory Intelligence")
    st.markdown("<span style='color: #7F8C8D; font-size: 14px;'>Operational Excellence Dashboard • Order Management</span>", unsafe_allow_html=True)
st.markdown("---")

# --- SESSION STATE (Filtre Butonları İçin) ---
if 'selected_locs' not in st.session_state:
    st.session_state['selected_locs'] = []
if 'selected_items' not in st.session_state:
    st.session_state['selected_items'] = []

# --- 3. YAN MENÜ (SIDEBAR) TASARIMI ---
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/c/c2/Stryker_Corporation_logo.svg/2560px-Stryker_Corporation_logo.svg.png", width=150)
    st.markdown("### Control Panel")
    
    # A) VERİ YÜKLEME (ACCORDION)
    with st.expander("📂 Data Upload", expanded=True):
        uploaded_file = st.file_uploader("Drop Daily Excel", type=["xlsx"])
        
    # Veri Okuma
    df = pd.DataFrame()
    if uploaded_file is not None:
        df = pd.read_excel(uploaded_file)
        st.toast('Data uploaded successfully!', icon='✅') # ANIMASYONLU BİLDİRİM
    elif os.path.exists('stok.xlsx'):
        df = pd.read_excel('stok.xlsx')

    # B) AYARLAR (ACCORDION)
    with st.expander("⚙️ System Settings", expanded=False):
        threshold = st.slider("🔴 Critical Stock Limit", 0, 100, 10)
        st.info(f"Items below {threshold} units will be flagged.")

# --- EXCEL ÇIKTI FONKSİYONU ---
def excel_olustur(df_input):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_input.to_excel(writer, index=False, sheet_name='Report')
    return output.getvalue()

# --- ANA PROGRAM AKIŞI ---
if not df.empty:
    df.columns = df.columns.str.strip()
    
    # Sütun Kontrolü
    gerekli = ["Location", "Quantity", "Item Code"]
    eksik = [c for c in gerekli if c not in df.columns]

    if not eksik:
        # Tipleme ve Temizleme
        df["Location"] = df["Location"].astype(str)
        df["Item Code"] = df["Item Code"].astype(str)
        df["Quantity"] = pd.to_numeric(df["Quantity"], errors='coerce').fillna(0)
        
        # --- C) GELİŞMİŞ FİLTRELEME (SIDEBAR DEVAM) ---
        with st.sidebar.expander("🔍 Smart Filters", expanded=True):
            
            # 1. Lokasyon Filtresi (Select All / Clear Logic)
            tum_lokasyonlar = sorted(list(df["Location"].unique()))
            
            # Helper butonlar için kolonlar
            c1, c2 = st.columns(2)
            if c1.button("Select All", key="all_loc"):
                st.session_state['selected_locs'] = tum_lokasyonlar
            if c2.button("Clear", key="clear_loc"):
                st.session_state['selected_locs'] = []
                
            secilen_yerler = st.multiselect(
                "Filter by Location:", 
                tum_lokasyonlar,
                default=st.session_state['selected_locs'],
                key='loc_multiselect'
            )
            
            # Dinamik Ürün Listesi
            if secilen_yerler:
                mevcut_urunler = df[df["Location"].isin(secilen_yerler)]["Item Code"].unique()
            else:
                mevcut_urunler = df["Item Code"].unique()
            
            st.markdown("---")
            
            # 2. Arama Kutusu (Eski buton yerine daha şık arama)
            search_term = st.text_input("Deep Search (SKU/Loc)", placeholder="Type to search...", help="Search inside Location or Item Code")

        # --- VERİ İŞLEME & FİLTRELEME ---
        df_filtered = df.copy()
        
        # Session State senkronizasyonu (Select All butonları için trick)
        # Multiselect değiştiyse onu baz al, buton basıldıysa butonu baz al mantığı karmaşıklaşır.
        # Bu kodda "Select All" basılınca sayfa yenilenir ve default değer dolar.
        
        if secilen_yerler: 
            df_filtered = df_filtered[df_filtered["Location"].isin(secilen_yerler)]
        
        if search_term:
            df_filtered = df_filtered[
                df_filtered["Item Code"].str.contains(search_term, case=False, na=False) |
                df_filtered["Location"].str.contains(search_term, case=False, na=False)
            ]

        # --- ANALİTİK HESAPLAMALAR (ABC & STATUS) ---
        if not df_filtered.empty:
            df_sorted = df_filtered.sort_values("Quantity", ascending=False)
            df_sorted["Cum_Sum"] = df_sorted["Quantity"].cumsum()
            df_sorted["Cum_Perc"] = 100 * df_sorted["Cum_Sum"] / df_sorted["Quantity"].sum()
            
            def get_class(x):
                if x <= 80: return "A"
                elif x <= 95: return "B"
                else: return "C"
                
            df_filtered["ABC Class"] = df_sorted["Cum_Perc"].apply(get_class)
            df_filtered["Status"] = df_filtered["Quantity"].apply(lambda x: "🔴 Critical" if x <= threshold else "🟢 Healthy")

            # --- GÖRSELLEŞTİRME ---
            tab1, tab2 = st.tabs(["📊 Executive Dashboard", "📋 Master Data List"])

            with tab1:
                # KPI KARTLARI
                total_qty = df_filtered["Quantity"].sum()
                total_sku = df_filtered["Item Code"].nunique()
                total_loc = df_filtered["Location"].nunique()
                critical_count = df_filtered[df_filtered["Quantity"] <= threshold].shape[0]

                k1, k2, k3, k4 = st.columns(4)
                k1.metric("📦 Total Stock", f"{total_qty:,.0f}")
                k2.metric("🏷️ Unique SKUs", f"{total_sku}")
                k3.metric("📍 Locations", f"{total_loc}")
                k4.metric("🚨 Critical Items", f"{critical_count}", delta_color="inverse")
                
                st.markdown("###") # Boşluk

                # GRAFİKLER
                c_chart1, c_chart2 = st.columns([2, 1])
                
                with c_chart1:
                    st.markdown("##### 📈 Top 15 Locations by Volume")
                    chart_data = df_filtered.groupby("Location")["Quantity"].sum().reset_index().nlargest(15, "Quantity")
                    
                    bar_chart = alt.Chart(chart_data).mark_bar(
                        cornerRadius=5, color="#FFC107"
                    ).encode(
                        x=alt.X('Location', sort='-y'),
                        y=alt.Y('Quantity'),
                        tooltip=['Location', 'Quantity']
                    ).properties(height=350)
                    
                    st.altair_chart(bar_chart, use_container_width=True)
                
                with c_chart2:
                    st.markdown("##### 🍰 ABC Segmentation")
                    abc_counts = df_filtered["ABC Class"].value_counts().reset_index()
                    abc_counts.columns = ["Class", "Count"]
                    
                    pie_chart = alt.Chart(abc_counts).mark_arc(innerRadius=60).encode(
                        theta=alt.Theta(field="Count", type="quantitative"),
                        color=alt.Color(field="Class", scale=alt.Scale(domain=['A', 'B', 'C'], range=['#2ECC71', '#F1C40F', '#E74C3C'])),
                        tooltip=["Class", "Count"]
                    ).properties(height=350)
                    
                    st.altair_chart(pie_chart, use_container_width=True)

            with tab2:
                col_h, col_b = st.columns([5, 1])
                col_h.markdown("### Detailed Inventory Report")
                
                excel_data = excel_olustur(df_filtered)
                col_b.download_button(
                    "📥 Export Excel",
                    data=excel_data,
                    file_name="Stryker_Inventory_Report.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
                
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
                        "Quantity": st.column_config.ProgressColumn(
                            "On Hand",
                            format="%d",
                            min_value=0,
                            max_value=max_stok,
                        ),
                    }
                )

        else:
            st.warning(f"⚠️ No results found for '{search_term}'. Try adjusting filters.")
    else:
        st.error(f"Missing Columns in Excel: {eksik}")
else:
    # Karşılama Ekranı
    st.info("👋 Welcome to Stryker Inventory Hub. Please upload your daily stock file from the sidebar.")