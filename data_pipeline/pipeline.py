import re
import sqlite3
import requests
import pandas as pd
from bs4 import BeautifulSoup

BASE = "https://books.toscrape.com/catalogue/category/books/"
CATEGORIES = {"Travel": "travel_2", "Mystery": "mystery_3", "Sequential Art": "sequential-art_5"}
RATING_MAP = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}
GBP_TO_INR = 105.50  # fixed project-defined constant, no date reference
DB_PATH = "books.db"


# ---------- 1. SCRAPE ----------
def scrape_category(name, slug):
    rows, page = [], 1
    while True:
        url = f"{BASE}{slug}/index.html" if page == 1 else f"{BASE}{slug}/page-{page}.html"
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        resp.encoding = "utf-8"  # otherwise the £ symbol gets garbled
        soup = BeautifulSoup(resp.text, "html.parser")
        for art in soup.select("article.product_pod"):
            rows.append({
                "title": art.h3.a["title"],
                "price": art.select_one("p.price_color").text.strip(),
                "star_rating": art.select_one("p.star-rating")["class"][1],
                "availability": art.select_one("p.availability").text.strip(),
                "category": name,
            })
        if not soup.select_one("li.next"):
            break
        page += 1
    return rows


def scrape_all():
    all_rows = []
    for name, slug in CATEGORIES.items():
        all_rows.extend(scrape_category(name, slug))
    return pd.DataFrame(all_rows)


# ---------- 2. CLEAN + CONVERT ----------
def parse_in_stock(text):
    t = str(text).lower()
    if "out of stock" in t:
        return False
    if "in stock" in t:
        return True
    return None  # unexpected text -> row dropped below


def clean(df):
    before = len(df)
    df = df.copy()
    df["price_gbp"] = pd.to_numeric(df["price"].str.extract(r"(\d+\.?\d*)")[0], errors="coerce")
    df["rating"] = df["star_rating"].map(RATING_MAP)
    df["in_stock"] = df["availability"].map(parse_in_stock)
    df = df.dropna(subset=["price_gbp", "rating", "in_stock"])  # drop unparseable rows
    print(f"Rows before cleaning: {before}, dropped: {before - len(df)}, kept: {len(df)}")
    df["rating"] = df["rating"].astype(int)
    df["in_stock"] = df["in_stock"].astype(bool)
    df["price_inr"] = (df["price_gbp"] * GBP_TO_INR).round(2)
    return df[["title", "price_gbp", "price_inr", "rating", "in_stock", "category"]].reset_index(drop=True)


# ---------- 3. DATABASE ----------
SCHEMA = """
DROP TABLE IF EXISTS books;
DROP TABLE IF EXISTS categories;
CREATE TABLE categories (
    category_id INTEGER PRIMARY KEY,
    category_name TEXT UNIQUE
);
CREATE TABLE books (
    book_id INTEGER PRIMARY KEY,
    title TEXT,
    price_gbp REAL,
    price_inr REAL,
    rating INTEGER,
    in_stock INTEGER,
    category_id INTEGER REFERENCES categories(category_id)
);
"""


def build_frames(df):
    cats = pd.DataFrame({"category_name": df["category"].unique()})
    cats.insert(0, "category_id", range(1, len(cats) + 1))
    books = df.merge(cats, left_on="category", right_on="category_name")
    books = books.drop(columns=["category", "category_name"])
    books["in_stock"] = books["in_stock"].astype(int)
    books.insert(0, "book_id", range(1, len(books) + 1))
    return cats, books


def load_db(cats, books):
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)
    cats.to_sql("categories", conn, if_exists="append", index=False)
    books.to_sql("books", conn, if_exists="append", index=False)
    conn.commit()
    return conn


# ---------- 4. SQL QUERIES ----------
QUERIES = {
    "Q1 SELECT/WHERE/ORDER BY/LIMIT - 5 priciest books over 30 GBP":
        "SELECT title, price_gbp FROM books WHERE price_gbp > 30 ORDER BY price_gbp DESC LIMIT 5",
    "Q2 DISTINCT - distinct ratings":
        "SELECT DISTINCT rating FROM books ORDER BY rating",
    "Q3 IN - books rated 4 or 5":
        "SELECT title, rating, price_gbp FROM books WHERE rating IN (4, 5) ORDER BY title",
    "Q4 BETWEEN - books priced 10 to 20 GBP":
        "SELECT title, price_gbp FROM books WHERE price_gbp BETWEEN 10 AND 20 ORDER BY price_gbp",
    "Q5 JOIN - top 10 rated books (rating>=4) with category":
        """SELECT b.title, c.category_name, b.rating, b.price_gbp
           FROM books b JOIN categories c ON b.category_id = c.category_id
           WHERE b.rating >= 4
           ORDER BY b.rating DESC, b.price_gbp DESC, b.title ASC
           LIMIT 10""",
}


def run_queries(conn):
    with open("queries_output.txt", "w", encoding="utf-8") as f:
        for label, q in QUERIES.items():
            out = pd.read_sql(q, conn)
            block = f"=== {label} ===\n{q}\n\n{out.to_string(index=False)}\n\n"
            print(block)
            f.write(block)


# ---------- 5. read_sql vs merge ----------
def compare_join(conn, cats, books):
    sql_df = pd.read_sql(QUERIES["Q5 JOIN - top 10 rated books (rating>=4) with category"], conn)

    merged = books.merge(cats, on="category_id")  # no SQL
    merged = merged[merged["rating"] >= 4]
    merged = merged.sort_values(["rating", "price_gbp", "title"],
                                ascending=[False, False, True]).head(10)
    merged = merged[["title", "category_name", "rating", "price_gbp"]].reset_index(drop=True)

    print("=== read_sql result vs pd.merge result (side by side) ===")
    print(pd.concat([sql_df, merged], axis=1, keys=["read_sql", "pd.merge"]).to_string())
    print("\nEquivalent:", sql_df.equals(merged))


if __name__ == "__main__":
    raw = scrape_all()
    df = clean(raw)
    print(df.dtypes, "\nTotal books:", len(df), "| Categories:", df["category"].nunique())
    cats, books = build_frames(df)
    conn = load_db(cats, books)
    run_queries(conn)
    compare_join(conn, cats, books)
    conn.close()