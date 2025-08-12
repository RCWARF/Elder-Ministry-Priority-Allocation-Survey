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
You have a fictional $100 to allocate among our church’s ministries. 
Assign dollar amounts to any items under any of the five ministry priorities.
Your total across all priorities must equal exactly $100.

This survey is anonymous.
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
    """Append to a local CSV file (persists for the app instance)."""
    header = ["timestamp", "priority", "item", "amount"]
    try:
        # If file doesn't exist, write header first
        try:
            with open("responses.csv", "x", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(header)
        except FileExistsError:
            pass

        with open("responses.csv", "a", newline="") as f:
            writer = csv.writer(f)
            for r in rows:
                writer.writerow(r)
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
