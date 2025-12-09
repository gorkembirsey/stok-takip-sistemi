import streamlit as st
import pandas as pd
import os
import altair as alt
from io import BytesIO

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Stryker Stock Search", layout="wide", page_icon="🔍")

# --- SADE VE TEMİZ TASARIM ---
st.markdown("""
    <style>
        .block-container {padding-top: 2rem;}
        h1 {color: #C29B0C;} 
        /* Tablo başlıklarını sabitle ve renklendir */
        thead tr th:first-child {display:none}
        tbody th {display:none}
        .stDataFrame {border: 1px solid #f0f0f0; border-radius: 5px;}
    </style>
""", unsafe_allow_html=True)

# --- BAŞLIK ---
c1, c2 = st.columns([0.5, 8])
with c2:
    st.title("Inventory Search Engine")
st.markdown("---")

# --- VERİ YÜKLEME ---
def verileri_yukle():
    st.sidebar.header("📂 Data Import")
    uploaded_file = st.sidebar.file_uploader("Upload Excel", type=["xlsx"])
    if uploaded_file is not None:
        return pd.read_excel(uploaded_file)
    elif os.path.exists('stok.xlsx'):
        return pd.read_excel('stok.xlsx')
    else:
        return pd.DataFrame()

df = verileri_yukle()

# --- EXCEL İNDİRME ---
def excel_olustur(df_input):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_input.to_excel(writer, index=False, sheet_name='Report')
    return output.getvalue()

# --- ANA PROGRAM ---
if not df.empty:
    df.columns = df.columns.str.strip()
    
    # Veri Hazırlığı
    gerekli = ["Location", "Quantity", "Item Code"]
    if all(col in df.columns for col in gerekli):
        df["Location"] = df["Location"].astype(str)
        df["Item Code"] = df["Item Code"].astype(str)
        df["Quantity"] = pd.to_numeric(df["Quantity"], errors='coerce').fillna(0)

        # --- YENİ: GLOBAL ARAMA MOTORU ---
        st.sidebar.subheader("🔍 Quick Search")
        # Buraya ne yazarsan (Ürün veya Depo) onu bulur
        arama_kelimesi = st.sidebar.text_input("Type location or item code...", placeholder="Ex: Shaver or A1")
        
        # Filtreleme Mantığı (Hem depoda hem ürün isminde arar)
        if arama_kelimesi:
            arama_kelimesi = arama_kelimesi.lower()
            df_filtered = df[
                df["Location"].str.lower().contains(arama_kelimesi) | 
                df["Item Code"].str.lower().contains(arama_kelimesi)
            ]
        else:
            df_filtered = df # Arama yoksa hepsi

        # --- SONUÇ ALANI ---
        if not df_filtered.empty:
            
            # Üst Özet
            k1, k2, k3 = st.columns(3)
            k1.metric("Items Found", f"{len(df_filtered)}")
            k2.metric("Total Qty", f"{df_filtered['Quantity'].sum():,.0f}")
            k3.metric("Locations", f"{df_filtered['Location'].nunique()}")

            tab1, tab2 = st.tabs(["🔥 Heatmap Matrix", "📋 Data List"])

            # --- TAB 1: ISI HARİTASI (MATRİS) ---
            with tab1:
                st.caption("Intensity Map: Darker colors indicate higher stock levels.")
                
                # Eğer çok fazla veri varsa grafik karışır, uyaralım veya limitleyelim
                if len(df_filtered) > 500:
                    st.warning("⚠️ Too many items found for heatmap. Showing top 50 items by quantity.")
                    chart_data = df_filtered.nlargest(50, "Quantity")
                else:
                    chart_data = df_filtered

                # Heatmap (Kareli Harita)
                heatmap = alt.Chart(chart_data).mark_rect().encode(
                    x=alt.X('Location:N', title='Location'),
                    y=alt.Y('Item Code:N', title='Item Code'),
                    color=alt.Color('Quantity:Q', scale=alt.Scale(scheme='goldorange'), title='Qty'),
                    tooltip=['Location', 'Item Code', 'Quantity']
                ).properties(
                    height=max(400, len(chart_data['Item Code'].unique()) * 20) # Otomatik yükseklik
                ).configure_axis(
                    labelFontSize=11
                )
                
                st.altair_chart(heatmap, use_container_width=True)

            # --- TAB 2: LİSTE ---
            with tab2:
                col_ex_1, col_ex_2 = st.columns([4,1])
                excel_data = excel_olustur(df_filtered)
                col_ex_2.download_button("📥 Download", data=excel_data, file_name="Search_Result.xlsx", use_container_width=True)

                st.dataframe(
                    df_filtered,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Quantity": st.column_config.ProgressColumn(
                            "Qty", format="%d", min_value=0, max_value=int(df["Quantity"].max())
                        )
                    }
                )
        else:
            st.warning("⚠️ No records found matching your search.")

    else:
        st.error("Missing headers in Excel.")
else:
    st.info("👋 Upload data to start searching.")