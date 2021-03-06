from datetime import datetime
import pytz
import altair as alt
import humanize
import gspread
import pandas as pd
import streamlit as st
from oauth2client.service_account import ServiceAccountCredentials


@st.cache(ttl=60)
def brita_log():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_name("shad-jupyter.json", scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key("16F6zkf7qxjdWZxlj-T7I5jjD9GzE1kIMUprVMFfLPNI")
    records = sheet.get_worksheet(0).get_all_records()

    df = pd.DataFrame.from_dict(records)
    df = df.rename({"Timestamp": "timestamp", "Event Name": "event"}, axis=1)
    df["timestamp"] = pd.to_datetime(df["timestamp"], format=r"%d/%m/%Y %H:%M:%S")
    df["timestamp"] = df["timestamp"].dt.tz_localize("US/Pacific")
    df = df.set_index("timestamp").sort_index()

    df["refills"] = 1
    df["filter"] = (df["event"] == "Brita filter replaced").cumsum()
    df["total_refills"] = df.groupby("filter").cumcount()
    return df


now = datetime.now(tz=pytz.timezone("US/Pacific"))
df = brita_log()

refills_df = df[df.event == "Brita pitcher refilled"]
replacements_df = df[df.event == "Brita filter replaced"]

recent_refilled = max(refills_df.index)
recent_replaced = max(replacements_df.index)
mean_refills_per_filter = refills_df.groupby("filter")["refills"].sum()[:-1].mean()
mean_refills_per_day = refills_df.groupby(pd.Grouper(freq="D"))["refills"].sum().mean()
mean_days_per_filter = mean_refills_per_filter / mean_refills_per_day
refills_this_iteration = refills_df["total_refills"][-1]
estimated_days_remaining = (
    mean_refills_per_filter - refills_this_iteration
) / mean_refills_per_day

f"""
# Brita Water Log
- Brita pitcher last refilled **{humanize.naturaltime(recent_refilled, when=now)}** with an average of **{mean_refills_per_day:.1f}** refills per day
- **{len(replacements_df)}** total Brita filters used and was most recently replaced **{humanize.naturaltime(recent_replaced, when=now)}**
- **{refills_this_iteration}** / **{mean_refills_per_filter:.1f}** refills used on the current Brita filter
- **{estimated_days_remaining:.0f}** / **{mean_days_per_filter:.1f}** days remaining before needing to replace the filter
"""

base_refills = alt.Chart(refills_df.reset_index())

filter_selection = alt.selection_multi(fields=["filter"], bind="legend")

refills = (
    base_refills.properties(title="Total Refills")
    .mark_line()
    .encode(
        x=alt.X("yearmonthdate(timestamp)", type="temporal", title="Date"),
        y=alt.Y("max(total_refills)", type="quantitative", title="Refills"),
        color=alt.Color("filter", type="nominal", title="Filter"),
        opacity=alt.condition(filter_selection, alt.value(1), alt.value(0.2)),
    )
)

expected_refills = (
    alt.Chart(pd.DataFrame({"mean_refills_per_filter": [mean_refills_per_filter]}))
    .mark_rule()
    .encode(y="mean_refills_per_filter")
)

replacements = (
    alt.Chart(replacements_df.reset_index())
    .mark_rule()
    .encode(
        x=alt.X("yearmonthdate(timestamp)", type="temporal"),
        color=alt.Color("filter", type="nominal"),
        opacity=alt.condition(filter_selection, alt.value(1), alt.value(0.2)),
    )
)

st.altair_chart(
    (refills + replacements + expected_refills).add_selection(filter_selection),
    use_container_width=True,
)


st.altair_chart(
    base_refills.properties(title="Refills by Hour of the Day")
    .mark_bar()
    .encode(
        x=alt.X("hours(timestamp)", type="temporal", title="Hour"),
        y=alt.Y("sum(refills)", title="Refills"),
        color=alt.Color("day(timestamp)", type="nominal", title="Day"),
        tooltip=[
            alt.Tooltip("hours(timestamp)", title="Hour of the Day"),
            alt.Tooltip("day(timestamp)", title="Day of the Week"),
            alt.Tooltip("sum(refills)", title="Refills"),
        ],
    ),
    use_container_width=True,
)


st.altair_chart(
    base_refills.properties(title="Refills by Month of the Year")
    .mark_bar()
    .encode(
        x=alt.X("yearmonth(timestamp)", type="temporal", title="Month"),
        y=alt.Y("sum(refills)", title="Refills"),
        color=alt.Color("hours(timestamp)", type="temporal", title="Hour"),
        tooltip=[
            alt.Tooltip("yearmonth(timestamp)", title="Month"),
            alt.Tooltip("hours(timestamp)", title="Hour of the Day"),
            alt.Tooltip("sum(refills)", title="Refills"),
        ],
    ),
    use_container_width=True,
)


st.altair_chart(
    base_refills.properties(title="Refills by Day of the Week")
    .mark_bar()
    .encode(
        x=alt.X("day(timestamp)", type="ordinal", title="Day"),
        y=alt.Y("sum(refills)", title="Refills"),
        color=alt.Color("filter", type="nominal", title="Filter"),
        tooltip=[
            alt.Tooltip("day(timestamp)", title="Day of the Week"),
            alt.Tooltip("filter", title="Filter"),
            alt.Tooltip("sum(refills)", title="Refills"),
        ],
    ),
    use_container_width=True,
)
