import streamlit as st
import re
import pandas as pd

# ------------------------------------------------------------------------
# REGEX PATTERNS FOCUSED ON TRANSACTION ID AND EVENT
# ------------------------------------------------------------------------
# Optional Timestamp pattern at the beginning of a line.
TIMESTAMP_PATTERN = re.compile(
    r"^(?P<timestamp>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z)?"
)

# Transaction ID pattern: look for "t=" followed by one or more digits.
TRANSACTION_PATTERN = re.compile(r"\bt=(?P<transaction_id>\d+)\b")

# Rendition ID pattern: look for "reid=" followed by one or more digits.
RENDITION_PATTERN = re.compile(r"\breid(?P<rendition_id>\d+)\b")

# Event marker can be either a cn= parameter or an "AdProgress" marker or a Duration[...] marker.
# (We use these to identify an event line.)
CN_PATTERN = re.compile(r"[?&]cn=(?P<cn>\w+)|\scn=(?P<cn2>\w+)")
ADPROGRESS_PATTERN = re.compile(r'"type":"(?P<type>AdProgress)"')
DURATION_PATTERN = re.compile(r"Duration\[(?P<duration>\d+)\]")

def parse_log_line(line: str) -> dict:
    """
    Parse a single line and return a dictionary with selected fields:
      - timestamp (if present)
      - transaction_id (required)
      - event_quartile (derived from cn=, "AdProgress" or Duration marker)
      
    Any line that does not contain a transaction ID is skipped.
    Lines where the event type is 'defaultClick' are ignored.
    """
    # 1) Get the optional timestamp if present.
    ts_match = TIMESTAMP_PATTERN.match(line)
    timestamp = ts_match.group("timestamp") if ts_match and ts_match.group("timestamp") else None

    # 2a) Look for the transaction ID.
    trans_match = TRANSACTION_PATTERN.search(line)
    if not trans_match:
        return {}  # Skip lines with no transaction id.
    transaction_id = trans_match.group("transaction_id")

    # 2b) Look for the rendition ID.
    rendition_match = RENDITION_PATTERN.search(line)
    
    rendition_id = ( 
        rendition_match.group("rendition_id")
        if renidition_match
        else None 
    )

    # 3) Identify the event. Check for a cn= marker, for "AdProgress", or for a Duration marker.
    cn_match = CN_PATTERN.search(line)
    adprogress_match = ADPROGRESS_PATTERN.search(line)
    duration_match = DURATION_PATTERN.search(line)

    # Accept the line if at least one condition is met.
    if not (cn_match or adprogress_match or duration_match):
        return {}

    # 4) Derive the event type.
    event_quartile = None
    if cn_match:
        event_quartile = cn_match.group("cn") or cn_match.group("cn2")
    elif adprogress_match:
        event_quartile = "AdProgress"
    elif duration_match:
        event_quartile = "DurationEvent"

    # Exclude events labeled as "defaultClick".
    if event_quartile and event_quartile.lower() == "defaultclick":
        return {}

    # 5) Return only the needed fields.
    return {
        "timestamp": timestamp,
        "transaction_id": transaction_id,
        "rendition_id": rendition_id
        "event": event_quartile,
    }

def parse_uploaded_logs(uploaded_files) -> pd.DataFrame:
    """
    Reads each uploaded file line-by-line, creates records from lines that have a transaction_id
    and an event, then returns a DataFrame with fields:
       timestamp, transaction_id, and event.
       
    Duplicate rows are dropped.
    """
    all_records = []
    for uploaded_file in uploaded_files:
        content = uploaded_file.read().decode("utf-8", errors="ignore")
        for line in content.splitlines():
            record = parse_log_line(line)
            if record and record.get("transaction_id") and record.get("event"):
                all_records.append(record)
    df = pd.DataFrame(all_records)
    if not df.empty:
        # Optionally sort by timestamp (lines with no timestamp will be sorted with None values).
        df.sort_values(by="timestamp", inplace=True, na_position="first")
        df.reset_index(drop=True, inplace=True)
        df.drop_duplicates(inplace=True)
    return df

def main():
    st.title("Log Parser - Transaction and Rendition ID Focus")
    st.write(
        "Upload log files. This app extracts only the timestamp, the transaction ID (from t=), the rendition ID (reid) "
        "and the event marker (excluding 'defaultClick' events)."
    )

    uploaded_files = st.file_uploader(
        "Choose log file(s)",
        accept_multiple_files=True,
        type=["txt", "log"]
    )

    if uploaded_files:
        df = parse_uploaded_logs(uploaded_files)
        if df.empty:
            st.warning("No relevant events were found in these logs!")
        else:
            st.success(f"Found {len(df)} event records.")
            st.dataframe(df)
            csv_data = df.to_csv(index=False)
            st.download_button(
                label="Download CSV",
                data=csv_data,
                file_name="parsed_events.csv",
                mime="text/csv"
            )

if __name__ == "__main__":
    main()
