import json
import os
import sqlite3

import pandas as pd
import streamlit as st

DB_FILE = "app.db"
SOURCES = {"ingredients": "ingredients_results.csv"}
SUMMARY_FILE = "ingredients_summary.json"  # optional: full-site totals from make_summary.py
SAMPLE_LIMIT = 1000
DISCLAIMER = (f"**Disclaimer:** this table contains only the first {SAMPLE_LIMIT:,} product records. "
              "The full extraction takes a very long time, so a sample was collected to keep "
              "the process within the available time. The scraper itself is built to collect every record.")

st.set_page_config(page_title="Scraping Challenge Explorer", layout="wide")


@st.cache_resource
def get_connection():
    """Load each CSV into SQLite once per app start (data persistence layer)."""
    con = sqlite3.connect(DB_FILE, check_same_thread=False)
    for table, path in SOURCES.items():
        if os.path.exists(path):
            pd.read_csv(path, keep_default_na=False).to_sql(table, con, index=False, if_exists="replace")
    return con


@st.cache_data
def load_table(table):
    con = get_connection()
    exists = con.execute("SELECT name FROM sqlite_master WHERE name=?", (table,)).fetchone()
    return pd.read_sql(f"SELECT * FROM {table}", con) if exists else None


def ingredients_tab():
    df = load_table("ingredients")
    if df is None:
        st.info("ingredients_results.csv not found.")
        return

    st.info(DISCLAIMER)

    if os.path.exists(SUMMARY_FILE):
        with open(SUMMARY_FILE, encoding="utf-8") as f:
            s = json.load(f)
        cols = st.columns(5)
        cols[0].metric("Total ingredients (whole site)", f"{s['total_ingredients']:,}")
        cols[1].metric("Total finished products (whole site)", f"{s['total_finished_products']:,}")
        cols[2].metric("Companies: Herbs, Spices", f"{s['companies_herbs_spices']:,}")
        cols[3].metric("Companies: Physical Formats", f"{s['companies_physical_formats']:,}")
        cols[4].metric("Companies: Cognitive & Mental Health", f"{s['companies_cognitive_mental_health']:,}")
        st.caption(f"Metrics above are full-site totals from the category listings. "
                   f"The table below shows only the {len(df):,} sampled product records.")
    else:
        cols = st.columns(3)
        cols[0].metric("Ingredient records (sample)", int(df["Record Type"].str.contains("Ingredient").sum()))
        cols[1].metric("Finished product records (sample)", int(df["Record Type"].str.contains("Finished").sum()))
        cols[2].metric("Unique companies (sample)", df["Company ID"].nunique())

    f1, f2, f3 = st.columns(3)
    kinds = f1.multiselect("Record type", sorted(df["Record Type"].unique()))
    countries = f2.multiselect("Country", sorted(c for c in df["Country"].unique() if c))
    search = f3.text_input("Search product, company or category", key="ing_search")

    view = df
    if kinds:
        view = view[view["Record Type"].isin(kinds)]
    if countries:
        view = view[view["Country"].isin(countries)]
    if search:
        text = view["Product Name"] + " " + view["Company Name"] + " " + view["Category"]
        view = view[text.str.contains(search, case=False, regex=False)]

    left, right = st.columns([2, 1])
    left.subheader(f"{len(view):,} products")
    show = [c for c in ["Product Name", "Record Type", "Category", "Company Name", "Country", "Company Type"]
            if c in view.columns]
    left.dataframe(view[show], width="stretch", hide_index=True)
    left.download_button("Download filtered CSV", view.to_csv(index=False).encode("utf-8-sig"),
                         "ingredients_filtered.csv", "text/csv", key="dl_ing")
    right.subheader("Top countries")
    right.bar_chart(view[view["Country"] != ""]["Country"].value_counts().head(10))


st.title("IngredientsNetwork Explorer")
st.caption("Data scraped from ingredientsnetwork.com, stored in SQLite.")
ingredients_tab()
