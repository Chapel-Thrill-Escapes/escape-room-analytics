import streamlit as st
import pandas as pd
import os
import datetime as dt
import pytz
import csv
import requests
import sqlite3
from enum import Enum

# TODO:
# -> Square functionality <-
# Revenue
# - Bookings
# - Invoices
# Cost of labor
# - Hourly wages
# - Bonuses
# -> Bookeo functionality <-
# Rooms/slots booked
# Rooms/slots run
# Fill rate (low priority)
# Customer segmentation
# - Pricing category
# - Group category
# - Contact method
# -> Google functionality <-
# Number of reviews (low priority)
# Reviews by quality (low priority)
# -> Security features <-
# Login screen: https://blog.streamlit.io/streamlit-authenticator-part-1-adding-an-authentication-component-to-your-app/

ZULU_FORMAT = "%Y-%m-%dT%H:%M:00Z"


def init_keys():
    os.environ["USER_AGENT"] = "CTE Sales Report Engine v0.1"
    # os.environ["SQUARE_API_KEY"] = st.secrets["SQUARE_API_KEY"]
    os.environ["BOOKEO_API_KEY"] = st.secrets["BOOKEO_API_KEY"]
    os.environ["BOOKEO_SECRET_KEY"] = st.secrets["BOOKEO_SECRET_KEY"]


@st.cache_resource
def get_db() -> sqlite3.Connection:
    # TODO: Design schema, implement database
    pass


@st.cache_data(ttl="1 hour")
def fetch_square_data(start: dt.date, end: dt.date) -> dict:
    pass


