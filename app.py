import streamlit as st
import pandas as pd
import os
import datetime as dt
import pytz
import csv
import requests
import sqlite3
import json
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
    os.environ["DATABASE"] = st.secrets["DATABASE_PATH"]


@st.cache_resource
def get_db() -> sqlite3.Connection:
    connection = sqlite3.connect(os.environ["DATABASE"])
    return connection


@st.cache_data(ttl="1 hour")
def fetch_square_data(start: dt.date, end: dt.date, **options):
    pass


@st.cache_data(ttl="1 hour")
def update_bookings():
    # https://www.bookeo.com/apiref/#tag/Bookings/paths/~1bookings/get
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM bookings")
    cur.execute("DELETE FROM participants")

    q1 = """INSERT INTO bookings (id, eventId, startTime, endTime,
        customerId, title, canceled, accepted, sourceIp, creationTime,
        creationAgent, productId, privateEvent, noShow)
        VALUES (:bookingNumber, :eventId, :startTime, :endTime,
        :customerId, :title, :canceled, :accepted, :sourceIp,
        :creationTime, :creationAgent, :productId, :privateEvent,
        :noShow)"""
    q2 = """INSERT INTO participants (bookingId, firstName,
        lastName, peopleCategory)
        VALUES (?, ?, ?, ?)"""

    start = dt.date(year=2023, month=1, day=1)
    start = dt.datetime.combine(start, dt.time(0, 0))
    end = dt.date.today()
    end = dt.datetime.combine(end, dt.time(23, 59, 59))
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
            bookings = res.json()["data"]
            cur.executemany(
                q1,
                [
                    {
                        "bookingNumber": b.get("bookingNumber"),
                        "eventId": b.get("eventId"),
                        "startTime": b.get("startTime"),
                        "endTime": b.get("endTime"),
                        "customerId": b.get("customerId"),
                        "title": b.get("title"),
                        "canceled": b.get("canceled"),
                        "accepted": b.get("accepted"),
                        "sourceIp": b.get("sourceIp"),
                        "creationTime": b.get("creationTime"),
                        "creationAgent": b.get("creationAgent"),
                        "productId": b.get("productId"),
                        "privateEvent": b.get("privateEvent"),
                        "noShow": b.get("noShow"),
                    }
                    for b in bookings
                ],
            )
            for booking in bookings:
                participant_data = booking["participants"]["details"]
                cur.executemany(
                    q2,
                    [
                        (
                            booking["bookingNumber"],
                            p.get("firstName"),
                            p.get("lastName"),
                            p["peopleCategoryId"],
                        )
                        for p in participant_data
                    ],
                )
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
                bookings = res.json()["data"]
                cur.executemany(
                    q1,
                    [
                        {
                            "bookingNumber": b.get("bookingNumber"),
                            "eventId": b.get("eventId"),
                            "startTime": b.get("startTime"),
                            "endTime": b.get("endTime"),
                            "customerId": b.get("customerId"),
                            "title": b.get("title"),
                            "canceled": b.get("canceled"),
                            "accepted": b.get("accepted"),
                            "sourceIp": b.get("sourceIp"),
                            "creationTime": b.get("creationTime"),
                            "creationAgent": b.get("creationAgent"),
                            "productId": b.get("productId"),
                            "privateEvent": b.get("privateEvent"),
                            "noShow": b.get("noShow"),
                        }
                        for b in bookings
                    ],
                )
                for booking in bookings:
                    participant_data = booking["participants"]["details"]
                    cur.executemany(
                        q2,
                        [
                            (
                                booking["bookingNumber"],
                                p.get("firstName"),
                                p.get("lastName"),
                                p["peopleCategoryId"],
                            )
                            for p in participant_data
                        ],
                    )
            page_number += 1
        block_start = block_end + dt.timedelta(days=1)

    conn.commit()
    cur.close()


# def extract_booking_participants(data: list[dict]) -> pd.DataFrame:
def extract_booking_participants(data: list[dict]) -> None:
    # TODO: Implement this method to enable transition from JSON to SQL
    if not data:
        return
    df = pd.json_normalize(data)
    print(df.columns)
    print(df["participants.numbers"].tolist())
    print(df["participants.details"].tolist())
    pass


@st.cache_data(ttl="1 hour")
def update_group_categories():
    return
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM groupCategories")
    cur.close()


def get_group_options() -> list[str]:
    update_group_categories()
    return []


def extract_group_category(data: dict) -> str:
    return ""


@st.cache_data(ttl="1 hour")
def update_people_categories():
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
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM peopleCategories")
    q = """INSERT INTO peopleCategories (id, name)
        VALUES (:id, :name)"""
    cur.executemany(q, data["categories"])
    conn.commit()
    cur.close()


def get_people_categories() -> list[str]:
    update_people_categories()
    conn = get_db()
    cur = conn.cursor()
    q = "SELECT name FROM peopleCategories"
    names = cur.execute(q).fetchall()
    cur.close()
    return [n[0] for n in names]


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
    cur = conn.cursor()
    cur.execute("DELETE FROM PRODUCTS")
    names = [(p["name"], p["productCode"]) for p in data["data"]]
    q = """INSERT INTO products (name, id)
        VALUES (?, ?)"""
    cur.executemany(q, names)
    conn.commit()
    cur.close()


