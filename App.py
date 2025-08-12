import streamlit as st
from datetime import datetime
import csv
from io import StringIO

# ---------------------
# App Config
# ---------------------
st.set_page_config(page_title="Elder Ministry Priority Allocation", layout="wide")

st.title("Elder Ministry Priority Allocation Survey")
st.write(
    """
You have a fictional **100** to allocate among our church’s ministries. 
Assign dollar amounts to any items under **any** of the five ministry priorities.
Your total across **all** priorities must equal **exactly 100**.

This survey is **anonymous**.
    """
)

# ---------------------
# Data
# ---------------------
ALL_ITEMS = [
    "Building Maintenance",
    "Building Upgrades",
    "Children's Ministry",
    "Children's Plays",
    "Choir",
    "Congregational Care (deacons, pastoral care, etc.)",
    "Garden",
    "Handbell Choir",
    "Men's Ministry",
    "Missions",
    "Office Expenses",
    "Office Staff",
    "Outreach events - Harvest Party, etc.",
    "Praise Band",
    "Preaching/Worship Leadership",
    "Small Groups",
    "Sound System",
    "Tech - Audio/Visual (sound system, streaming, etc.)",
    "Tech - Office/Building",
    "Women's Ministry",
    "Youth Ministry",
]

PRIORITIES = [
    "Worship-centered",
    "Ministry/Spiritual Formation-centered",
    "Missions-Centered",
    "Community-Centered",
    "Support-Centered",
]

PRIORITY_ITEMS = {p: ALL_ITEMS for p in PRIORITIES}  # same items in each category

# ---------------------
# Helpers
# ---------------------

def init_state():
    if "allocations" not in st.session_state:
        st.session_state.allocations = {
            p: {item: 0 for item in PRIORITY_ITEMS[p]} for p in PRIORITIES
        }
    if "submitted" not in st.session_state:
        st.session_state.submitted = False


def get_subtotals_and_total():
    subtotals = {}
    for p in PRIORITIES:
        subtotals[p] = sum(st.session_state.allocations[p].values())
    total = sum(subtotals.values())
    return subtotals, total


def clear_all():
    for p in PRIORITIES:
        for item in PRIORITY_ITEMS[p]:
            st.session_state.allocations[p][item] = 0
    st.session_state.submitted = False


def allocations_rows(timestamp_iso: str):
    """Flatten allocations into CSV-ready rows."""
    rows = []
    for p in PRIORITIES:
        for item, amt in st.session_state.allocations[p].items():
            if amt and amt > 0:
                rows.append([
                    timestamp_iso,
                    p,
                    item,
                    int(amt),
                ])
    return rows


