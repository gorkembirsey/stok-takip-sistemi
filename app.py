import streamlit as st
import pandas as pd
import altair as alt
from io import BytesIO
import datetime

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Akıllı Analiz", layout="wide", page_icon="🧠")

# --- CSS (Görünüm) ---
st.markdown("""
    <style>
        .stApp {background-color: #F5F7FA;}
        div[data-testid="stMetric"] {background-color: #ffffff; border-radius: 10px; padding: 15px; box-shadow: 0 2px 5px rgba(0,0,0,0.05);}
    </style>
""", unsafe_allow_html=True)


# --- EXCEL İNDİRME FONKSİYONU ---
def convert_df(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()


# --- YAN MENÜ ---
with st.sidebar:
    st.header("📂 Veri Yükleme")
    uploaded_file = st.file_uploader("Excel dosyasını sürükleyin", type=["xlsx"])
    st.info("💡 İpucu: Sistem, yüklediğiniz dosyadaki metin ve sayıları otomatik ayırt eder.")

# --- ANA PROGRAM ---
if uploaded_file:
    try:
        # Veriyi Oku
        df = pd.read_excel(uploaded_file)

        # Sütun isimlerini temizle (Baş ve sondaki boşlukları sil)
        df.columns = df.columns.str.strip()

        # --- OTOMATİK TİP ANALİZİ (SİHİRLİ KISIM) ---

        # 1. Sayısal Sütunları Bul (Miktar, Tutar, Stok vb.)
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()

        # 2. Kategorik (Metin) Sütunları Bul (Ürün Adı, Lokasyon, Kod vb.)
        # Object ve Category tiplerini al, ayrıca sayısal olsa bile adı "ID", "No", "Code" içerenleri buraya dahil etmeye çalışabiliriz
        # Şimdilik sadece net metin olanları alıyoruz.
        text_cols = df.select_dtypes(include=['object', 'string']).columns.tolist()

        # Eğer hiç metin sütunu yoksa (mesela sadece sayılar varsa), index'i referans al
        if not text_cols:
            df["Satır No"] = df.index.astype(str)
            text_cols = ["Satır No"]

        # --- VARSAYILAN SEÇİMLER (AUTO-SELECT) ---
        # Genelde en çok benzersiz değeri olan metin sütunu "Ürün Adı" veya "Açıklama"dır.
        # Onu X ekseni yapmak mantıklıdır.
        default_x_axis = text_cols[0]
        # "Description" veya "Ad" geçiyorsa onu önceliklendir
        for col in text_cols:
            if any(x in col.lower() for x in ['desc', 'tanım', 'ad', 'name', 'açıklama']):
                default_x_axis = col
                break

        # Genelde son sütunlar "Toplam" olur, varsayılan Y ekseni olarak en son sayısal sütunu seçelim.
        default_y_axis = numeric_cols[-1] if numeric_cols else None

        # --- BAŞLIK ---
        st.title(f"📊 Otomatik Veri Analizi: {uploaded_file.name}")
        st.markdown("---")

        if not numeric_cols:
            st.error("❌ Bu dosyada grafik çizilebilecek sayısal bir sütun bulunamadı.")
        else:
            # --- 1. KULLANICI KONTROLÜ (İsterse değiştirebilir) ---
            with st.expander("🛠️ Analiz Ayarları (Otomatik Algılandı)", expanded=True):
                c1, c2 = st.columns(2)

                # X Ekseni Seçimi (Kategoriler)
                selected_category = c1.selectbox(
                    "Gruplama Başlığı (X Ekseni):",
                    text_cols,
                    index=text_cols.index(default_x_axis)
                )

                # Y Ekseni Seçimi (Sayılar)
                selected_metric = c2.selectbox(
                    "Analiz Değeri (Y Ekseni):",
                    numeric_cols,
                    index=numeric_cols.index(default_y_axis)
                )

                # Toplama Yöntemi
                agg_func = st.radio("Hesaplama Yöntemi:", ["Toplam (Sum)", "Ortalama (Average)", "Sayım (Count)"],
                                    horizontal=True)

            # --- 2. HESAPLAMA VE ÇAKIŞMA ÖNLEME ---
            # Pandas'ta gruplama yaparken sütun ismi çakışmasını önlemek için
            # .reset_index(name='...') kullanarak yeni sütuna 'Analiz_Degeri' ismini veriyoruz.

            if agg_func == "Toplam (Sum)":
                grouped_df = df.groupby(selected_category)[selected_metric].sum().reset_index(name='Analiz_Sonucu')
            elif agg_func == "Ortalama (Average)":
                grouped_df = df.groupby(selected_category)[selected_metric].mean().reset_index(name='Analiz_Sonucu')
            else:
                grouped_df = df.groupby(selected_category)[selected_metric].count().reset_index(name='Analiz_Sonucu')

            # --- 3. DASHBOARD GÖRSELLEŞTİRME ---

            # KPI Kartları
            total_val = grouped_df['Analiz_Sonucu'].sum()
            count_val = grouped_df[selected_category].nunique()
            max_item = grouped_df.loc[grouped_df['Analiz_Sonucu'].idxmax()]

            k1, k2, k3 = st.columns(3)
            k1.metric("Genel Toplam", f"{total_val:,.0f}")
            k2.metric(f"Benzersiz {selected_category}", f"{count_val}")
            k3.metric("🏆 Lider", f"{max_item[selected_category]}", help=f"Değer: {max_item['Analiz_Sonucu']:,.0f}")

            st.markdown("###")

            # GRAFİK (Altair)
            st.subheader(f"📈 {selected_category} Bazlı Dağılım")

            # En büyük 20 veriyi göster (Grafik boğulmasın diye)
            chart_data = grouped_df.nlargest(20, 'Analiz_Sonucu')

            bar_chart = alt.Chart(chart_data).mark_bar(cornerRadius=5).encode(
                x=alt.X(selected_category, sort='-y', title=selected_category),
                y=alt.Y('Analiz_Sonucu', title=selected_metric),
                color=alt.Color('Analiz_Sonucu', scale=alt.Scale(scheme='goldorange'), legend=None),
                tooltip=[selected_category, alt.Tooltip('Analiz_Sonucu', format=',.0f', title=selected_metric)]
            ).properties(height=400)

            st.altair_chart(bar_chart, use_container_width=True)

            # --- 4. DETAYLI TABLO ---
            with st.expander("📋 Detaylı Veri Tablosunu Gör"):
                st.dataframe(grouped_df, use_container_width=True)

                excel_data = convert_df(grouped_df)
                st.download_button(
                    "📥 Bu Analizi İndir",
                    data=excel_data,
                    file_name="Analiz_Sonucu.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

    except Exception as e:
        st.error(f"Bir hata oluştu: {e}")
        st.warning("Lütfen dosyanızın bozuk olmadığından emin olun.")

else:
    # Karşılama Ekranı
    st.info(
        "👆 Lütfen analiz etmek istediğiniz Excel dosyasını sol taraftan yükleyin. Sistem başlıkları otomatik algılayacaktır.")