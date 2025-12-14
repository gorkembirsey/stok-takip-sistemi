import streamlit as st
import pandas as pd
import altair as alt
from io import BytesIO

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Stryker Analiz Pro", layout="wide", page_icon="🚀")

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
    st.header("📂 Veri Yükleme")
    uploaded_file = st.file_uploader("Excel dosyasını buraya bırakın", type=["xlsx"])
    st.caption("Noktalama işaretleri otomatik temizlenir.")

# --- ANA PROGRAM ---
if uploaded_file:
    try:
        # Veri Okuma
        df = pd.read_excel(uploaded_file)

        # --- KRİTİK DÜZELTME: SÜTUN İSİMLERİNİ TEMİZLEME ---
        # Altair kütüphanesi '.' ve '()' karakterlerini sevmez. Bunları temizliyoruz.
        df.columns = df.columns.astype(str).str.replace(r'[.\(\)]', '', regex=True).str.strip()
        # Örnek: "Kasım 1. Hafta" -> "Kasım 1 Hafta" olur.

        # --- OTOMATİK TİP ANALİZİ ---
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        text_cols = df.select_dtypes(include=['object', 'string']).columns.tolist()

        if not text_cols:
            df["Satır No"] = df.index.astype(str)
            text_cols = ["Satır No"]

        # Varsayılan X Ekseni (Tanım)
        default_x = text_cols[0]
        for col in text_cols:
            if any(x in col.lower() for x in ['desc', 'tanım', 'ad', 'name', 'açıklama']):
                default_x = col
                break

        # Varsayılan Y Ekseni (Sayısal)
        # Genelde son sütunlar toplamlardır, onları seçelim
        default_y = [numeric_cols[-1]] if numeric_cols else []

        st.title(f"📊 Akıllı Analiz Paneli: {uploaded_file.name}")
        st.markdown("---")

        if not numeric_cols:
            st.error("Grafik çizilebilecek sayısal veri bulunamadı.")
        else:
            # --- AYARLAR ---
            with st.expander("🛠️ Analiz Ayarları", expanded=True):
                c1, c2 = st.columns([1, 2])

                # X Ekseni (Tek seçim)
                x_axis = c1.selectbox("Gruplama (X Ekseni):", text_cols, index=text_cols.index(default_x))

                # Y Ekseni (Çoklu Seçim)
                y_axis = c2.multiselect("Karşılaştırılacak Değerler (Y Ekseni):", numeric_cols, default=default_y)

            if not y_axis:
                st.warning("Lütfen analiz için en az bir sayısal sütun seçin.")
            else:
                # --- HESAPLAMALAR ---
                # 1. Ana Gruplama
                grouped_df = df.groupby(x_axis)[y_axis].sum().reset_index()

                # KPI Hesaplamaları
                total_val = grouped_df[y_axis].sum().sum()
                unique_count = grouped_df[x_axis].nunique()

                # Ortalama (Satır başına düşen ortalama değer)
                # Seçilen tüm sütunların toplamını satır sayısına bölüyoruz
                avg_val = total_val / unique_count if unique_count > 0 else 0

                # Lideri bulmak için geçici toplam
                grouped_df['Total_Temp'] = grouped_df[y_axis].sum(axis=1)
                leader_row = grouped_df.loc[grouped_df['Total_Temp'].idxmax()]
                leader_name = leader_row[x_axis]
                leader_val = leader_row['Total_Temp']

                # --- KPI KARTLARI ---
                k1, k2, k3, k4 = st.columns(4)
                k1.metric("Genel Toplam", f"{total_val:,.0f}")
                k2.metric(f"Benzersiz {x_axis}", f"{unique_count}")
                k3.metric("Ortalama Ürün Adedi", f"{avg_val:,.1f}")
                k4.metric("🏆 Lider", f"{str(leader_name)[:15]}..", f"{leader_val:,.0f}")

                st.markdown("###")

                # --- GRAFİK MANTIĞI ---

                # Senaryo 1: TEK BİR SÜTUN SEÇİLDİYSE
                if len(y_axis) == 1:
                    selected_metric = y_axis[0]

                    c_chart_type, c_dummy = st.columns([1, 3])
                    chart_type = c_chart_type.radio("Grafik Türü:", ["Sütun Grafiği (Bar)", "Pasta Grafiği (Pie)"],
                                                    horizontal=True)

                    # Top 20 Veri
                    chart_data = grouped_df.nlargest(20, selected_metric)

                    if "Sütun" in chart_type:
                        chart = alt.Chart(chart_data).mark_bar(cornerRadius=5).encode(
                            x=alt.X(x_axis, sort='-y', title=x_axis),
                            y=alt.Y(selected_metric, title='Değer'),
                            color=alt.Color(selected_metric, scale=alt.Scale(scheme='goldorange'), legend=None),
                            tooltip=[x_axis, selected_metric]
                        ).properties(height=400)
                    else:
                        chart = alt.Chart(chart_data).mark_arc(innerRadius=60).encode(
                            theta=alt.Theta(selected_metric, stack=True),
                            color=alt.Color(x_axis, sort='descending'),
                            tooltip=[x_axis, selected_metric],
                            order=alt.Order(selected_metric, sort='descending')
                        ).properties(height=400)

                    st.altair_chart(chart, use_container_width=True)

                # Senaryo 2: KARŞILAŞTIRMA MODU (Multi-Select)
                else:
                    st.info(f"ℹ️ {len(y_axis)} farklı veri seti karşılaştırılıyor.")

                    # Veriyi Uzun Format'a çevir (Altair için)
                    melted_df = grouped_df.melt(id_vars=[x_axis], value_vars=y_axis, var_name='Kategori',
                                                value_name='Değer')

                    # En büyük 15 kalemi filtrele (Grafik karışmasın)
                    top_items = grouped_df.nlargest(15, 'Total_Temp')[x_axis].tolist()
                    melted_filtered = melted_df[melted_df[x_axis].isin(top_items)]

                    # Gruplanmış Bar Grafiği
                    chart = alt.Chart(melted_filtered).mark_bar().encode(
                        x=alt.X(x_axis, sort=None, title=x_axis),
                        y=alt.Y('Değer', title='Miktar'),
                        color=alt.Color('Kategori', title='Dönem / Veri', scale=alt.Scale(scheme='category10')),
                        xOffset='Kategori',  # Yan yana barlar
                        tooltip=[x_axis, 'Kategori', 'Değer']
                    ).properties(height=400)

                    st.altair_chart(chart, use_container_width=True)

                    # --- GENEL TOPLAM ÖZETİ ---
                    st.markdown("---")
                    st.subheader("📈 Seçilen Dönemlerin Toplam Karşılaştırması")

                    totals_data = df[y_axis].sum().reset_index()
                    totals_data.columns = ['Veri Seti', 'Genel Toplam']

                    summary_chart = alt.Chart(totals_data).mark_bar(color="#2ECC71", cornerRadius=5, size=50).encode(
                        x=alt.X('Veri Seti', sort='-y'),
                        y=alt.Y('Genel Toplam'),
                        tooltip=['Veri Seti', 'Genel Toplam']
                    ).properties(height=250)

                    st.altair_chart(summary_chart, use_container_width=True)

                # --- TABLO ---
                with st.expander("📋 Detaylı Verileri İncele"):
                    st.dataframe(grouped_df, use_container_width=True)
                    excel_data = convert_df(grouped_df)
                    st.download_button("📥 Tabloyu İndir", data=excel_data, file_name="Analiz.xlsx")

    except Exception as e:
        st.error(f"Bir hata oluştu: {e}")
        st.warning("Excel dosyasındaki sütun isimlerini kontrol edin.")

else:
    st.info("👆 Analiz için Excel dosyasını yükleyin.")