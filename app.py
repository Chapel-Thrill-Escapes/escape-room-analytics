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
# Number of reviews
# Reviews by quality


def init_keys():
    os.environ["SQUARE_API_KEY"] = st.secrets["SQUARE_API_KEY"]
    os.environ["BOOKEO_API_KEY"] = st.secrets["BOOKEO_API_KEY"]
    os.environ["BOOKEO_SECRET_KEY"] = st.secrets["BOOKEO_SECRET_KEY"]


@st.cache_data
def fetch_square_data(start_dt, end_dt) -> dict:
    pass


@st.cache_data
def fetch_bookeo_data(start_dt, end_dt) -> dict:
    pass


def generate_display_report(start_dt, end_dt, **kwargs):
    square_data = fetch_square_data(start_dt, end_dt)
    bookeo_data = fetch_bookeo_data(start_dt, end_dt)


def main():
    st.write("# Escape Room Analytics")
    # https://docs.streamlit.io/library/api-reference/widgets/st.date_input
    today = dt.datetime.now(pytz.timezone("US/Eastern"))
    start_date = st.date_input(
        "Start date",
        value=today.replace(day=1),
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
    st.write("## Parameters")
    revenue = st.checkbox("Total revenue", value=False, key="revenue")
    booking_revenue = st.checkbox("Booking revenue", value=False, key="b_revenue")
    invoice_revenue = st.checkbox("Invoice revenue", value=False, key="i_revenue")
    rooms_booked = st.checkbox("Rooms booked", value=False, key="rooms_booked")
    slots_booked = st.checkbox("Slots booked", value=False, key="slots_booked")
    rooms_run = st.checkbox("Rooms run", value=False, key="rooms_run")
    slots_run = st.checkbox("Slots run", value=False, key="slots_run")
    cost_of_labor = st.checkbox("Cost of labor", value=False, key="cost_of_labor")
    wages = st.checkbox("Wages", value=False, key="wages")
    bonuses = st.checkbox("Bonuses", value=False, key="bonuses")
    pricing_category = st.checkbox("Pricing category", value=False, key="cat_price")
    group_category = st.checkbox("Group category", value=False, key="cat_group")
    contact_method = st.checkbox("Contact method", value=False, key="contact_method")
    kwargs = {"test": st.checkbox("This is a test!")}

    st.button(
        "Generate report",
        on_click=generate_display_report,
        args=(start_date, end_date),
        kwargs=kwargs,
    )


if __name__ == "__main__":
    init_keys()
    main()
