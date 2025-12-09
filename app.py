import streamlit as st
import pandas as pd
import os
import altair as alt
from io import BytesIO

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
        
        /* Butonlar - Tüm butonları standartlaştır */
        div.stButton > button {
            width: 100%;
            border-radius: 6px;
            font-weight: 600;
            border: 1px solid #e0e0e0;
        }
        
        /* "Select All" vb. butonlar için özel renk */
        div.stButton > button:first-child {
            background-color: #FFC107; 
            color: black; 
            border: none;
        }
    </style>
""", unsafe_allow_html=True)

# --- BAŞLIK BÖLÜMÜ (DÜZENLENDİ) ---
col_logo, col_title = st.columns([0.5, 6])
with col_title:
    st.title("Inventory Intelligence") 
    # Alt başlık kaldırıldı
st.markdown("---")

# --- SESSION STATE ---
if 'selected_locs' not in st.session_state:
    st.session_state['selected_locs'] = []
if 'selected_items' not in st.session_state:
    st.session_state['selected_items'] = []

# --- 3. SIDEBAR ---
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/c/c2/Stryker_Corporation_logo.svg/2560px-Stryker_Corporation_logo.svg.png", width=150)
    st.markdown("### Control Panel")
    
    # A) VERİ YÜKLEME
    with st.expander("📂 Data Upload", expanded=True):
        uploaded_file = st.file_uploader("Drop Daily Excel", type=["xlsx"])
        
    df = pd.DataFrame()
    if uploaded_file is not None:
        df = pd.read_excel(uploaded_file)
    elif os.path.exists('stok.xlsx'):
        df = pd.read_excel('stok.xlsx')

    # B) AYARLAR
    with st.expander("⚙️ System Settings", expanded=False):
        threshold = st.slider("🔴 Critical Stock Limit", 0, 100, 10)

# --- EXCEL ÇIKTI FONKSİYONU ---
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
        # Veri Tipleme
        df["Location"] = df["Location"].astype(str)
        df["Item Code"] = df["Item Code"].astype(str)
        df["Quantity"] = pd.to_numeric(df["Quantity"], errors='coerce').fillna(0)
        
        # --- C) SMART FILTERS (BURASI DÜZENLENDİ) ---
        with st.sidebar.expander("🔍 Smart Filters", expanded=True):
            
            # 1. LOKASYON FİLTRESİ
            st.markdown("**📍 Filter by Location**")
            tum_lokasyonlar = sorted(list(df["Location"].unique()))
            
            c1, c2 = st.columns([1, 1]) # Eşit genişlik
            if c1.button("Select All", key="loc_all"):
                st.session_state['selected_locs'] = tum_lokasyonlar
                st.rerun()
            if c2.button("Clear", key="loc_clear"):
                st.session_state['selected_locs'] = []
                st.rerun()
                
            secilen_yerler = st.multiselect(
                "Select Locations", 
                tum_lokasyonlar,
                default=st.session_state['selected_locs'],
                label_visibility="collapsed",
                key='loc_multiselect'
            )
            
            # Dinamik Ürün Listesi Hazırlığı
            if secilen_yerler:
                mevcut_urunler = df[df["Location"].isin(secilen_yerler)]["Item Code"].unique()
            else:
                mevcut_urunler = df["Item Code"].unique()
            
            st.markdown("---") # Ayırıcı Çizgi
            
            # 2. ÜRÜN FİLTRESİ (ITEM CODE) - KESİN GÖRÜNMESİ İÇİN BURADA
            st.markdown("**🏷️ Filter by Item Code**")
            
            c3, c4 = st.columns([1, 1]) # Eşit genişlik
            if c3.button("Select All", key="item_all"):
                st.session_state['selected_items'] = sorted(list(mevcut_urunler))
                st.rerun()
            if c4.button("Clear", key="item_clear"):
                st.session_state['selected_items'] = []
                st.rerun()

            # Session State temizliği (Eğer listede olmayan bir seçim kaldıysa)
            valid_defaults = [x for x in st.session_state['selected_items'] if x in mevcut_urunler]
            
            secilen_urunler = st.multiselect(
                "Select Items",
                sorted(list(mevcut_urunler)),
                default=valid_defaults,
                label_visibility="collapsed",
                key='item_multiselect'
            )

            st.markdown("---")
            
            # 3. ARAMA
            search_term = st.text_input("Deep Search", placeholder="Type SKU or Location...", help="Global search")

        # --- FİLTRELEME MANTIĞI ---
        df_filtered = df.copy()
        
        # 1. Lokasyon
        if secilen_yerler: 
            df_filtered = df_filtered[df_filtered["Location"].isin(secilen_yerler)]
        
        # 2. Ürün
        if secilen_urunler:
            df_filtered = df_filtered[df_filtered["Item Code"].isin(secilen_urunler)]
            
        # 3. Arama
        if search_term:
            df_filtered = df_filtered[
                df_filtered["Item Code"].str.contains(search_term, case=False, na=False) |
                df_filtered["Location"].str.contains(search_term, case=False, na=False)
            ]

        # --- DASHBOARD GÖRSELLEŞTİRME ---
        if not df_filtered.empty:
            # ABC ve Kritik Stok Hesabı
            df_sorted = df_filtered.sort_values("Quantity", ascending=False)
            df_sorted["Cum_Sum"] = df_sorted["Quantity"].cumsum()
            df_sorted["Cum_Perc"] = 100 * df_sorted["Cum_Sum"] / df_sorted["Quantity"].sum()
            
            def get_class(x):
                if x <= 80: return "A"
                elif x <= 95: return "B"
                else: return "C"
                
            df_filtered["ABC Class"] = df_sorted["Cum_Perc"].apply(get_class)
            df_filtered["Status"] = df_filtered["Quantity"].apply(lambda x: "🔴 Critical" if x <= threshold else "🟢 Healthy")

            # TABLAR
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
                k4.metric("🚨 Critical Items", f"{critical_count}", delta_color="inverse")
                
                st.markdown("###")

                # Charts
                c_chart1, c_chart2 = st.columns([2, 1])
                with c_chart1:
                    st.markdown("##### 📈 Volume Analysis")
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
                    st.markdown("##### 🍰 Inventory Mix")
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
                        "Quantity": st.column_config.ProgressColumn("On Hand", format="%d", min_value=0, max_value=max_stok),
                    }
                )
        else:
            st.warning(f"⚠️ No results found. Try adjusting filters.")
    else:
        st.error(f"Missing Columns: {eksik}")
else:
    st.info("👋 Welcome to Inventory Intelligence. Please upload your daily stock file.")