@st.cache_data(ttl="1 hour", show_spinner="Fetching latest data from Bookeo...")
def update_bookings():
    # https://www.bookeo.com/apiref/#tag/Bookings/paths/~1bookings/get
    # start = dt.datetime.combine(start, dt.time(0, 0))
    # end = dt.datetime.combine(end, dt.time(23, 59))
    conn = get_db()
    qd = "DELETE FROM bookings"
    conn.execute(qd)
    qd = "DELETE FROM participants"
    conn.execute(qd)
    q1 = """INSERT INTO bookings
        VALUES ..."""
    q2 = """INSERT INTO participants
        VALUES ..."""
    end = dt.date.today()
    start = dt.date(year=2023, month=1, day=1)
    day_range = (end - start).days
    block_start = start
    for _ in range((day_range // 31) + 1):
        block_end = block_start + dt.timedelta(days=31)
        block_end = min(block_end, end)
        res = requests.get(
            "https://api.bookeo.com/v2/bookings",
            params={
                "startTime": block_start.strftime(ZULU_FORMAT),
                "endTime": block_end.strftime(ZULU_FORMAT),
                "secretKey": os.environ["BOOKEO_SECRET_KEY"],
                "apiKey": os.environ["BOOKEO_API_KEY"],
                "expandParticipants": True,
                "itemsPerPage": 100,
            },
            headers={"User-Agent": os.environ["USER_AGENT"]},
        )
        if res.status_code == 200:
            conn.execute(q1, ...)
            data.extend(res.json()["data"])
        page_token = res.json()["info"].get("pageNavigationToken")
        total_pages = res.json()["info"]["totalPages"]
        page_number = 2

        while page_number <= total_pages:
            res = requests.get(
                "https://api.bookeo.com/v2/bookings",
                params={
                    "pageNavigationToken": page_token,
                    "pageNumber": page_number,
                    "secretKey": os.environ["BOOKEO_SECRET_KEY"],
                    "apiKey": os.environ["BOOKEO_API_KEY"],
                },
                headers={"User-Agent": os.environ["USER_AGENT"]},
            )
            if res.status_code == 200:
                data.extend(res.json()["data"])
            page_number += 1
        block_start = block_end + dt.timedelta(days=1)

    return data


# This function is likely not necessary.
# def get_bookings(start: dt.date, end: dt.date) -> pd.DataFrame:
#     conn = get_db()
#     q = """SELECT *
#     FROM bookings
#     WHERE startTime BETWEEN ? AND ?"""
#     bookings = conn.execute(q, (start, end)).fetchall()
#     return pd.DataFrame(bookings)


def extract_booking_participants(data: list[dict]) -> pd.DataFrame:
    # TODO: Implement this method to enable transition from JSON to SQL
    if not data:
        return pd.DataFrame()
    df = pd.json_normalize(data)
    print(df.columns)
    print(df["participants.numbers"].tolist())
    print(df["participants.details"].tolist())
    pass


@st.cache_data(ttl="1 hour")
def update_group_categories() -> dict:
    conn = get_db()
    q = """"""


def extract_group_category(data: dict) -> str:
    pass


@st.cache_data("1 hour")
def update_people_categories() -> dict:
    # https://www.bookeo.com/apiref/#tag/Settings/paths/~1settings~1peoplecategories/get
    res = requests.get(
        "https://api.bookeo.com/v2/settings/peoplecategories",
        params={
            "secretKey": os.environ["BOOKEO_SECRET_KEY"],
            "apiKey": os.environ["BOOKEO_API_KEY"],
        },
        headers={"User-Agent": os.environ["USER_AGENT"]},
    )
    data = res.json()
    if "categories" not in data.keys():
        return
    cats = [(c["id"], c["name"]) for c in data["categories"]]
    conn = get_db()
    q = "DELETE FROM peopleCategories"
    conn.execute(q)
    q = """INSERT INTO peopleCategories (id, name)
        VALUES (?, ?)"""
    conn.executemany(q, cats)
    conn.cursor().commit()


def get_people_categories() -> list[str]:
    conn = get_db()
    q = "SELECT name FROM peopleCategories"
    names = conn.execute(q).fetchall()
    return [n for n in names]


def people_category(id: str) -> str:
    conn = get_db()
    q = """SELECT name
        FROM peopleCategories
        WHERE id=?"""
    name = conn.execute(q, (id,)).fetchone()[0]
    return name or "ID not found"


@st.cache_data(ttl="1 hour")
def update_products():
    # https://www.bookeo.com/apiref/#tag/Settings/paths/~1settings~1products/get
    res = requests.get(
        "https://api.bookeo.com/v2/settings/products",
        params={
            "secretKey": os.environ["BOOKEO_SECRET_KEY"],
            "apiKey": os.environ["BOOKEO_API_KEY"],
            "itemsPerPage": 100,
        },
        headers={"User-Agent": os.environ["USER_AGENT"]},
    )
    data = res.json()
    if res.status_code != 200 or "data" not in data.keys():
        return
    conn = get_db()
    q = "DELETE FROM PRODUCTS"
    conn.execute(q)
    names = [p["name"] for p in data["data"]]
    q = """INSERT INTO products (name)
        VALUES (?)"""
    conn.executemany(q, (names,))
    conn.cursor().commit()


def get_products() -> list[str]:
    conn = get_db()
    q = "SELECT name FROM products"
    return conn.execute(q).fetchall()


def get_rooms_booked(start: dt.date, end: dt.date) -> int:
    conn = get_db()
    q = """SELECT COUNT(*)
        FROM bookings
        WHERE startTime BETWEEN ? AND ?"""
    return conn.execute(q, (start, end)).fetchone()


def get_slots_booked(start: dt.date, end: dt.date) -> int:
    conn = get_db()
    q = """SELECT COUNT(*)
        FROM participants p JOIN bookings b
        ON p.bookingId=b.id
        WHERE startTime BETWEEN ? AND ?"""
    return conn.execute(q, (start, end)).fetchone()


def generate_report(start: dt.date, end: dt.date, **options):
    square_data = fetch_square_data(start, end)
    bookeo_data = fetch_bookeo_data(start, end, **options)
    bookeo_rows = extract_booking_participants(bookeo_data)
    if options["product"]:
        bookeo_data = [
            b for b in bookeo_data if b.get("productName", "") in options["product"]
        ]
    rooms_booked = get_rooms_booked()
    slots_booked = get_slots_booked()
    rooms_run = 0
    slots_run = 0
    print(len(bookeo_data))


def main():
    update_bookings()
    st.write("# Escape Room Analytics")
    today = dt.datetime.now(pytz.timezone("US/Eastern"))
    start_date = st.date_input(
        "Start date",
        max_value=today,
        key="start_date",
        format="MM/DD/YYYY",
    )
    end_date = st.date_input(
        "End date",
        max_value=today,
        key="end_date",
        format="MM/DD/YYYY",
    )
    if end_date - start_date < dt.timedelta(days=0):
        st.write("*End date cannot be before start date!*")
        return
    st.write("## Parameters")
    report_options = {
        "pricingcat": st.multiselect(
            "Pricing category", options=pricing_options, placeholder="All categories"
        ),
        "groupcat": st.multiselect(
            "Group category", options=group_options, placeholder="All categories"
        ),
        "product": st.multiselect(
            "Product", options=product_options, placeholder="All products"
        ),
        "revenue": st.checkbox("Total revenue"),
        "booking_revenue": st.checkbox("Booking revenue"),
        "invoice_revenue": st.checkbox("Invoice revenue"),
        "cost_of_labor": st.checkbox("Cost of labor"),
        "wages": st.checkbox("Wages"),
        "bonuses": st.checkbox("Bonuses"),
        "contact_method": st.checkbox("Contact method"),
    }

    report_btn = st.button("Generate report")
    force_cache_refresh = st.checkbox("Force cache refresh?")
    if report_btn:
        if force_cache_refresh:
            update_bookings.clear()
        report = generate_report(start_date, end_date, **report_options)


if __name__ == "__main__":
    init_keys()
    conn = get_db()

    pricing_options = [p for p in get_people_categories()]
    GroupCategory = Enum("Group", [])
    group_options = [g.name for g in GroupCategory]

    Product = Enum("Product", [x for x in get_products()])
    product_options = [p.name for p in Product]

    main()