def write_csv(rows):
    """Append to a local CSV file (persists for the app instance) and also
    save a per-response CSV under ./submissions/ for owner download.
    """
    import os
    os.makedirs("submissions", exist_ok=True)

    header = ["timestamp", "priority", "item", "amount"]
    try:
        # Create master CSV if missing
        try:
            with open("responses.csv", "x", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(header)
        except FileExistsError:
            pass

        # Append to master
        with open("responses.csv", "a", newline="") as f:
            writer = csv.writer(f)
            for r in rows:
                writer.writerow(r)

        # Also write a per-response CSV
        ts_safe = rows[0][0].replace(":", "-")
        per_path = os.path.join("submissions", f"submission_{ts_safe}.csv")
        with open(per_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(header)
            writer.writerows(rows)

        return True, None
    except Exception as e:
        return False, str(e)


def make_personal_copy_csv():
    """Allow the current respondent to download their own allocations as a CSV."""
    header = ["priority", "item", "amount"]
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(header)
    for p in PRIORITIES:
        for item, amt in st.session_state.allocations[p].items():
            if amt and amt > 0:
                writer.writerow([p, item, int(amt)])
    output.seek(0)
    return output.getvalue()


# ---------------------
# Admin / Owner tools (set an optional admin key in secrets to reveal controls)
# ---------------------
admin_key_secret = None
try:
    from streamlit.runtime.secrets import secrets
    admin_key_secret = secrets.get("ADMIN_KEY", None)
except Exception:
    admin_key_secret = None

with st.sidebar:
    st.subheader("Owner tools")
    entered_key = st.text_input("Enter admin key to unlock", type="password")
    owner_mode = bool(admin_key_secret) and entered_key == admin_key_secret
    if not admin_key_secret:
        st.caption("Tip: add ADMIN_KEY to Streamlit secrets to enable admin tools.")

# ---------------------
# Main UI
# ---------------------
init_state()

st.markdown("---")

# Draw inputs in two columns per priority for readability
for p in PRIORITIES:
    with st.expander(f"{p}", expanded=False):
        cols = st.columns(2)
        items = PRIORITY_ITEMS[p]
        half = (len(items) + 1) // 2
        left_items = items[:half]
        right_items = items[half:]

        with cols[0]:
            for item in left_items:
                key = f"{p}:{item}"
                st.session_state.allocations[p][item] = st.number_input(
                    f"{item}",
                    min_value=0,
                    max_value=100,
                    step=1,
                    value=int(st.session_state.allocations[p][item]),
                    key=key,
                )
        with cols[1]:
            for item in right_items:
                key = f"{p}:{item}"
                st.session_state.allocations[p][item] = st.number_input(
                    f"{item}",
                    min_value=0,
                    max_value=100,
                    step=1,
                    value=int(st.session_state.allocations[p][item]),
                    key=key,
                )

# Totals and validation
subtotals, total = get_subtotals_and_total()

st.markdown("---")

# Summary row
sum_cols = st.columns(len(PRIORITIES) + 1)
for idx, p in enumerate(PRIORITIES):
    sum_cols[idx].metric(label=f"{p} subtotal", value=f"${subtotals[p]}")

sum_cols[-1].metric(label="Total allocated", value=f"${total}")

st.progress(min(total, 100) / 100)

# Guidance
if total > 100:
    st.error(f"Total exceeds $100 by ${total - 100}. Please reallocate.")
elif total < 100:
    st.warning(f"Total is less than $100 by ${100 - total}. Keep allocating to reach $100.")
else:
    st.success("Perfect — total is exactly $100. You can submit now.")

left, mid, right = st.columns([1,1,2])

with left:
    if st.button("Clear all"):
        clear_all()
        st.rerun()

with mid:
    submitted = st.button("Submit allocations", type="primary", disabled=(total != 100))

if submitted and total == 100:
    timestamp = datetime.utcnow().isoformat()
    rows = allocations_rows(timestamp)
    if not rows:
        st.error("No allocations entered. Please allocate funds before submitting.")
    else:
        ok, err = write_csv(rows)
        if ok:
            st.session_state.submitted = True
            st.success("Thank you! Your anonymous response has been recorded.")

            # Offer a personal copy
            csv_data = make_personal_copy_csv()
            st.download_button(
                "Download your allocation as CSV",
                data=csv_data,
                file_name="my_ministry_allocation.csv",
                mime="text/csv",
            )
            clear_all()
        else:
            st.error(f"There was an error saving your response: {err}")

# ---------------------
# Optional: Google Sheets integration (uncomment to use)
# ---------------------
# To use Google Sheets instead of a local CSV, add a service account JSON to Streamlit Secrets
# and use gspread to append rows. Example setup:
#
# 1) In Streamlit, add secrets:
#    [gcp_service_account]
#    type = "service_account"
#    project_id = "..."
#    private_key_id = "..."
#    private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
#    client_email = "...@...iam.gserviceaccount.com"
#    client_id = "..."
#    auth_uri = "https://accounts.google.com/o/oauth2/auth"
#    token_uri = "https://oauth2.googleapis.com/token"
#    auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
#    client_x509_cert_url = "..."
#    spreadsheet_name = "Elder Ministry Responses"
#
# 2) Then replace write_csv with something like this:
#
# import gspread
# from oauth2client.service_account import ServiceAccountCredentials
#
# def write_gsheet(rows):
#     try:
#         import json
#         from streamlit.runtime.secrets import secrets
#         sa = dict(secrets["gcp_service_account"])  # service account dict
#         scope = [
#             "https://spreadsheets.google.com/feeds",
#             "https://www.googleapis.com/auth/drive",
#         ]
#         creds = ServiceAccountCredentials.from_json_keyfile_dict(sa, scope)
#         gc = gspread.authorize(creds)
#         sh = gc.open(secrets["gcp_service_account"]["spreadsheet_name"])  # by name
#         ws = sh.sheet1
#         for r in rows:
#             ws.append_row(r)  # [timestamp, priority, item, amount]
#         return True, None
#     except Exception as e:
#         return False, str(e)
#
# ...and call write_gsheet(rows) instead of write_csv(rows).

# ---------------------
# Owner / Admin Panel (visible with correct key)
# ---------------------
if 'owner_mode' in globals() and owner_mode:
    st.markdown("---")
    st.subheader("Admin: All Submissions")

    import os, zipfile
    from pathlib import Path

    # Preview master CSV
    if Path("responses.csv").exists():
        try:
            import pandas as pd
            df = pd.read_csv("responses.csv")
            st.caption(f"Total rows: {len(df)} (each row = one line item)")
            st.dataframe(df, use_container_width=True, hide_index=True)

            # Download master CSV
            with open("responses.csv", "rb") as f:
                st.download_button(
                    "Download ALL responses (master CSV)",
                    data=f.read(),
                    file_name="all_responses.csv",
                    mime="text/csv",
                )
        except Exception as e:
            st.warning(f"Couldn't preview master CSV: {e}")
    else:
        st.info("No responses saved yet.")

    # Zip up per-response CSVs for download
    subs_dir = Path("submissions")
    if subs_dir.exists():
        files = list(subs_dir.glob("submission_*.csv"))
        st.caption(f"Individual submission files: {len(files)}")
        if files:
            import io
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                for fp in files:
                    zf.write(fp, arcname=fp.name)
            zip_buffer.seek(0)
            st.download_button(
                "Download ZIP of all individual submissions",
                data=zip_buffer,
                file_name="all_submissions.zip",
                mime="application/zip",
            )
    st.success("Owner tools unlocked.")

