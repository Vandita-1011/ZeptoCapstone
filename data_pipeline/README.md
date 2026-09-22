# Module 1 - Data Pipeline

This module scrapes book data from a website, cleans it, converts the prices, stores
everything in a normalized SQLite database, and queries it using both SQL and pandas.

## Files in this folder

| File | Purpose |
|---|---|
| `pipeline.py` | The complete pipeline: scrape, clean, convert, load into the database, run queries, compare SQL with pandas |
| `requirements.txt` | Libraries needed for this module |
| `books.db` | The SQLite database produced by the pipeline |
| `queries_output.txt` | Each SQL query with its output |
| `README.md` | This file |

## Setup and how to run

This module has its own `requirements.txt` (one per module, not one consolidated file).

1. Install the libraries:

        pip install -r requirements.txt

2. Run the pipeline from inside this folder:

        python pipeline.py

An internet connection is needed because the data is scraped live. The script runs end
to end with no manual copying or pasting. It creates `books.db` and
`queries_output.txt` in this folder. Running it again rebuilds the database from scratch.

## Data source and scope

The data comes from books.toscrape.com, a public website built for scraping practice.
It needs no login, no API key and no payment. I used the `requests` and `BeautifulSoup`
libraries and scraped every book listed in three categories, following the pagination
of each category page:

| Category | Books |
|---|---|
| Travel | 11 |
| Mystery | 32 |
| Sequential Art | 75 |
| **Total** | **118** |

For each book I captured the title, the price as listed (in GBP), the star rating as
text (for example "Three"), the availability text and the category.

## Cleaning

| Raw field | Clean column | Type | What I did |
|---|---|---|---|
| price (for example `£51.77`) | `price_gbp` | float | Removed the currency symbol and converted to a number |
| star rating text (`One` to `Five`) | `rating` | int (1 to 5) | Mapped the words to numbers |
| availability text (for example `In stock`) | `in_stock` | bool | True if the text says in stock, False if it says out of stock |

**Handling rows that fail to parse:** if any field cannot be read (for example
unexpected text in the rating or availability), that row is dropped and the pipeline
carries on without crashing. I chose dropping over median imputation because an
invented price or rating would make the pricing data misleading, and losing a single
row costs very little. The script prints how many rows were dropped. In my run, 118
rows were scraped, 0 were dropped and 118 were kept.

## Currency conversion

The `price_inr` column is calculated as `price_gbp * 105.50`, rounded to 2 decimals.

**1 GBP = 105.50 INR.** This is a fixed, project-defined constant. It is not a live or
historical market rate, so there is no lookup, no API call and no date involved.

## Database design

The SQLite database (`books.db`) has two tables linked by a primary key / foreign key
relationship:

**categories**

| Column | Type | Notes |
|---|---|---|
| `category_id` | INTEGER | Primary key |
| `category_name` | TEXT | Unique |

**books**

| Column | Type | Notes |
|---|---|---|
| `book_id` | INTEGER | Primary key |
| `title` | TEXT | |
| `price_gbp` | REAL | |
| `price_inr` | REAL | |
| `rating` | INTEGER | 1 to 5 |
| `in_stock` | INTEGER | 1 = in stock, 0 = not in stock |
| `category_id` | INTEGER | Foreign key referencing `categories(category_id)` |

The tables are created with the schema written in `pipeline.py`, and the cleaned data
is inserted using `pandas.DataFrame.to_sql`.

## SQL queries

Five queries are run against the database. Each query and its output is printed when
the script runs and saved in `queries_output.txt`.

| # | Clauses covered | Question answered |
|---|---|---|
| 1 | SELECT, WHERE, ORDER BY, LIMIT | The 5 most expensive books priced over 30 GBP |
| 2 | DISTINCT | The distinct ratings present in the data |
| 3 | IN | Books rated 4 or 5 |
| 4 | BETWEEN | Books priced between 10 and 20 GBP |
| 5 | JOIN | The top 10 highest-rated books (rating 4 or above) with their category names |

The JOIN query:

```sql
SELECT b.title, c.category_name, b.rating, b.price_gbp
FROM books b JOIN categories c ON b.category_id = c.category_id
WHERE b.rating >= 4
ORDER BY b.rating DESC, b.price_gbp DESC, b.title ASC
LIMIT 10
```

## SQL results read into pandas, and the pandas merge

All query results are read into pandas DataFrames with `pd.read_sql(...)`.

For the JOIN query, I also reproduced the result without any SQL. I merged the
in-memory `books` and `categories` DataFrames with `pd.merge`, then filtered for
rating 4 or above, sorted, and took the top 10. The script prints the `read_sql`
result and the `pd.merge` result side by side and checks whether they are equal.
Both approaches give identical output (`Equivalent: True`).