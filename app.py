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
def init_db() -> sqlite3.Connection:
    # TODO: Design schema, implement database
    pass


@st.cache_data(ttl="1 hour")
def fetch_square_data(start: dt.date, end: dt.date) -> dict:
    pass


@st.cache_data(ttl="1 hour")
def fetch_bookeo_data(start: dt.date, end: dt.date) -> list[dict]:
    # https://www.bookeo.com/apiref/#tag/Bookings/paths/~1bookings/get
    start = dt.datetime.combine(start, dt.time(0, 0))
    end = dt.datetime.combine(end, dt.time(23, 59))

    day_range = (end - start).days
    data = []
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


def extract_bookeo_rows(data: list[dict]) -> pd.DataFrame:
    # TODO: Implement this method to enable transition from JSON to SQL
    pass


@st.cache_data(ttl="7 days")
def fetch_group_categories() -> dict:
    pass


def extract_group_category(data: dict) -> str:
    pass


@st.cache_data(ttl="7 days")
def fetch_people_categories() -> dict:
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
        return {}
    return {c["id"]: c["name"] for c in data["categories"]}


def people_category(id: str) -> str:
    categories = fetch_people_categories()
    return categories.get(id, "ID not found")


@st.cache_data(ttl="7 days")
def fetch_products() -> list:
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
        return {}
    return [p["name"] for p in data["data"]]


@st.cache_data(ttl="15 minutes")
def generate_report(start: dt.date, end: dt.date, **options):
    square_data = fetch_square_data(start, end)
    bookeo_data = fetch_bookeo_data(start, end)
    bookeo_rows = extract_bookeo_rows(bookeo_data)
    if options["product"]:
        bookeo_data = [
            b for b in bookeo_data if b.get("productName", "") in options["product"]
        ]
    print(len(bookeo_data))


def main():
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
        "rooms_booked": st.checkbox("Rooms booked"),
        "slots_booked": st.checkbox("Slots booked"),
        "rooms_run": st.checkbox("Rooms run"),
        "slots_run": st.checkbox("Slots run"),
        "cost_of_labor": st.checkbox("Cost of labor"),
        "wages": st.checkbox("Wages"),
        "bonuses": st.checkbox("Bonuses"),
        "pricing_category": st.checkbox("Pricing category"),
        "group_category": st.checkbox("Group category"),
        "contact_method": st.checkbox("Contact method"),
    }

    report_btn = st.button("Generate report")
    if report_btn:
        report = generate_report(start_date, end_date, **report_options)


if __name__ == "__main__":
    init_keys()
    conn = init_db()

    PricingCategory = Enum("Price", [x for x in fetch_people_categories().values()])
    pricing_options = [p.name for p in PricingCategory]
    GroupCategory = Enum("Group", [])
    group_options = [g.name for g in GroupCategory]

    Product = Enum("Product", [x for x in fetch_products()])
    product_options = [p.name for p in Product]

    main()
