import os
import streamlit as st
import pandas as pd
from datetime import date, datetime

# Försök importera streamlit_gsheets; om paketet saknas, använd lokal Excel-fallback.
import importlib
import importlib.util

spec = importlib.util.find_spec("streamlit_gsheets")
if spec is not None:
    try:
        module = importlib.import_module("streamlit_gsheets")
        GSheetsConnection = getattr(module, "GSheetsConnection", None)
        USE_GSHEETS = GSheetsConnection is not None
    except Exception:
        GSheetsConnection = None
        USE_GSHEETS = False
else:
    GSheetsConnection = None
    USE_GSHEETS = False

# --- KONFIGURATION ---
st.set_page_config(page_title="Körjournal Cloud", page_icon="🚗", layout="wide")

# --- FUNKTIONER ---

def get_data():
    """Hämtar data från Google Sheets eller lokal Excel som fallback."""
    expected_cols = ["Datum", "Starttid", "Sluttid", "Restid (min)",
                     "Startplats", "Slutplats", "Sträcka (km)", "Syfte"]

    if USE_GSHEETS and GSheetsConnection is not None:
        try:
            conn = st.connection("gsheets", type=GSheetsConnection)
            df = conn.read(ttl=0)
            for col in expected_cols:
                if col not in df.columns:
                    df[col] = pd.Series(dtype='object')
            df["Datum"] = pd.to_datetime(df["Datum"], errors='coerce').dt.date
            df = df.dropna(subset=["Datum"])
            return df
        except Exception as e:
            st.error(f"Kunde inte hämta data från Google Sheets: {e}")
            return pd.DataFrame(columns=expected_cols)
    else:
        # Lokal Excel-fallback
        excel_path = "korjournal.xlsx"
        if os.path.exists(excel_path):
            try:
                df = pd.read_excel(excel_path, engine="openpyxl")
                for col in expected_cols:
                    if col not in df.columns:
                        df[col] = pd.Series(dtype='object')
                df["Datum"] = pd.to_datetime(df["Datum"], errors='coerce').dt.date
                df = df.dropna(subset=["Datum"])
                return df
            except Exception as e:
                st.error(f"Kunde inte läsa lokal Excel-fil: {e}")
                return pd.DataFrame(columns=expected_cols)
        else:
            return pd.DataFrame(columns=expected_cols)

def save_data(df):
    """Sparar dataframe till Google Sheets eller lokal Excel som fallback."""
    if USE_GSHEETS and GSheetsConnection is not None:
        try:
            conn = st.connection("gsheets", type=GSheetsConnection)
            df_save = df.copy()
            df_save["Datum"] = pd.to_datetime(df_save["Datum"]).dt.strftime("%Y-%m-%d")
            conn.update(data=df_save)
            st.cache_data.clear() # Rensa cache så vi ser ändringen direkt
            return True
        except Exception as e:
            st.error(f"Kunde inte spara till Google Sheets: {e}")
            return False
    else:
        try:
            df_save = df.copy()
            if "Datum" in df_save.columns:
                df_save["Datum"] = pd.to_datetime(df_save["Datum"]).dt.strftime("%Y-%m-%d")
            df_save.to_excel("korjournal.xlsx", index=False, engine="openpyxl")
            return True
        except Exception as e:
            st.error(f"Kunde inte spara till lokal Excel-fil: {e}")
            return False

def rakna_ut_restid(start_str, slut_str):
    try:
        fmt = "%H:%M"
        # Hantera om det kommer in som datetime.time objekt
        s_str = start_str.strftime(fmt) if hasattr(start_str, "strftime") else str(start_str)
        e_str = slut_str.strftime(fmt) if hasattr(slut_str, "strftime") else str(slut_str)
        
        t1 = datetime.strptime(s_str, fmt)
        t2 = datetime.strptime(e_str, fmt)
        diff = (t2 - t1).seconds / 60
        return int(diff)
    except:
        return 0

# --- HUVUDPROGRAM ---

st.title("🚗 Körjournal (Cloud)")

# Ladda data direkt (vi behöver inte session state på samma sätt med GSheets som "databas")
# Men vi använder det för att hålla redigeringar stabila
if "journey_df" not in st.session_state:
    st.session_state.journey_df = get_data()

# Knapp för att tvinga uppdatering
if st.sidebar.button("🔄 Ladda om data"):
    st.session_state.journey_df = get_data()
    st.rerun()

