import streamlit as st
import pandas as pd
import altair as alt
from io import BytesIO
import datetime

# --- SAYFA YAPILANDIRMASI ---
st.set_page_config(page_title="Stock Control Intelligence", layout="wide", page_icon="🧠")

# --- CSS AYARLARI (GÖRSEL DÜZENLEMELER) ---
st.markdown("""
    <style>
        .stApp {background-color: #F4F6F9;}

        /* ALERT CENTER STİLİ */
        .alert-box-red {
            padding: 15px; border-radius: 8px; background-color: #ffebee; 
            border-left: 5px solid #d32f2f; color: #b71c1c; font-weight: bold;
        }
        .alert-box-orange {
            padding: 15px; border-radius: 8px; background-color: #fff3e0; 
            border-left: 5px solid #f57c00; color: #e65100; font-weight: bold;
        }

        /* KPI KARTLARI */
        div[data-testid="stMetric"] {
            background-color: #ffffff !important;
            border: 1px solid #e0e0e0;
            border-left: 6px solid #FFC107 !important;
            padding: 15px; border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }

        /* TABLOLAR */
        thead th {
            background-color: #f0f2f6 !important; color: #31333F !important;
            font-size: 14px !important; font-weight: 600 !important;
            border-bottom: 2px solid #e0e0e0 !important;
        }
        tbody tr:nth-of-type(even) {background-color: #f9f9f9;}

        /* SEKMELER */
        .stTabs [data-baseweb="tab-list"] {gap: 8px;}
        .stTabs [data-baseweb="tab"] {height: 40px; background-color: white; border-radius: 4px; font-weight: 600; border: 1px solid #ddd;}
        .stTabs [aria-selected="true"] {background-color: #fff !important; color: #000 !important; border-bottom: 3px solid #FFC107 !important;}
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

        # STOK (Burada SKT Analizi Yapacağız)
        df_stok = sheets.get("Stok", pd.DataFrame())
        if not df_stok.empty:
            df_stok.columns = df_stok.columns.str.strip()
            df_stok.rename(columns={'Item Number': 'Item No'}, inplace=True)
            if 'Item No' in df_stok.columns: df_stok['Item No'] = df_stok['Item No'].astype(str).str.strip()
            if 'Qty On Hand' in df_stok.columns: df_stok['Qty On Hand'] = pd.to_numeric(df_stok['Qty On Hand'],
                                                                                        errors='coerce').fillna(0)

            # --- 🔥 EXPIRY RISK SCORE MOTORU ---
            if 'Expire' in df_stok.columns:
                # Tarih formatını zorla
                df_stok['Expire_Date'] = pd.to_datetime(df_stok['Expire'], errors='coerce')

                # Gün farkını hesapla
                df_stok['Days_To_Expire'] = (df_stok['Expire_Date'] - today).dt.days


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

        # --- 🔔 ALERT CENTER (AKILLI UYARILAR) ---
        with st.expander("🔔 Alert Center (Uyarı Merkezi)", expanded=True):
            # Kritik Verileri Hesapla
            critical_expiry = df_stok[df_stok['Risk Durumu'] == "🔴 Kritik (<6 Ay)"].shape[0] if not df_stok.empty else 0
            warning_expiry = df_stok[df_stok['Risk Durumu'] == "🟠 Riskli (6-12 Ay)"].shape[
                0] if not df_stok.empty else 0
            stock_outs = len(df_out)

            col_a1, col_a2, col_a3 = st.columns(3)

            with col_a1:
                st.markdown(f"""
                    <div class="alert-box-red">
                    🚨 {critical_expiry} Ürün SKT Riski Taşıyor (<6 Ay)
                    </div>
                """, unsafe_allow_html=True)
                if critical_expiry > 0:
                    with st.popover("Detayları Gör"):
                        st.dataframe(
                            df_stok[df_stok['Risk Durumu'] == "🔴 Kritik (<6 Ay)"][['Item No', 'Expire', 'Location']],
                            hide_index=True)

            with col_a2:
                st.markdown(f"""
                    <div class="alert-box-orange">
                    ⚠️ {warning_expiry} Ürün Yakın Takipte (6-12 Ay)
                    </div>
                """, unsafe_allow_html=True)

            with col_a3:
                st.markdown(f"""
                    <div class="alert-box-red" style="border-left-color: #333; color: #333; background-color: #f5f5f5;">
                    📉 {stock_outs} Ürün Stock Out Durumunda
                    </div>
                """, unsafe_allow_html=True)

        st.markdown("###")

        # KPI KARTLARI
        qty_hand = df_stok['Qty On Hand'].sum() if not df_stok.empty else 0
        qty_order = df_venlo['Ordered Qty Order UOM'].sum() if not df_venlo.empty else 0
        qty_ship = df_yolda['Qty Shipped'].sum() if not df_yolda.empty else 0

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("📦 Toplam Stok", f"{qty_hand:,.0f}")
        c2.metric("🌍 Bekleyen Sipariş", f"{qty_order:,.0f}")
        c3.metric("🚢 Yoldaki Ürün", f"{qty_ship:,.0f}")
        c4.metric("📊 Listelenen Kalem", f"{len(df_gen)}")

        st.markdown("###")

        # --- SEKMELER ---
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📋 General",
            "📍 Stok (Risk Analizi)",
            "🌍 Venlo Orders",
            "🚚 Yoldaki İthalatlar",
            "🚨 Stock Out"
        ])

        with tab1:
            if not df_gen.empty:
                st.dataframe(df_gen, use_container_width=True, hide_index=True,
                             column_config={
                                 "SS Coverage (W/O Consignment)": st.column_config.NumberColumn("SS Coverage",
                                                                                                format="%.1f%%")})
            else:
                st.info("Veri yok.")

        with tab2:
            if not df_stok.empty:
                c_chart, c_data = st.columns([1, 2])

                with c_chart:
                    # Risk Pasta Grafiği
                    risk_counts = df_stok['Risk Durumu'].value_counts().reset_index()
                    risk_counts.columns = ['Risk', 'Adet']

                    st.markdown("##### ⏳ SKT Risk Dağılımı")
                    base = alt.Chart(risk_counts).encode(theta=alt.Theta("Adet", stack=True))
                    pie = base.mark_arc(outerRadius=120).encode(
                        color=alt.Color("Risk", scale=alt.Scale(
                            domain=['🔴 Kritik (<6 Ay)', '🟠 Riskli (6-12 Ay)', '🟢 Güvenli (>12 Ay)', '⚪ Bilinmiyor'],
                            range=['#d32f2f', '#f57c00', '#2e7d32', '#9e9e9e'])),
                        tooltip=["Risk", "Adet"]
                    )
                    text = base.mark_text(radius=140).encode(
                        text="Adet", order=alt.Order("Risk"), color=alt.value("black")
                    )
                    st.altair_chart(pie + text, use_container_width=True)

                with c_data:
                    st.markdown("##### 📋 Stok Detayı ve Risk Puanı")


                    # Risk'e göre renklendirme (Highlight)
                    def highlight_risk(val):
                        if "🔴" in str(val):
                            return 'background-color: #ffebee; color: #b71c1c'
                        elif "🟠" in str(val):
                            return 'background-color: #fff3e0; color: #e65100'
                        elif "🟢" in str(val):
                            return 'background-color: #e8f5e9; color: #1b5e20'
                        return ''


                    st.dataframe(
                        df_stok.style.map(highlight_risk, subset=['Risk Durumu']),
                        use_container_width=True,
                        hide_index=True,
                        column_order=("Item No", "Location", "Qty On Hand", "Expire", "Risk Durumu")
                    )
            else:
                st.warning("Stok verisi yok.")

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

    except Exception as e:
        st.error(f"Bir hata oluştu: {e}")
else:
    st.info("👆 Lütfen Excel dosyasını yükleyin.")