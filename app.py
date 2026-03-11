import streamlit as st
import pandas as pd

st.set_page_config(page_title="Job Runtime Analyzer", layout="wide")

st.title("⚙️ Job Runtime Metrics Analyzer")

uploaded_file = st.file_uploader(
    "Upload CSV or Excel File",
    type=["csv", "xlsx"]
)

# --------------------------------------------------
# Runtime formatter
# --------------------------------------------------

def format_runtime(ms):

    ms = int(ms)

    hours = ms // (1000 * 60 * 60)
    ms = ms % (1000 * 60 * 60)

    minutes = ms // (1000 * 60)
    ms = ms % (1000 * 60)

    seconds = ms // 1000
    milliseconds = ms % 1000

    return f"{hours}h {minutes}m {seconds}s {milliseconds}ms"


# --------------------------------------------------
# SAFE runtime parser
# --------------------------------------------------

def parse_runtime(value):

    try:

        if pd.isna(value):
            return 0

        value = str(value).strip()

        parts = value.split(":")

        if len(parts) == 4:

            h = int(parts[0])
            m = int(parts[1])
            s = int(parts[2])
            ms = int(parts[3])

        elif len(parts) == 3:

            h = int(parts[0])
            m = int(parts[1])
            s = int(parts[2])
            ms = 0

        else:
            return 0

        return (((h * 60 + m) * 60) + s) * 1000 + ms

    except:
        return 0


# --------------------------------------------------
# Process file
# --------------------------------------------------

