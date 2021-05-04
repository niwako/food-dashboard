import datetime
import string

import gspread
import pandas as pd
import streamlit as st

gc = gspread.service_account_from_dict(st.secrets["gcp_service_account"])
sh = gc.open_by_key("1bWv49xiZ4stjf8V6AnPWnDSyU9rbHe1R62Fw9eKyK98")
ws = sh.sheet1

df = pd.DataFrame(ws.get_all_records())
CL_MAP = dict(zip(df.columns, string.ascii_uppercase))
df["expiration_date"] = pd.to_datetime(df["expiration_date"])
df["is_opened"] = df["is_opened"] == "TRUE"
df["priority"] = (df["expiration_date"] - datetime.datetime.now()).dt.days - df[
    "servings"
]
df = df.sort_values("priority")


def get_cell_name(entry, column):
    return f"{CL_MAP[column]}{entry.name+2}"


def render_item(entry):
    st.write("---")
    st.write(f'### {entry["content"]} from {entry["storage_location"]}')
    st.write(f"({entry.servings} servings)")
    if st.button("I ate it", key=entry.name):
        cell_name = get_cell_name(entry, "servings")
        ws.update(cell_name, str(entry.servings - 1), raw=False)
        st.experimental_rerun()


meals_df = df[df.type == "Meal"]

f"""
# Niwako's food dashboard

## This week's meal suggestions
"""
render_item(meals_df.iloc[0])
render_item(meals_df.iloc[1])
render_item(meals_df.iloc[2])
