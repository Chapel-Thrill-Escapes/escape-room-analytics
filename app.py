import streamlit as st
import pandas as pd
import os
import datetime as dt
import pytz
import csv
import requests

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

ZULU_FORMAT = "%Y-%m-%dT%H:%M:00Z"

people_categories = {}


def init_keys():
    os.environ["USER_AGENT"] = "CTE Sales Report Engine v0.1"
    os.environ["SQUARE_API_KEY"] = st.secrets["SQUARE_API_KEY"]
    os.environ["BOOKEO_API_KEY"] = st.secrets["BOOKEO_API_KEY"]
    os.environ["BOOKEO_SECRET_KEY"] = st.secrets["BOOKEO_SECRET_KEY"]


@st.cache_data
def fetch_square_data(start: dt.date, end: dt.date) -> dict:
    pass


@st.cache_data
def fetch_bookeo_data(start: dt.date, end: dt.date) -> list[dict]:
    # https://www.bookeo.com/apiref/#tag/Bookings/paths/~1bookings/get
    start = dt.datetime.combine(start, dt.time(0, 0))
    end = dt.datetime.combine(end, dt.time(11, 59))

    if (end - start).days >= 31:
        date_overflow = True

    res = requests.get(
        "https://api.bookeo.com/v2/bookings",
        params={
            "startTime": start.strftime(ZULU_FORMAT),
            "endTime": end.strftime(ZULU_FORMAT),
            "secretKey": os.environ["BOOKEO_SECRET_KEY"],
            "apiKey": os.environ["BOOKEO_API_KEY"],
            "expandParticipants": False,
            "itemsPerPage": 100,
        },
        headers={"User-Agent": os.environ["USER_AGENT"]},
    )
    print(res.json())


@st.cache_data
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
        return None
    return {c["id"]: c["name"] for c in data["categories"]}


def generate_display_report(start: dt.date, end: dt.date, **kwargs):
    square_data = fetch_square_data(start, end)
    bookeo_data = fetch_bookeo_data(start, end)
    for arg in kwargs:
        if kwargs[arg]:
            print(arg)


def main():
    people_categories = fetch_people_categories()
    st.write("# Escape Room Analytics")
    # https://docs.streamlit.io/library/api-reference/widgets/st.date_input
    today = dt.datetime.now(pytz.timezone("US/Eastern"))
    start_date = st.date_input(
        "Start date",
        value=None,
        max_value=today,
        key="start_date",
        format="MM/DD/YYYY",
    )
    end_date = st.date_input(
        "End date",
        value=None,
        max_value=today,
        key="end_date",
        format="MM/DD/YYYY",
    )
    st.write("## Parameters")
    # https://docs.streamlit.io/library/api-reference/widgets/st.checkbox
    report_options = {
        "revenue": st.checkbox("Total revenue", value=False, key="revenue"),
        "booking_revenue": st.checkbox("Booking revenue", value=False, key="b_revenue"),
        "invoice_revenue": st.checkbox("Invoice revenue", value=False, key="i_revenue"),
        "rooms_booked": st.checkbox("Rooms booked", value=False, key="rooms_booked"),
        "slots_booked": st.checkbox("Slots booked", value=False, key="slots_booked"),
        "rooms_run": st.checkbox("Rooms run", value=False, key="rooms_run"),
        "slots_run": st.checkbox("Slots run", value=False, key="slots_run"),
        "cost_of_labor": st.checkbox("Cost of labor", value=False, key="cost_of_labor"),
        "wages": st.checkbox("Wages", value=False, key="wages"),
        "bonuses": st.checkbox("Bonuses", value=False, key="bonuses"),
        "pricing_category": st.checkbox(
            "Pricing category", value=False, key="cat_price"
        ),
        "group_category": st.checkbox("Group category", value=False, key="cat_group"),
        "contact_method": st.checkbox(
            "Contact method", value=False, key="contact_method"
        ),
    }

    st.button(
        "Generate report",
        on_click=generate_display_report,
        args=(start_date, end_date),
        kwargs=report_options,
    )


if __name__ == "__main__":
    init_keys()
    main()
