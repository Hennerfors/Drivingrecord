import streamlit as st
import pandas as pd
from datetime import date, datetime
import os

# --- KONFIGURATION ---
st.set_page_config(page_title="Körjournal", page_icon="🚗", layout="wide")

EXCEL_FIL = "korjournal.xlsx"
LOG_FIL = "korjournal_log.txt"

# --- FUNKTIONER ---

def ladda_data():
    """Laddar data från Excel och säkerställer korrekta datatyper."""
    if not os.path.exists(EXCEL_FIL):
        return pd.DataFrame(columns=[
            "Datum", "Starttid", "Sluttid", "Restid (min)", 
            "Startplats", "Slutplats", "Sträcka (km)", "Syfte"
        ])
    
    try:
        df = pd.read_excel(EXCEL_FIL, engine="openpyxl")
        if "Datum" in df.columns:
            df["Datum"] = pd.to_datetime(df["Datum"]).dt.date
        
        # Se till att tider tolkas korrekt för editorn
        for col in ["Starttid", "Sluttid"]:
            if col in df.columns:
                # Försök konvertera till time-objekt om det är strängar
                df[col] = pd.to_datetime(df[col].astype(str), format='%H:%M', errors='coerce').dt.time
                
        return df
    except Exception as e:
        st.error(f"Fel vid inläsning av data: {e}")
        return pd.DataFrame()

def spara_data(df, action_label="Okänd ändring"):
    """Sparar DataFrame till Excel."""
    try:
        df_save = df.copy()
        
        # Konvertera datum till sträng
        if "Datum" in df_save.columns:
            df_save["Datum"] = pd.to_datetime(df_save["Datum"]).dt.strftime("%Y-%m-%d")
            
        # Konvertera tider till sträng (HH:MM)
        for col in ["Starttid", "Sluttid"]:
            if col in df_save.columns:
                df_save[col] = df_save[col].apply(lambda x: x.strftime("%H:%M") if hasattr(x, "strftime") else str(x))
            
        df_save.to_excel(EXCEL_FIL, index=False, engine="openpyxl")
        
        # Logga
        with open(LOG_FIL, "a", encoding="utf-8") as f:
            tidsstampel = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            f.write(f"[{tidsstampel}] {action_label}: {len(df)} resor sparades.\n")
            
        return True
    except PermissionError:
        st.error("🚨 KAN INTE SPARA! Excel-filen är öppen i ett annat program. Stäng den och försök igen.")
        return False
    except Exception as e:
        st.error(f"Kunde inte spara data: {e}")
        return False

def rakna_ut_restid(start, slut):
    try:
        # Hantera både strängar och tidsobjekt
        s_str = start.strftime("%H:%M") if hasattr(start, "strftime") else str(start)
        e_str = slut.strftime("%H:%M") if hasattr(slut, "strftime") else str(slut)
        
        t1 = datetime.strptime(s_str, "%H:%M")
        t2 = datetime.strptime(e_str, "%H:%M")
        diff = (t2 - t1).seconds / 60
        return int(diff)
    except:
        return 0

# --- HUVUDPROGRAM ---

if "journey_log_df" not in st.session_state:
    st.session_state.journey_log_df = ladda_data()

st.title("🚗 Körjournal (Lokal)")

# --- 1. SNABBREGISTRERING ---
st.subheader("🏢 Snabbregistrera")
favoritresor = {
    "Till jobbet": {
        "Startplats": "Bruksgatan 4D, 78474 Borlänge", "Slutplats": "Kajvägen 13 Parking, Ludvika",
        "Starttid": "00:30", "Sluttid": "01:07", "Sträcka (km)": 45.7, "Syfte": "Resa till jobbet"
    },
    "Från jobbet": {
        "Startplats": "Kajvägen 13 Parking, Ludvika", "Slutplats": "Bruksgatan 4D, 78474 Borlänge",
        "Starttid": "22:10", "Sluttid": "22:47", "Sträcka (km)": 45.7, "Syfte": "Resa hem från jobbet"
    }
}

col1, col2 = st.columns([1, 2])
with col1:
    work_datum = st.date_input("Datum", value=date.today())
with col2:
    st.write("")
    st.write("")
    if st.button("➕ Lägg till jobb-resor"):
        nya_rader = []
        for namn, resa in favoritresor.items():
            t_start = datetime.strptime(resa["Starttid"], "%H:%M").time()
            t_slut = datetime.strptime(resa["Sluttid"], "%H:%M").time()
            
            ny_rad = {
                "Datum": work_datum, "Starttid": t_start, "Sluttid": t_slut,
                "Restid (min)": rakna_ut_restid(t_start, t_slut),
                "Startplats": resa["Startplats"], "Slutplats": resa["Slutplats"],
                "Sträcka (km)": resa["Sträcka (km)"], "Syfte": resa["Syfte"]
            }
            nya_rader.append(ny_rad)
        
        ny_df = pd.DataFrame(nya_rader)
        st.session_state.journey_log_df = pd.concat([st.session_state.journey_log_df, ny_df], ignore_index=True)
        spara_data(st.session_state.journey_log_df, "Snabbregistrering")
        st.rerun()

# --- 2. TABELL ---
st.markdown("---")
st.subheader("📋 Alla Resor")

column_config = {
    "Datum": st.column_config.DateColumn("Datum", format="YYYY-MM-DD"),
    "Starttid": st.column_config.TimeColumn("Start", format="HH:mm"),
    "Sluttid": st.column_config.TimeColumn("Slut", format="HH:mm"),
    "Restid (min)": st.column_config.NumberColumn("Min", disabled=True),
    "Sträcka (km)": st.column_config.NumberColumn("Km", format="%.1f"),
}

edited_df = st.data_editor(
    st.session_state.journey_log_df,
    column_config=column_config,
    num_rows="dynamic",
    use_container_width=True,
    hide_index=True
)

if not edited_df.equals(st.session_state.journey_log_df):
    # Räkna om tider
    for index, row in edited_df.iterrows():
        try:
            val = rakna_ut_restid(row["Starttid"], row["Sluttid"])
            if val > 0: edited_df.at[index, "Restid (min)"] = val
        except: pass
    
    st.session_state.journey_log_df = edited_df
    if spara_data(edited_df, "Manuell ändring"):
        st.toast("✅ Sparat!")

# --- 3. EXCEL-IMPORT (För moln-användning) ---
st.markdown("---")
with st.expander("📤 Ladda upp Excel (Om du bytt dator/moln)"):
    uploaded_file = st.file_uploader("Välj din korjournal.xlsx", type="xlsx")
    if uploaded_file and st.button("Importera fil"):
        try:
            ny_data = pd.read_excel(uploaded_file, engine="openpyxl")
            # Konvertera
            if "Datum" in ny_data.columns: ny_data["Datum"] = pd.to_datetime(ny_data["Datum"]).dt.date
            for c in ["Starttid", "Sluttid"]:
                if c in ny_data.columns:
                    ny_data[c] = pd.to_datetime(ny_data[c].astype(str), format='%H:%M', errors='coerce').dt.time
            
            st.session_state.journey_log_df = ny_data
            spara_data(ny_data, "Import")
            st.success("Data importerad!")
            st.rerun()
        except Exception as e:
            st.error(f"Fel: {e}")
