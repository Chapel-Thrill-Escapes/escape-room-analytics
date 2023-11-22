import datetime as dt
import email
import imaplib
import json
import os
import sqlite3
from csv import DictReader

import pandas as pd
import pytz
import requests
import streamlit as st

# TODO:
# -> Square functionality <-
# https://developer.squareup.com/reference/square/orders-api
# https://developer.squareup.com/reference/square/payments-api
# https://developer.squareup.com/reference/square/catalog-api
# Revenue
# - Bookings
# - Invoices
# Cost of labor
# - Hourly wages
# - Bonuses
# -> Bookeo functionality <-
# Fill rate (low priority)
# Customer segmentation
# - Group category
# - Contact method
# -> Google functionality <-
# Number of reviews (low priority)
# Reviews by quality (low priority)

ZULU_FORMAT = "%Y-%m-%dT%H:%M:00Z"


def BookeoUpdate(func):
    def wrapper(*args, **kwargs):
        update_bookings()
        return func(*args, **kwargs)

    return wrapper


def init_keys():
    os.environ["USER_AGENT"] = "CTE Sales Report Engine v0.1"
    # os.environ["SQUARE_API_KEY"] = st.secrets["SQUARE_API_KEY"]
    os.environ["BOOKEO_API_KEY"] = st.secrets["BOOKEO_API_KEY"]
    os.environ["BOOKEO_SECRET_KEY"] = st.secrets["BOOKEO_SECRET_KEY"]
    os.environ["DATABASE"] = st.secrets["DATABASE_PATH"]
    os.environ["IMAP_SERVER"] = st.secrets["IMAP_SERVER"]
    os.environ["EMAIL"] = st.secrets["EMAIL"]
    os.environ["EMAIL_PASSWORD"] = st.secrets["EMAIL_PASSWORD"]
    os.environ["ROSTER_SUBJECT"] = st.secrets["ROSTER_SUBJECT"]
    os.environ["ROSTER_SENDER"] = st.secrets["ROSTER_SENDER"]
    os.environ["TEMPFILE"] = st.secrets["TEMPFILE"]


def init_db():
    db_path = os.environ["DATABASE"]
    open(db_path, "w+").close()  # create file if not exists
    # Set up tables
    connection = sqlite3.connect(db_path, check_same_thread=False)
    cur = connection.cursor()
    try:
        cur.execute(
            """CREATE TABLE IF NOT EXISTS bookings (
            id INT PRIMARY KEY,
            eventId INT NOT NULL,
            startTime TEXT NOT NULL,
            endTime TEXT NOT NULL,
            customerId TEXT,
            title TEXT,
            canceled INT NOT NULL CHECK(canceled=0 OR canceled=1),
            accepted INT NOT NULL CHECK(accepted=0 OR accepted=1),
            sourceIP TEXT,
            creationTime TEXT NOT NULL,
            privateEvent INT NOT NULL CHECK(privateEvent=0 OR privateEvent=1),
            noShow INT NOT NULL CHECK(noShow=0 OR noShow=1),
            productId TEXT NOT NULL,
            creationAgent TEXT,
            FOREIGN KEY(productId) REFERENCES products(id))"""
        )
        cur.execute(
            """CREATE TABLE IF NOT EXISTS participants (
            bookingId INT NOT NULL,
            firstName TEXT,
            lastName TEXT,
            peopleCategory TEXT,
            pid INT,
            FOREIGN KEY(peopleCategory) REFERENCES peopleCategories(id),
            FOREIGN KEY(bookingId) REFERENCES bookings(id))"""
        )
        cur.execute(
            """CREATE TABLE IF NOT EXISTS peopleCategories (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL)"""
        )
        cur.execute(
            """CREATE TABLE IF NOT EXISTS products (
            id TEXT PRIMARY KEY,
            name TEXT)"""
        )
        cur.execute(
            """CREATE TABLE IF NOT EXISTS onCampusPids (
            pid INT PRIMARY KEY,
            firstName TEXT,
            lastName TEXT)"""
        )
        connection.commit()
    finally:
        cur.close()


@st.cache_resource
def get_db() -> sqlite3.Connection:
    connection = sqlite3.connect(os.environ["DATABASE"], check_same_thread=False)
    return connection