def get_products() -> list[str]:
    update_products()
    conn = get_db()
    cur = conn.cursor()
    q = "SELECT name FROM products"
    names = cur.execute(q).fetchall()
    cur.close()
    return [n[0] for n in names]


def get_rooms_booked(start: dt.date, end: dt.date, **options) -> int:
    update_bookings()
    conn = get_db()
    cur = conn.cursor()
    params = {"start": start, "end": end}
    q = """SELECT COUNT(DISTINCT creationTime)
        FROM bookings
        WHERE creationTime BETWEEN :start AND :end
        AND NOT canceled """
    if options["product"]:
        sq = "SELECT id FROM products WHERE name IN (SELECT value FROM json_each(?))"
        product_ids = cur.execute(sq, (json.dumps(options["product"]),)).fetchall()
        q += " AND productId IN (SELECT value FROM json_each(:product_ids)) "
        params["product_ids"] = json.dumps([p[0] for p in product_ids])
    count = cur.execute(q, params).fetchone()
    cur.close()
    return count[0]


def get_slots_booked(start: dt.date, end: dt.date, **options) -> int:
    update_bookings()
    conn = get_db()
    cur = conn.cursor()
    params = {"start": start, "end": end}
    q = """SELECT COUNT(*)
        FROM participants p JOIN bookings b
        ON p.bookingId=b.id
        WHERE creationTime BETWEEN :start AND :end"""
    if options["product"]:
        sq = "SELECT id FROM products WHERE name IN (SELECT value FROM json_each(?))"
        product_ids = cur.execute(sq, (json.dumps(options["product"]),)).fetchall()
        q += " AND productId IN (SELECT value FROM json_each(:product_ids)) "
        params["product_ids"] = json.dumps([p[0] for p in product_ids])
    count = cur.execute(q, params).fetchone()
    cur.close()
    return count[0]


def get_rooms_run(start: dt.date, end: dt.date, **options) -> int:
    update_bookings()
    conn = get_db()
    cur = conn.cursor()
    params = {"start": start, "end": end}
    q = """SELECT COUNT(DISTINCT startTime)
        FROM bookings
        WHERE startTime BETWEEN :start AND :end
        AND NOT canceled """
    if options["product"]:
        sq = "SELECT id FROM products WHERE name IN (SELECT value FROM json_each(?))"
        product_ids = cur.execute(sq, (json.dumps(options["product"]),)).fetchall()
        q += " AND productId IN (SELECT value FROM json_each(:product_ids)) "
        params["product_ids"] = json.dumps([p[0] for p in product_ids])
    count = cur.execute(q, params).fetchone()
    cur.close()
    return count[0]


def get_slots_run(start: dt.date, end: dt.date, **options) -> int:
    update_bookings()
    conn = get_db()
    cur = conn.cursor()
    params = {"start": start, "end": end}
    q = """SELECT COUNT(*)
        FROM participants p JOIN bookings b
        ON p.bookingId=b.id
        WHERE startTime BETWEEN :start AND :end"""
    if options["product"]:
        sq = "SELECT id FROM products WHERE name IN (SELECT value FROM json_each(?))"
        product_ids = cur.execute(sq, (json.dumps(options["product"]),)).fetchall()
        q += " AND productId IN (SELECT value FROM json_each(:product_ids)) "
        params["product_ids"] = json.dumps([p[0] for p in product_ids])
    count = cur.execute(q, params).fetchone()
    cur.close()
    return count[0]


def get_revenue(start: dt.date, end: dt.date, **options) -> int:
    return -1


def generate_report(start: dt.date, end: dt.date, **options):
    square_data = fetch_square_data(start, end, **options)
    # print(start)
    # print(end)
    # print(options)
    rooms_booked = get_rooms_booked(start, end, **options)
    slots_booked = get_slots_booked(start, end, **options)
    rooms_run = get_rooms_run(start, end, **options)
    slots_run = get_slots_run(start, end, **options)
    revenue = get_revenue(start, end, **options)
    st.write(f"Rooms booked: {rooms_booked}")
    st.write(f"Slots booked: {slots_booked}")
    st.write(f"Rooms run: {rooms_run}")
    st.write(f"Slots run: {slots_run}")
    rooms_run = 0
    slots_run = 0


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
            "Pricing category",
            options=get_people_categories(),
            placeholder="All categories",
        ),
        "groupcat": st.multiselect(
            "Group category", options=get_group_options(), placeholder="All categories"
        ),
        "product": st.multiselect(
            "Product", options=get_products(), placeholder="All products"
        ),
    }
    # "booking_revenue": st.checkbox("Booking revenue"),
    # "invoice_revenue": st.checkbox("Invoice revenue"),
    # "cost_of_labor": st.checkbox("Cost of labor"),
    # "wages": st.checkbox("Wages"),
    # "bonuses": st.checkbox("Bonuses"),
    # "contact_method": st.checkbox("Contact method"),
    force_cache_refresh = st.checkbox("Force cache refresh?")
    if force_cache_refresh:
        st.cache_data.clear()
    report_btn = st.button("Generate report")
    if report_btn:
        report = generate_report(start_date, end_date, **report_options)


if __name__ == "__main__":
    init_keys()
    main()
