import datetime
import string

import altair as alt
from altair.vegalite.v4.schema.channels import Color
import gspread
import pandas as pd
import streamlit as st

gc = gspread.service_account_from_dict(st.secrets["gcp_service_account"])
sh = gc.open_by_key("1bWv49xiZ4stjf8V6AnPWnDSyU9rbHe1R62Fw9eKyK98")
inventory_ws = sh.get_worksheet(0)
postpone_ws = sh.get_worksheet(1)

inventory_df = pd.DataFrame(inventory_ws.get_all_records())
inventory_df["expiration_date"] = pd.to_datetime(
    inventory_df["expiration_date"]
).dt.date
postpone_df = pd.DataFrame(postpone_ws.get_all_records())
postpone_df["expiration_date"] = pd.to_datetime(postpone_df["expiration_date"]).dt.date
postpone_df["postpone_until"] = pd.to_datetime(postpone_df["postpone_until"]).dt.date
postpone_df = postpone_df[postpone_df["postpone_until"] > datetime.date.today()]

df = inventory_df.merge(postpone_df, on=["expiration_date", "content"], how="left")

CL_MAP = dict(zip(df.columns, string.ascii_uppercase))
df["is_opened"] = df["is_opened"] == "TRUE"
df["priority"] = (df["expiration_date"] - datetime.date.today()).dt.days - df[
    "servings"
]
df = df.sort_values("priority")
df = df[~(df["postpone_until"] > datetime.date.today())]


def get_cell_name(entry, column):
    return f"{CL_MAP[column]}{entry.name+2}"


def render_item(col, entry, postpone_df):
    col.write(f"### {entry.content}")
    col.write(f"Expiring on: {entry.expiration_date}")
    col.write(f"{entry.servings} servings in the {entry.storage_location}")
    if col.button("I ate it", key=entry.name):
        cell_name = get_cell_name(entry, "servings")
        inventory_ws.update(cell_name, str(entry.servings - 1), raw=False)
        st.experimental_rerun()
    if col.button("Postpone", key=entry.name):
        postpone_df = postpone_df.append(
            {
                "expiration_date": entry.expiration_date,
                "content": entry.content,
                "postpone_until": datetime.date.today() + datetime.timedelta(days=21),
            },
            ignore_index=True,
        )
        postpone_ws.clear()
        postpone_ws.update(
            "A1:C",
            [postpone_df.columns.tolist()] + postpone_df.astype(str).values.tolist(),
            raw=False,
        )
        st.experimental_rerun()


meals_df = df[df.type == "Meal"]
snacks_df = df[df.type == "Snack"]
sweets_df = df[df.type == "Sweets"]

st.set_page_config(layout="wide")


f"""
# Niwako's food dashboard

## This week's meal suggestions
"""

cols = st.beta_columns(spec=3)
for i in range(len(cols)):
    render_item(cols[i], meals_df.iloc[i], postpone_df)

st.write("---")

f"""
## This week's snack suggestions
"""
cols = st.beta_columns(spec=3)
for i in range(len(cols)):
    render_item(cols[i], snacks_df.iloc[i], postpone_df)

st.write("---")

f"""
## This week's sweets suggestions
"""
cols = st.beta_columns(spec=3)
for i in range(len(cols)):
    render_item(cols[i], sweets_df.iloc[i], postpone_df)

# df
st.write("---")

f"""
## Servings expiring by month
"""

event_df = pd.DataFrame(
    {
        "date": [datetime.date.today()],
        "label": ["Today"],
    }
)
event_chart = (
    alt.Chart(event_df)
    .mark_rule(color="red")
    .encode(
        x=alt.X("date", type="temporal"),
        tooltip=[
            alt.Tooltip("label"),
        ],
    )
)
servings_expiring_by_month_chart = (
    alt.Chart(df)
    .mark_bar()
    .encode(
        x=alt.X("yearmonth(expiration_date)", type="temporal", title="Month"),
        y=alt.Y("sum(servings)", title="Servings"),
        color=alt.Color("type", title="Meal type"),
        tooltip=[
            alt.Tooltip("yearmonth(expiration_date)", title="Month"),
            alt.Tooltip("sum(servings)", title="Servings"),
            alt.Tooltip("type", title="Meal type"),
        ],
    )
)

st.altair_chart(
    (servings_expiring_by_month_chart + event_chart),
    use_container_width=True,
)