# --- 1. SNABBREGISTRERING ---
st.subheader("🏢 Snabbregistrera")
favoritresor = {
    "Till jobbet": {
        "Startplats": "Bruksgatan 4D, 78474 Borlänge",
        "Slutplats": "Kajvägen 13 Parking, Ludvika",
        "Starttid": "00:30", "Sluttid": "01:07",
        "Sträcka (km)": 45.7, "Syfte": "Resa till jobbet"
    },
    "Från jobbet": {
        "Startplats": "Kajvägen 13 Parking, Ludvika",
        "Slutplats": "Bruksgatan 4D, 78474 Borlänge",
        "Starttid": "22:10", "Sluttid": "22:47",
        "Sträcka (km)": 45.7, "Syfte": "Resa hem från jobbet"
    }
}

col_date, col_btn = st.columns([1, 2])
with col_date:
    work_datum = st.date_input("Datum", value=date.today())

with col_btn:
    st.write(" ")
    st.write(" ")
    if st.button("➕ Lägg till: Till & Från Jobbet"):
        nya_rader = []
        for namn, resa in favoritresor.items():
            restid = rakna_ut_restid(resa["Starttid"], resa["Sluttid"])
            ny_rad = {
                "Datum": work_datum,
                "Starttid": resa["Starttid"],
                "Sluttid": resa["Sluttid"],
                "Restid (min)": restid,
                "Startplats": resa["Startplats"],
                "Slutplats": resa["Slutplats"],
                "Sträcka (km)": resa["Sträcka (km)"],
                "Syfte": resa["Syfte"]
            }
            nya_rader.append(ny_rad)
        
        ny_df = pd.DataFrame(nya_rader)
        # Slå ihop och spara
        updated_df = pd.concat([st.session_state.journey_df, ny_df], ignore_index=True)
        if save_data(updated_df):
            st.session_state.journey_df = updated_df
            st.success("✅ Resor sparade till Google Sheets!")
            st.rerun()

st.markdown("---")

# --- 2. REDIGERA I TABELL ---
st.subheader("📋 Alla Resor")
st.info("Ändringar sparas automatiskt till Google Sheets när du redigerar i tabellen.")

column_config = {
    "Datum": st.column_config.DateColumn("Datum", format="YYYY-MM-DD", step=1),
    "Starttid": st.column_config.TimeColumn("Start", format="HH:mm"),
    "Sluttid": st.column_config.TimeColumn("Slut", format="HH:mm"),
    "Restid (min)": st.column_config.NumberColumn("Min", disabled=True),
    "Startplats": st.column_config.TextColumn("Startplats", width="medium"),
    "Slutplats": st.column_config.TextColumn("Slutplats", width="medium"),
    "Sträcka (km)": st.column_config.NumberColumn("Km", format="%.1f", min_value=0),
    "Syfte": st.column_config.TextColumn("Syfte", width="medium"),
}

edited_df = st.data_editor(
    st.session_state.journey_df,
    column_config=column_config,
    num_rows="dynamic",
    use_container_width=True,
    key="editor",
    hide_index=True
)

# Kolla om något ändrats jämfört med vad vi hade i minnet
if not edited_df.equals(st.session_state.journey_df):
    # Enkel beräkning av restid (samma som förut)
    for index, row in edited_df.iterrows():
        try:
            val = rakna_ut_restid(row["Starttid"], row["Sluttid"])
            if val > 0:
                edited_df.at[index, "Restid (min)"] = val
        except:
            pass
            
    # Spara till Google Sheets
    if save_data(edited_df):
        st.session_state.journey_df = edited_df
        st.toast("💾 Sparat till molnet!", icon="☁️")
        # Vi gör ingen rerun här direkt för det kan störa skrivandet, 
        # men datan är sparad.

# --- 3. STATISTIK ---
with st.sidebar:
    st.header("📊 Statistik")
    if not st.session_state.journey_df.empty:
        df = st.session_state.journey_df
        total_km = df["Sträcka (km)"].sum()
        st.metric("Total sträcka", f"{total_km:.0f} km")
        st.metric("Antal resor", len(df))
        
        st.markdown("---")
        # Månadsstatistik
        try:
            chart_df = df.copy()
            chart_df["Datum"] = pd.to_datetime(chart_df["Datum"])
            chart_df["Månad"] = chart_df["Datum"].dt.strftime("%Y-%m")
            monthly = chart_df.groupby("Månad")["Sträcka (km)"].sum()
            st.bar_chart(monthly)
        except:
            pass