@st.cache_data(ttl="12 hours", show_spinner="Fetching on-campus PIDs...")
def update_roster():
    # https://gist.github.com/kngeno/5337e543eb72174a6ac95e028b3b6456
    with imaplib.IMAP4_SSL(os.environ["IMAP_SERVER"], port=993) as imap:
        val, _ = imap.login(os.environ["EMAIL"], os.environ["EMAIL_PASSWORD"])
        if val != "OK":
            return

        imap.select("Inbox")
        val, f = imap.search(
            None,
            f'(FROM "{os.environ["ROSTER_SENDER"]}" SUBJECT "{os.environ["ROSTER_SUBJECT"]}")',
        )
        if val != "OK":
            return

        # Fetch from IMAP, download roster to temp file
        with open(os.environ["TEMPFILE"], "wb") as temp:
            for id in reversed(f[0].split()):
                val, msgParts = imap.fetch(id, "(RFC822)")
                if val != "OK":
                    continue
                mail = msgParts[0][1]
                mail = mail.decode("utf-8")
                mail = email.message_from_string(mail)
                for part in mail.walk():
                    fname = part.get_filename()
                    if fname:
                        temp.write(part.get_payload(decode=True))
                        escape = True
                        break
                if escape:
                    break

        with open(os.environ["TEMPFILE"], "r") as f:
            roster = DictReader(f)
            roster = list(roster)  # iterable -> list[dict]

            for key in roster[0].keys():
                if "pid" in key.lower():
                    pidKey = key
                elif "first" in key.lower():
                    firstNameKey = key
                elif "last" in key.lower():
                    lastNameKey = key

            if None in [pidKey, firstNameKey, lastNameKey]:
                print("Could not read roster")
                return

            conn = get_db()
            cur = conn.cursor()
            try:
                cur.execute("DELETE FROM onCampusPids")
                # The roster may contain duplicate entries... let's ignore them
                q = """INSERT OR IGNORE INTO onCampusPids (pid, firstName, lastName)
                        VALUES (?, ?, ?)"""
                roster = [(r[pidKey], r[firstNameKey], r[lastNameKey]) for r in roster]
                cur.executemany(q, roster)
                conn.commit()
            finally:
                cur.close()
                os.remove(os.environ["TEMPFILE"])