if uploaded_file:

    if uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    df.columns = df.columns.str.strip()

    total_rows = len(df)

    st.write(f"Total rows in file: {total_rows}")

    # ----------------------------------------------
    # Clean columns
    # ----------------------------------------------

    df["isSystemJob"] = df["isSystemJob"].astype(str).str.strip().str.upper()
    df["triggerType"] = df["triggerType"].astype(str).str.strip().str.lower()

    df["tenant"] = df["tenant"].astype(str).str.strip()

    if "jobId" in df.columns:
        df["jobId"] = df["jobId"].astype(str).str.strip()

    if "jobName" in df.columns:
        df["jobName"] = df["jobName"].astype(str).str.strip()

    # ----------------------------------------------
    # Detect runtime column
    # ----------------------------------------------

    time_column = None

    for col in ["timetaken_dbformat", "timeTaken_dbFormat"]:
        if col in df.columns:
            time_column = col
            break

    if time_column is None:

        for col in ["timetaken_uiformat", "timeTaken_uiFormat"]:
            if col in df.columns:
                time_column = col
                break

    if time_column is None:
        st.error("No runtime column found")
        st.stop()

    st.success(f"Using runtime column: {time_column}")

    # ----------------------------------------------
    # Convert runtime
    # ----------------------------------------------

    df["runtime_ms"] = df[time_column].apply(parse_runtime)

    st.write(f"Rows used for calculation: {len(df)}")

    # ------------------------------------------------
    # GLOBAL SYSTEM TABLE
    # ------------------------------------------------

    system_true = df.loc[df["isSystemJob"] == "TRUE", "runtime_ms"].sum()
    system_false = df.loc[df["isSystemJob"] == "FALSE", "runtime_ms"].sum()

    system_table = pd.DataFrame({

        "System Jobs": [format_runtime(system_true)],
        "User defined jobs": [format_runtime(system_false)],
        "Total": [format_runtime(system_true + system_false)]
    })

    st.subheader("Total run time of system and user defined jobs")
    st.dataframe(system_table, use_container_width=True)

    # ------------------------------------------------
    # GLOBAL TRIGGER TABLE
    # ------------------------------------------------

    scheduled = df.loc[df["triggerType"] == "scheduled", "runtime_ms"].sum()
    adhoc = df.loc[df["triggerType"] == "ad-hoc", "runtime_ms"].sum()

    trigger_table = pd.DataFrame({

        "Ad-hoc Jobs": [format_runtime(adhoc)],
        "Scheduled Jobs": [format_runtime(scheduled)],
        "Total": [format_runtime(adhoc + scheduled)]
    })

    st.subheader("Total run time of ad-hoc and scheduled jobs")
    st.dataframe(trigger_table, use_container_width=True)

    # ------------------------------------------------
    # TENANT SYSTEM METRICS
    # ------------------------------------------------

    tenant_system = []

    for tenant, group in df.groupby("tenant"):

        sys_true = group.loc[group["isSystemJob"] == "TRUE", "runtime_ms"].sum()
        sys_false = group.loc[group["isSystemJob"] == "FALSE", "runtime_ms"].sum()

        total = sys_true + sys_false

        tenant_system.append({

            "Tenant": tenant,
            "Total Executions": len(group),

            "System Jobs": format_runtime(sys_true),
            "User Defined Jobs": format_runtime(sys_false),
            "Total Run Time": format_runtime(total),
            "Total_ms": total
        })

    tenant_system_df = pd.DataFrame(tenant_system)

    tenant_system_df = tenant_system_df.sort_values(
        by="Total_ms",
        ascending=False
    ).drop(columns=["Total_ms"])

    st.subheader("Tenant Wise System & User Defined Job Run Time Metrics :")
    st.dataframe(tenant_system_df,use_container_width=True)

    # ------------------------------------------------
    # Tenant Wise Trigger Type Run Time Metrics
    # ------------------------------------------------

    tenant_trigger = []

    for tenant, group in df.groupby("tenant"):

        sch = group.loc[group["triggerType"] == "scheduled", "runtime_ms"].sum()
        adh = group.loc[group["triggerType"] == "ad-hoc", "runtime_ms"].sum()

        total = sch + adh

        tenant_trigger.append({

            "Tenant": tenant,
            "Total Executions": len(group),

            "Scheduled Jobs": format_runtime(sch),
            "Ad-hoc Jobs": format_runtime(adh),
            "Total Run Time": format_runtime(total),
            "Total_ms": total
        })

    tenant_trigger_df = pd.DataFrame(tenant_trigger)

    tenant_trigger_df = tenant_trigger_df.sort_values(
        by="Total_ms",
        ascending=False
    ).drop(columns=["Total_ms"])

    st.subheader("Tenant Wise Trigger Type Run Time Metrics :")
    st.dataframe(tenant_trigger_df, use_container_width=True)

    # ------------------------------------------------
    # Job Wise Run Time Metrics
    # ------------------------------------------------

    job_df_filtered = df[df["isSystemJob"] == "FALSE"]

    job_metrics = []

    for (tenant, job), group in job_df_filtered.groupby(["tenant", "jobId"]):

        job_name = group["jobName"].iloc[0] if "jobName" in group.columns else "N/A"

        sch = group.loc[group["triggerType"] == "scheduled", "runtime_ms"].sum()
        adh = group.loc[group["triggerType"] == "ad-hoc", "runtime_ms"].sum()

        total = sch + adh

        job_metrics.append({

            "Tenant": tenant,
            "Job Id": job,
            "Job Name": job_name,
            "Total Executions": len(group),

            "Ad-hoc": format_runtime(adh),
            "Scheduled": format_runtime(sch),
            "Total Run Time": format_runtime(total),
            "Total_ms": total
        })

    job_df = pd.DataFrame(job_metrics)

    job_df = job_df.sort_values(
        by="Total_ms",
        ascending=False
    ).drop(columns=["Total_ms"])

    st.subheader("Job Wise Run Time Metrics :")
    st.dataframe(job_df, use_container_width=True)

    # ------------------------------------------------
# DOWNLOAD ALL TABLES AS EXCEL
# ------------------------------------------------

import io

def convert_to_excel():

    output = io.BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:

        system_table.to_excel(
            writer,
            sheet_name="Global_System_Jobs",
            index=False
        )

        trigger_table.to_excel(
            writer,
            sheet_name="Global_Trigger_Jobs",
            index=False
        )

        tenant_system_df.to_excel(
            writer,
            sheet_name="Tenant_System_Metrics",
            index=False
        )

        tenant_trigger_df.to_excel(
            writer,
            sheet_name="Tenant_Trigger_Metrics",
            index=False
        )

        job_df.to_excel(
            writer,
            sheet_name="Job_Wise_Metrics",
            index=False
        )

    output.seek(0)

    return output


excel_file = convert_to_excel()

st.download_button(
    label="📥 Download All Metrics as Excel",
    data=excel_file,
    file_name="job_runtime_metrics.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
