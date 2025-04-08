import streamlit as st
import re
import pandas as pd

# --- REGEX PATTERNS ---
TIMESTAMP_PATTERN = re.compile(
    r"^(?P<timestamp>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z)"
)
ADID_PATTERN = re.compile(r"adid=(?P<adid>\d+)")
CRID_PATTERN = re.compile(r"crid=(?P<crid>\d+)")
CN_PATTERN = re.compile(r"[?&]cn=(?P<cn>\w+)|\scn=(?P<cn2>\w+)")
ADPROGRESS_PATTERN = re.compile(r'"type":"(?P<type>AdProgress)"')

RESERVATION_PATTERN = re.compile(r"reservationId=(?P<res>\d+)")
SPOTID_PATTERN = re.compile(r"spotid=(?P<spot>[\w\d]+,\d+)")
SEGMENTATION_EVENT_PATTERN = re.compile(r"segmentation_event_id=(?P<segid>\d+)")

def parse_log_line(line: str) -> dict:
    """
    Parse a single line of the log and return a dict with relevant info.
    Returns an empty dict if not relevant.
    """
    ts_match = TIMESTAMP_PATTERN.search(line)
    if not ts_match:
        return {}

    timestamp = ts_match.group("timestamp")
    adid_match = ADID_PATTERN.search(line)
    crid_match = CRID_PATTERN.search(line)
    cn_match = CN_PATTERN.search(line)
    adprogress_match = ADPROGRESS_PATTERN.search(line)
    reservation_match = RESERVATION_PATTERN.search(line)
    spotid_match = SPOTID_PATTERN.search(line)
    segid_match = SEGMENTATION_EVENT_PATTERN.search(line)

    # If there's no 'cn=' nor "AdProgress", skip
    if not cn_match and not adprogress_match:
        return {}

    quartile = None
    if cn_match:
        quartile = cn_match.group("cn") or cn_match.group("cn2")
    if adprogress_match and not quartile:
        quartile = "AdProgress"

    return {
        "timestamp": timestamp,
        "event_quartile": quartile,
        "ad_id": adid_match.group("adid") if adid_match else None,
        "creative_id": crid_match.group("crid") if crid_match else None,
        "reservation_id": reservation_match.group("res") if reservation_match else None,
        "spot_id": spotid_match.group("spot") if spotid_match else None,
        "segmentation_event_id": segid_match.group("segid") if segid_match else None,
    }

def parse_uploaded_logs(uploaded_files) -> pd.DataFrame:
    all_records = []
    for uploaded_file in uploaded_files:
        content = uploaded_file.read().decode("utf-8", errors="ignore")
        for line in content.splitlines():
            record = parse_log_line(line)
            if record and record.get("event_quartile"):
                all_records.append(record)
    df = pd.DataFrame(all_records)
    if not df.empty:
        df.sort_values(by="timestamp", inplace=True)
        df.reset_index(drop=True, inplace=True)
    return df

def main():
    st.title("ITV Log Parser")
    st.write("Upload one or more log files to parse ad events (quartile, AdProgress, etc.).")

    uploaded_files = st.file_uploader(
        "Choose log file(s)",
        accept_multiple_files=True,
        type=["txt","log"]
    )

    if uploaded_files:
        df = parse_uploaded_logs(uploaded_files)
        if df.empty:
            st.warning("No ad events found in these logs!")
        else:
            st.success(f"Found {len(df)} events.")
            st.dataframe(df)
            # Provide CSV download
            csv_data = df.to_csv(index=False)
            st.download_button(
                label="Download CSV",
                data=csv_data,
                file_name="parsed_ad_events.csv",
                mime="text/csv"
            )

if __name__ == "__main__":
    main()
