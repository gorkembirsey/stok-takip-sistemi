import streamlit as st
import pandas as pd
import altair as alt
from io import BytesIO

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Stryker Analiz Pro Max", layout="wide", page_icon="💎")

# --- CSS (Görünüm) ---
st.markdown("""
    <style>
        .stApp {background-color: #F5F7FA;}
        div[data-testid="stMetric"] {background-color: #ffffff; border-radius: 10px; padding: 15px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); border: 1px solid #e0e0e0;}
        div.stButton > button {width: 100%; border-radius: 6px; font-weight: 600;}
    </style>
""", unsafe_allow_html=True)


# --- EXCEL İNDİRME ---
def convert_df(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()


# --- YAN MENÜ ---
with st.sidebar:
    st.image(
        "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c2/Stryker_Corporation_logo.svg/2560px-Stryker_Corporation_logo.svg.png",
        width=150)
    st.header("📂 Veri ve Ayarlar")
    uploaded_file = st.file_uploader("Excel dosyasını bırakın", type=["xlsx"])

    st.markdown("---")
    st.subheader("🎨 Görünüm Ayarları")

    # 1. YENİLİK: PARA BİRİMİ SEÇİCİ
    currency_symbol = st.radio("Para Birimi / Biçim:", ["Yok (Adet)", "₺ (TL)", "$ (USD)", "€ (EUR)"], horizontal=True)
    curr_code = "" if "Yok" in currency_symbol else currency_symbol.split("(")[0].strip()

# --- ANA PROGRAM ---
if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file)
        # Sütun isimlerini temizle (Nokta ve parantezleri kaldır)
        df.columns = df.columns.astype(str).str.replace(r'[.\(\)]', '', regex=True).str.strip()

        # --- TİP ANALİZİ ---
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        text_cols = df.select_dtypes(include=['object', 'string']).columns.tolist()

        if not text_cols:
            df["Satır No"] = df.index.astype(str)
            text_cols = ["Satır No"]

        # Varsayılanlar
        default_x = text_cols[0]
        for col in text_cols:
            if any(x in col.lower() for x in ['desc', 'tanım', 'ad', 'name', 'açıklama']):
                default_x = col
                break

        default_y = [numeric_cols[-1]] if numeric_cols else []

        st.title(f"💎 Yönetici Analiz Paneli: {uploaded_file.name}")
        st.markdown("---")

        if not numeric_cols:
            st.error("Sayısal veri bulunamadı.")
        else:
            with st.expander("🛠️ Analiz Parametreleri", expanded=True):
                c1, c2, c3 = st.columns([1, 2, 1])
                x_axis = c1.selectbox("Gruplama (X):", text_cols, index=text_cols.index(default_x))
                y_axis = c2.multiselect("Değerler (Y):", numeric_cols, default=default_y)

                # 2. YENİLİK: HEDEF ÇİZGİSİ
                target_line = c3.number_input("🎯 Hedef / Limit Çizgisi:", min_value=0, value=0,
                                              help="Grafikte referans çizgisi oluşturur.")

            if not y_axis:
                st.warning("Lütfen sayısal sütun seçin.")
            else:
                # --- VERİ HAZIRLIĞI ---
                grouped_df = df.groupby(x_axis)[y_axis].sum().reset_index()

                # Toplamlar
                total_val = grouped_df[y_axis].sum().sum()
                unique_count = grouped_df[x_axis].nunique()
                avg_val = total_val / unique_count if unique_count > 0 else 0

                # Lider
                grouped_df['Total_Temp'] = grouped_df[y_axis].sum(axis=1)
                leader_row = grouped_df.loc[grouped_df['Total_Temp'].idxmax()]

                # --- KPI KARTLARI (Para Birimli) ---
                k1, k2, k3, k4 = st.columns(4)
                k1.metric("Genel Toplam", f"{curr_code} {total_val:,.0f}")
                k2.metric(f"Benzersiz {x_axis}", f"{unique_count}")
                k3.metric("Ortalama", f"{curr_code} {avg_val:,.1f}")
                k4.metric("🏆 Lider", f"{str(leader_row[x_axis])[:15]}..",
                          f"{curr_code} {leader_row['Total_Temp']:,.0f}")

                st.markdown("###")

                # --- GRAFİK ALANI ---

                # Senaryo 1: TEK SÜTUN (PARETO ANALİZİ EKLENDİ)
                if len(y_axis) == 1:
                    sel_metric = y_axis[0]

                    # Veriyi hazırla (Top 25)
                    chart_data = grouped_df.sort_values(sel_metric, ascending=False).head(25).reset_index(drop=True)

                    # Pareto Hesabı: Kümülatif Yüzde
                    total_metric = chart_data[sel_metric].sum()
                    chart_data['Cumulative'] = chart_data[sel_metric].cumsum() / total_metric

                    # Temel Bar Grafiği
                    base = alt.Chart(chart_data).encode(
                        x=alt.X(x_axis, sort=None, title=x_axis)
                    )

                    bars = base.mark_bar(cornerRadius=5, color="#FFC107").encode(
                        y=alt.Y(sel_metric, title=sel_metric),
                        tooltip=[x_axis, alt.Tooltip(sel_metric, format=',.0f', title=f"{curr_code} Değer")]
                    )

                    # Pareto Çizgisi (Kırmızı)
                    line = base.mark_line(color='red', strokeWidth=3).encode(
                        y=alt.Y('Cumulative', title='Kümülatif %', axis=alt.Axis(format='%')),
                        tooltip=[alt.Tooltip('Cumulative', format='.1%', title="Kümülatif Pay")]
                    )

                    # Hedef Çizgisi (Kullanıcı girdiyse)
                    final_chart = (bars + line).resolve_scale(y='independent')

                    if target_line > 0:
                        rule = alt.Chart(pd.DataFrame({'y': [target_line]})).mark_rule(color='green',
                                                                                       strokeDash=[5, 5]).encode(y='y')
                        final_chart = (bars + line + rule).resolve_scale(y='independent')

                    st.subheader(f"📊 {x_axis} Analizi (Pareto + Hedef)")
                    st.altair_chart(final_chart, use_container_width=True)

                # Senaryo 2: ÇOKLU KARŞILAŞTIRMA
                else:
                    st.subheader("📈 Karşılaştırmalı Analiz")
                    melted = grouped_df.melt(id_vars=[x_axis], value_vars=y_axis, var_name='Grup', value_name='Deger')

                    # Top 15 Filtreleme
                    top_list = grouped_df.nlargest(15, 'Total_Temp')[x_axis].tolist()
                    melted_filtered = melted[melted[x_axis].isin(top_list)]

                    base_multi = alt.Chart(melted_filtered).encode(
                        x=alt.X(x_axis, sort=None)
                    )

                    bars_multi = base_multi.mark_bar().encode(
                        y=alt.Y('Deger', title='Değer'),
                        color=alt.Color('Grup', title='Veri'),
                        xOffset='Grup',
                        tooltip=[x_axis, 'Grup', alt.Tooltip('Deger', format=',.0f', title=f"{curr_code} Tutar")]
                    )

                    # Hedef çizgisi çoklu grafikte de olsun
                    if target_line > 0:
                        rule_multi = alt.Chart(pd.DataFrame({'y': [target_line]})).mark_rule(color='green',
                                                                                             strokeDash=[5, 5]).encode(
                            y='y')
                        st.altair_chart(bars_multi + rule_multi, use_container_width=True)
                    else:
                        st.altair_chart(bars_multi, use_container_width=True)

                    # Genel Toplam Barı
                    st.markdown("---")
                    totals = df[y_axis].sum().reset_index()
                    totals.columns = ['Metrik', 'Toplam']

                    summ_chart = alt.Chart(totals).mark_bar(color="#2ECC71", cornerRadius=5).encode(
                        x=alt.X('Metrik', sort='-y'),
                        y=alt.Y('Toplam'),
                        tooltip=['Metrik', alt.Tooltip('Toplam', format=',.0f', title=f"{curr_code} Toplam")]
                    ).properties(height=200)
                    st.altair_chart(summ_chart, use_container_width=True)

                # --- TABLO ---
                with st.expander("📋 Detaylı Veri Tablosu"):
                    st.dataframe(grouped_df, use_container_width=True)
                    excel_data = convert_df(grouped_df)
                    st.download_button("📥 İndir (Excel)", data=excel_data, file_name="Analiz.xlsx")

    except Exception as e:
        st.error(f"Hata: {e}")
else:
    st.info("👆 Analiz için Excel dosyasını yükleyin.")