@st.cache_data(ttl="1 hour", show_spinner="Fetching latest bookings...")
def update_bookings():
    # https://www.bookeo.com/apiref/#tag/Bookings/paths/~1bookings/get
    conn = get_db()
    cur = conn.cursor()
    try:
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
            lastName, peopleCategory, pid)
            VALUES (?, ?, ?, ?, ?)"""

        start = dt.date(year=2023, month=1, day=1)
        start = dt.datetime.combine(start, dt.time(0, 0, 0))
        end = dt.datetime.now()
        day_range = (end - start).days
        block_start = start
        for b in range(day_range // 30):
            block_start = start + dt.timedelta(days=31 * b)
            block_end = block_start + dt.timedelta(days=30)
            block_end = dt.datetime.combine(block_end, dt.time(23, 59, 59))
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
                    for p in participant_data:
                        if p.get("personDetails") is None:
                            p["firstName"] = None
                            p["lastName"] = None
                    cur.executemany(
                        q2,
                        [
                            (
                                booking["bookingNumber"],
                                p.get("firstName"),
                                p.get("lastName"),
                                p["peopleCategoryId"],
                                extract_pid(p),
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
                        for p in participant_data:
                            if p.get("personDetails") is None:
                                p["firstName"] = None
                                p["lastName"] = None
                        cur.executemany(
                            q2,
                            [
                                (
                                    booking["bookingNumber"],
                                    p.get("firstName"),
                                    p.get("lastName"),
                                    p["peopleCategoryId"],
                                    extract_pid(p),
                                )
                                for p in participant_data
                            ],
                        )
                page_number += 1

        conn.commit()
    finally:
        cur.close()


def extract_pid(participant: dict) -> str:
    try:
        for f in participant["personDetails"]["customFields"]:
            if f["name"] == "PID":
                return f["value"]
        return None
    except:
        return None


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
    if res.status_code != 200 or "categories" not in data.keys():
        return
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM peopleCategories")
        q = """INSERT INTO peopleCategories (id, name)
            VALUES (:id, :name)"""
        cur.executemany(q, data["categories"])
        conn.commit()
    finally:
        cur.close()


def get_people_categories() -> list[str]:
    update_people_categories()
    conn = get_db()
    cur = conn.cursor()
    try:
        q = "SELECT name FROM peopleCategories"
        names = cur.execute(q).fetchall()
        return [n[0] for n in names]
    finally:
        cur.close()


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
    try:
        cur.execute("DELETE FROM products")
        products = [(p["name"], p["productCode"]) for p in data["data"]]
        q = """INSERT INTO products (name, id)
            VALUES (?, ?)"""
        cur.executemany(q, products)
        conn.commit()
    finally:
        cur.close()


def get_products() -> list[str]:
    update_products()
    conn = get_db()
    cur = conn.cursor()
    try:
        q = "SELECT name FROM products"
        names = cur.execute(q).fetchall()
        return [n[0] for n in names]
    finally:
        cur.close()


@BookeoUpdate
def get_rooms_booked(start: dt.date, end: dt.date, **options) -> int:
    conn = get_db()
    cur = conn.cursor()
    try:
        params = {"start": start, "end": end}
        q = """SELECT COUNT(DISTINCT creationTime)
            FROM bookings
            WHERE creationTime BETWEEN :start AND :end
            AND NOT canceled """
        if options["product"]:
            sq = (
                "SELECT id FROM products WHERE name IN (SELECT value FROM json_each(?))"
            )
            product_ids = cur.execute(sq, (json.dumps(options["product"]),)).fetchall()
            q += " AND productId IN (SELECT value FROM json_each(:product_ids)) "
            params["product_ids"] = json.dumps([p[0] for p in product_ids])
        count = cur.execute(q, params).fetchone()
        return count[0]
    finally:
        cur.close()


@BookeoUpdate
def get_slots_booked(start: dt.date, end: dt.date, **options) -> int:
    conn = get_db()
    cur = conn.cursor()
    try:
        params = {"start": start, "end": end}
        q = """SELECT COUNT(*)
            FROM participants p JOIN bookings b
            ON p.bookingId=b.id
            WHERE creationTime BETWEEN :start AND :end"""
        if options["product"]:
            sq = (
                "SELECT id FROM products WHERE name IN (SELECT value FROM json_each(?))"
            )
            product_ids = cur.execute(sq, (json.dumps(options["product"]),)).fetchall()
            q += " AND productId IN (SELECT value FROM json_each(:product_ids)) "
            params["product_ids"] = json.dumps([p[0] for p in product_ids])
        count = cur.execute(q, params).fetchone()
        return count[0]
    finally:
        cur.close()


@BookeoUpdate
def get_rooms_run(start: dt.date, end: dt.date, **options) -> int:
    conn = get_db()
    cur = conn.cursor()
    try:
        params = {"start": start, "end": end}
        q = """SELECT COUNT(DISTINCT startTime)
            FROM bookings
            WHERE startTime BETWEEN :start AND :end
            AND NOT canceled """
        if options["product"]:
            sq = (
                "SELECT id FROM products WHERE name IN (SELECT value FROM json_each(?))"
            )
            product_ids = cur.execute(sq, (json.dumps(options["product"]),)).fetchall()
            q += " AND productId IN (SELECT value FROM json_each(:product_ids)) "
            params["product_ids"] = json.dumps([p[0] for p in product_ids])
        count = cur.execute(q, params).fetchone()
        return count[0]
    finally:
        cur.close()


@BookeoUpdate
def get_slots_run(start: dt.date, end: dt.date, **options) -> int:
    conn = get_db()
    cur = conn.cursor()
    try:
        params = {"start": start, "end": end}
        q = """SELECT COUNT(*)
            FROM participants p JOIN bookings b
            ON p.bookingId=b.id
            WHERE startTime BETWEEN :start AND :end"""
        if options["product"]:
            sq = (
                "SELECT id FROM products WHERE name IN (SELECT value FROM json_each(?))"
            )
            product_ids = cur.execute(sq, (json.dumps(options["product"]),)).fetchall()
            q += " AND productId IN (SELECT value FROM json_each(:product_ids)) "
            params["product_ids"] = json.dumps([p[0] for p in product_ids])
        count = cur.execute(q, params).fetchone()
        return count[0]
    finally:
        cur.close()


def get_revenue(start: dt.date, end: dt.date, **options) -> int:
    return -1


def generate_report(start: dt.date, end: dt.date, **options):
    rooms_booked = get_rooms_booked(start, end, **options)
    slots_booked = get_slots_booked(start, end, **options)
    rooms_run = get_rooms_run(start, end, **options)
    slots_run = get_slots_run(start, end, **options)
    # revenue = get_revenue(start, end, **options)
    st.write(f"Rooms booked: {rooms_booked}")
    st.write(f"Slots booked: {slots_booked}")
    st.write(f"Rooms run: {rooms_run}")
    st.write(f"Slots run: {slots_run}")


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
    # force_cache_refresh = st.checkbox("Force cache refresh?")
    # if force_cache_refresh:

    #     st.cache_data.clear()
    update_roster()
    report_btn = st.button("Generate report")
    if report_btn:
        generate_report(start_date, end_date, **report_options)


if __name__ == "__main__":
    init_keys()
    init_db()
    main()
