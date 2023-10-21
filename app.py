import streamlit as st
import pandas as pd
import os
import datetime as dt
import pytz
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


def main():
    st.write("Hello, world!")
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


if __name__ == "__main__":
    init_keys()
    main()
