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
    df["timestamp"] = pd.to_datetime(df["timestamp"], format="%d/%m/%Y %H:%M:%S")
    df = df.set_index("timestamp").sort_index()

    df["refills"] = 1
    df["filter"] = (df["event"] == "Brita filter replaced").cumsum()
    df["total_refills"] = df.groupby("filter").cumcount()
    return df


df = brita_log()

refills_df = df[df.event == "Brita pitcher refilled"]
replacements_df = df[df.event == "Brita filter replaced"]

recent_refilled = max(refills_df.index)
recent_replaced = max(replacements_df.index)
mean_refills_per_filter = refills_df.groupby("filter")["refills"].sum()[:-1].mean()
mean_refills_per_day = refills_df.groupby(pd.Grouper(freq="D"))["refills"].sum().mean()
refills_this_iteration = refills_df["total_refills"][-1]
estimated_days_remaining = (
    mean_refills_per_filter - refills_this_iteration
) / mean_refills_per_day

f"""
# Brita Water Log
- Brita pitcher last refilled **{humanize.naturaltime(recent_refilled)}**
- Brita filter last replaced **{humanize.naturaltime(recent_replaced)}**
- **{len(replacements_df)}** total Brita filters used
- Average of **{mean_refills_per_filter:.1f}** refills per Brita filter
- Average of **{mean_refills_per_day:.1f}** refills per day
- **{refills_this_iteration}** refills used on the current Brita filter
- **{estimated_days_remaining:.0f}** days remaining before needing to replace the filter
"""

refills = (
    alt.Chart(refills_df.reset_index(), title="Total Refills")
    .mark_line()
    .encode(
        x=alt.X("yearmonthdate(timestamp)", type="temporal", title="Date"),
        y=alt.Y("max(total_refills)", type="quantitative", title="Refills"),
        color=alt.Color("filter", type="nominal"),
    )
)

replacements = (
    alt.Chart(replacements_df.reset_index())
    .mark_rule(color="red")
    .encode(
        x=alt.X("yearmonthdate(timestamp)", type="temporal"),
        color=alt.Color("filter", type="nominal"),
    )
)

st.altair_chart(
    (refills + replacements),
    use_container_width=True,
)

st.altair_chart(
    alt.Chart(refills_df.reset_index(), title="Refills by Hour of the Day")
    .mark_bar()
    .encode(
        x=alt.X("hours(timestamp)", type="temporal", title="Hour"),
        y=alt.Y("sum(refills)", title="Refills"),
        color=alt.Color("day(timestamp)", type="temporal", title="Day"),
        tooltip=[
            alt.Tooltip("hours(timestamp)", title="Hour of the Day"),
            alt.Tooltip("day(timestamp)", title="Day of the Week"),
            alt.Tooltip("sum(refills)", title="Refills"),
        ],
    ),
    use_container_width=True,
)

st.altair_chart(
    alt.Chart(refills_df.reset_index(), title="Refills by Month of the Year")
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
