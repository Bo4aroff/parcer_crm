import streamlit as st
import pandas as pd
import re
import io
import matplotlib.pyplot as plt

# ==========================
# НАСТРОЙКИ
# ==========================

st.set_page_config(page_title="Анализ обращений", layout="wide")
st.title("📋 Анализ обращений клиентов (Diagnostics v1.2)")

st.markdown(
    "Загрузите Excel-файл с обращениями. "
    "Система определит обращения, связанные с **регистратурой / администраторами** "
    "и **ожиданием / задержками**, покажет динамику по месяцам и примеры."
)

plt.rcParams.update({
    "axes.titlesize": 7,
    "axes.labelsize": 7,
    "xtick.labelsize": 7,
    "ytick.labelsize": 7,
    "legend.fontsize": 7,
})

keywords_admin = [
    "регистрат", "администрат", "ресепш", "записал", "запись не", "не приняли", "не дозвон",
    "не дозвониться", "ошибка при записи", "в регистратуре", "в регистратуру", "кассир", "касса"
]

keywords_wait = [
    "очеред", "ожидан", "ждать", "задерж", "поздно", "долго", "задержка", "задержали",
    "дозвон", "не отвеч", "звоню", "долго отвечали", "долго не"
]

# ==========================
# ФУНКЦИИ
# ==========================

def filter_by_keywords(data, text_col, keywords):
    pattern = r"\b(" + "|".join(keywords) + r")\b"
    mask = data[text_col].str.contains(pattern, flags=re.IGNORECASE, na=False)
    return data[mask].copy()

def monthly_counts(df, date_col):
    """Возвращает количество обращений по месяцам"""
    if date_col not in df.columns or df[date_col].isna().all():
        return pd.DataFrame()
    df["Месяц"] = df[date_col].dt.to_period("M").astype(str)
    return df.groupby("Месяц").size().reset_index(name="Количество")

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
        date_col = st.selectbox(
            "Выберите столбец с датой обращения (если есть):",
            ["— нет даты —"] + cols,
            index=0
        )

        df[text_col] = df[text_col].astype(str).str.lower()

        if date_col != "— нет даты —":
            df["Дата"] = pd.to_datetime(df[date_col], errors="coerce")
            df["Год"] = df["Дата"].dt.year
            df["Месяц"] = df["Дата"].dt.to_period("M").astype(str)
        else:
            df["Дата"] = pd.NaT
            df["Год"] = None
            df["Месяц"] = None

        # фильтрация
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

        # ==========================
        # ДИНАМИКА ПО МЕСЯЦАМ
        # ==========================
        if date_col != "— нет даты —":
            st.subheader("📈 Динамика обращений по месяцам")

            admin_trend = monthly_counts(admin_df, "Дата")
            wait_trend = monthly_counts(wait_df, "Дата")
            all_trend = monthly_counts(df, "Дата")

            trend_df = pd.merge(all_trend, admin_trend, on="Месяц", how="left", suffixes=("_всего", "_регистратура"))
            trend_df = pd.merge(trend_df, wait_trend, on="Месяц", how="left")
            trend_df.rename(columns={"Количество": "Ожидание"}, inplace=True)
            trend_df.fillna(0, inplace=True)

            # График 1 — абсолютные значения
            fig, ax = plt.subplots(figsize=(8, 3))
            ax.plot(trend_df["Месяц"], trend_df["Количество_регистратура"], marker="o", color="#E67E22", label="Регистратура / Администратор")
            ax.plot(trend_df["Месяц"], trend_df["Ожидание"], marker="o", color="#3498DB", label="Ожидание / Очередь")
            ax.set_title("Количество обращений по месяцам")
            ax.set_xlabel("Месяц")
            ax.set_ylabel("Количество обращений")
            ax.legend()
            ax.grid(axis="y", linestyle="--", alpha=0.5)
            plt.xticks(rotation=45)
            st.pyplot(fig)

            # График 2 — доля обращений (%)
            trend_df["%_регистратура"] = (trend_df["Количество_регистратура"] / trend_df["Количество_всего"] * 100).round(1)
            trend_df["%_ожидание"] = (trend_df["Ожидание"] / trend_df["Количество_всего"] * 100).round(1)

            fig2, ax2 = plt.subplots(figsize=(8, 3))
            ax2.plot(trend_df["Месяц"], trend_df["%_регистратура"], marker="o", color="#E67E22", label="% Регистратура / Админ")
            ax2.plot(trend_df["Месяц"], trend_df["%_ожидание"], marker="o", color="#3498DB", label="% Ожидание / Очередь")
            ax2.set_title("Доля проблемных обращений по месяцам (%)")
            ax2.set_xlabel("Месяц")
            ax2.set_ylabel("% обращений")
            ax2.legend()
            ax2.grid(axis="y", linestyle="--", alpha=0.5)
            plt.xticks(rotation=45)
            st.pyplot(fig2)

        # ==========================
        # ПРИМЕРЫ ОБРАЩЕНИЙ
        # ==========================
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

        # ==========================
        # СКАЧИВАНИЕ EXCEL
        # ==========================
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

        st.caption("BlackQuant Diagnostics — анализ обращений v1.2")

    except Exception as e:
        st.error(f"Ошибка при загрузке файла: {e}")
else:
    st.info("Загрузите Excel-файл для начала анализа.")
