import streamlit as st
import pandas as pd
import os
import datetime
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


def main():
    st.write("Hello, world!")


@st.cache_data
def fetch_square_data(start_dt, end_dt) -> dict:
    pass


@st.cache_data
def fetch_bookeo_data(start_dt, end_dt) -> dict:
    pass


if __name__ == "__main__":
    init_keys()
    main()
