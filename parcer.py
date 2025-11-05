import streamlit as st
import pandas as pd
import re
import io

# ==========================
# НАСТРОЙКИ
# ==========================

st.set_page_config(page_title="Анализ обращений", layout="wide")
st.title("📋 Анализ обращений клиентов (BlackQuant Diagnostics v1.1)")

st.markdown(
    "Загрузите Excel-файл с обращениями. "
    "Система определит обращения, связанные с **регистратурой / администраторами** "
    "и **ожиданием / задержками** и покажет примеры с указанием даты."
)

# Ключевые слова
keywords_admin = [
    "регистрат", "администрат", "ресепш", "не приняли",
    "ошибка при записи", "в регистратуре", "в регистратуру", "кассир", "касса"
]

keywords_wait = [
    "очеред", "ожидан", "ждать", "задерж", "поздно", "долго", "задержка", "задержали",
    "долго не"
]

# ==========================
# ФУНКЦИИ
# ==========================

def filter_by_keywords(data, text_col, keywords):
    pattern = "|".join(keywords)
    mask = data[text_col].str.contains(pattern, case=False, na=False)
    return data[mask].copy()

# ==========================
# ИНТЕРФЕЙС
# ==========================

uploaded_file = st.file_uploader("📂 Загрузите Excel-файл", type=["xlsx"])

if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file)
        st.success(f"Файл успешно загружен. Всего строк: {len(df)}")

        cols = list(df.columns)
        text_col = st.selectbox("Выберите столбец с текстом обращения:", cols)

        # попытка определить столбец даты
        date_col = st.selectbox(
            "Выберите столбец с датой обращения (если есть):",
            ["— нет даты —"] + cols,
            index=0
        )

        # анализ
        df[text_col] = df[text_col].astype(str).str.lower()

        if date_col != "— нет даты —":
            df["Дата"] = pd.to_datetime(df[date_col], errors="coerce")
            df["Год"] = df["Дата"].dt.year
            df["Месяц"] = df["Дата"].dt.to_period("M").astype(str)
        else:
            df["Дата"] = pd.NaT
            df["Год"] = None
            df["Месяц"] = None

        admin_df = filter_by_keywords(df, text_col, keywords_admin)
        wait_df = filter_by_keywords(df, text_col, keywords_wait)

        total = len(df)
        admin_count = len(admin_df)
        wait_count = len(wait_df)

        # KPI
        col1, col2, col3 = st.columns(3)
        col1.metric("Всего обращений", f"{total}")
        col2.metric("Регистратура / Администратор", f"{admin_count} ({admin_count/total:.1%})")
        col3.metric("Ожидание / Очередь", f"{wait_count} ({wait_count/total:.1%})")

        # Визуализация
        st.subheader("📊 Частота упоминаний тем")
        freq_df = pd.DataFrame({
            "Категория": ["Регистратура / Администратор", "Ожидание / Очередь"],
            "Количество": [admin_count, wait_count]
        })
        st.bar_chart(freq_df.set_index("Категория"))

        # Примеры обращений
        st.subheader("🧾 Примеры обращений с датами")

        def format_examples(df_examples):
            if "Дата" in df_examples.columns:
                df_examples = df_examples[["Дата", text_col]].copy()
            else:
                df_examples = df_examples[[text_col]].copy()
            df_examples = df_examples.rename(columns={text_col: "Текст обращения"})
            return df_examples.head(10).reset_index(drop=True)

        tabs = st.tabs(["Регистратура / Администратор", "Ожидание / Очередь"])

        with tabs[0]:
            st.dataframe(format_examples(admin_df))
        with tabs[1]:
            st.dataframe(format_examples(wait_df))

        # Скачивание Excel
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            admin_df.to_excel(writer, sheet_name="Регистратура_Администратор", index=False)
            wait_df.to_excel(writer, sheet_name="Ожидание_Очередь", index=False)
        st.download_button(
            "⬇️ Скачать результат (Excel)",
            data=output.getvalue(),
            file_name="filtered_obrasheniya.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        st.caption("BlackQuant Diagnostics — анализ обращений v1.1")

    except Exception as e:
        st.error(f"Ошибка при загрузке файла: {e}")
else:
    st.info("Загрузите Excel-файл для начала анализа.")
