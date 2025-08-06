import streamlit as st
import pandas as pd
import pydeck as pdk
from datetime import date
from datetime import datetime

# Konfigurera sidlayout
st.set_page_config(page_title="Körjournal", page_icon="🚗", layout="wide")

excel_fil = "korjournal.xlsx"

# Funktion för att ladda data från Excel
def ladda_data():
    try:
        df = pd.read_excel(excel_fil, engine="openpyxl", parse_dates=["Datum"])
        return df.to_dict(orient="records")
    except FileNotFoundError:
        st.info("Ingen körjournal hittades. Skapar ny.")
        return []
    except Exception as e:
        st.error(f"Fel vid inladdning av data: {e}")
        return []

# Ladda befintlig data eller skapa ny
if "journey_log" not in st.session_state:
    st.session_state.journey_log = ladda_data()

st.title("🚗 Körjournal")
st.markdown("---")

# 🏢 Snabbregistrera arbetsdagens resor
st.subheader("🏢 Snabbregistrera arbetsdagens resor")

# Förinställda tider och platser
favoritresor = {
    "Till jobbet": {
        "Startplats": "Bruksgatan 4D, 78474 Borlänge",
        "Slutplats": "Kajvägen 13 Parking, Ludvika",
        "Starttid": "00:30",
        "Sluttid": "01:07",
        "Sträcka (km)": 45.7,
        "Syfte": "Resa till jobbet"
    },
    "Från jobbet": {
        "Startplats": "Kajvägen 13 Parking, Ludvika",
        "Slutplats": "Bruksgatan 4D, 78474 Borlänge",
        "Starttid": "22:10",
        "Sluttid": "22:47",
        "Sträcka (km)": 45.7,
        "Syfte": "Resa hem från jobbet"
    }
}

work_datum = st.date_input("Datum för arbetsdagen", value=date.today(), key="work_date")

if st.button("Registrera arbetsdagens resor", key="add_work_journeys"):
    nya_resor = []
    for namn, resa in favoritresor.items():
        restid = (datetime.strptime(resa["Sluttid"], "%H:%M") -
                  datetime.strptime(resa["Starttid"], "%H:%M")).seconds / 60

        ny_resa = {
            "Datum": work_datum,
            "Startid": resa["Starttid"],
            "Sluttid": resa["Sluttid"],
            "Restid (min)": int(restid),
            "Startplats": resa["Startplats"],
            "Slutplats": resa["Slutplats"],
            "Sträcka (km)": resa["Sträcka (km)"],
            "Syfte": resa["Syfte"]
        }
        nya_resor.append(ny_resa)

    # Add to session state
    st.session_state.journey_log.extend(nya_resor)
    
    # Save to Excel
    df_to_save = pd.DataFrame(st.session_state.journey_log)
    df_to_save.to_excel(excel_fil, index=False, engine="openpyxl")
    st.success("Resorna till och från jobbet har registrerats!")
    st.rerun()

st.markdown("---")

# Sidopanel för debug och diagnostik
st.sidebar.title("📊 Diagnostik")
st.sidebar.info(f"Session State Resor: {len(st.session_state.journey_log)}")

# Försök att läsa Excel för jämförelse
try:
    debug_df = pd.read_excel(excel_fil, engine="openpyxl")
    st.sidebar.info(f"Excel Fil Resor: {len(debug_df)}")
except:
    st.sidebar.warning("Kan inte läsa Excel fil")

if st.sidebar.button("Synkronisera från Excel"):
    st.session_state.journey_log = ladda_data()
    st.sidebar.success("Data uppdaterad från Excel!")
    st.rerun()

# Formulär för att lägga till ny resa
with st.form("add_journey_form"):
    st.subheader("Lägg till ny resa")
    datum = st.date_input("Datum", value=date.today(), key="add_datum")
    starttid = st.time_input("Starttid", key="add_starttid")
    sluttid = st.time_input("Sluttid", key="add_sluttid")
    startplats = st.text_input("Startplats", key="add_startplats")
    slutplats = st.text_input("Slutplats", key="add_slutplats")
    stracka = st.number_input("Sträcka (km)", min_value=0.0, step=0.1, key="add_stracka")
    syfte = st.text_input("Syfte", key="add_syfte")
    submitted = st.form_submit_button("Lägg till")

    if submitted and startplats and slutplats and stracka > 0:
        # Calculate travel time
        tid_format = "%H:%M"
        restid = (datetime.strptime(sluttid.strftime(tid_format), tid_format) -
                  datetime.strptime(starttid.strftime(tid_format), tid_format)).seconds / 60  # minuter
        
        ny_resa = {
            "Datum": datum,
            "Startid": starttid.strftime("%H:%M"),
            "Sluttid": sluttid.strftime("%H:%M"),
            "Restid (min)": int(restid),
            "Startplats": startplats,
            "Slutplats": slutplats,
            "Sträcka (km)": stracka,
            "Syfte": syfte
        }
        
        # Add to session state
        st.session_state.journey_log.append(ny_resa)
        
        # Save to Excel
        df_to_save = pd.DataFrame(st.session_state.journey_log)
        df_to_save.to_excel(excel_fil, index=False, engine="openpyxl")
        st.success("Resa sparad!")
        st.rerun()  # Refresh the app to show new data

# ➕ Formulär för att lägga till flera resor
st.subheader("📅 Lägg till flera resor")

# Välj flera datum
datum_lista = st.multiselect("Välj datum", options=[d.date() for d in pd.date_range(date(2024, 1, 1), date.today())])

# Gemensamma uppgifter
starttid_multi = st.time_input("Starttid", key="multi_starttid")
sluttid_multi = st.time_input("Sluttid", key="multi_sluttid")
startplats_multi = st.text_input("Startplats", key="multi_startplats")
slutplats_multi = st.text_input("Slutplats", key="multi_slutplats")
stracka_multi = st.number_input("Sträcka (km)", min_value=0.0, step=0.1, key="multi_stracka")
syfte_multi = st.text_input("Syfte", key="multi_syfte")

if st.button("Lägg till resor", key="add_multiple_journeys"):
    if datum_lista and startplats_multi and slutplats_multi and stracka_multi > 0:
        nya_resor = []
        for d in datum_lista:
            restid = (datetime.strptime(sluttid_multi.strftime("%H:%M"), "%H:%M") -
                      datetime.strptime(starttid_multi.strftime("%H:%M"), "%H:%M")).seconds / 60

            resa = {
                "Datum": d,  # d is already a date object now
                "Startid": starttid_multi.strftime("%H:%M"),
                "Sluttid": sluttid_multi.strftime("%H:%M"),
                "Restid (min)": int(restid),
                "Startplats": startplats_multi,
                "Slutplats": slutplats_multi,
                "Sträcka (km)": stracka_multi,
                "Syfte": syfte_multi
            }
            nya_resor.append(resa)

        # Add to session state
        st.session_state.journey_log.extend(nya_resor)
        
        # Save to Excel
        df_to_save = pd.DataFrame(st.session_state.journey_log)
        df_to_save.to_excel(excel_fil, index=False, engine="openpyxl")
        st.success(f"{len(nya_resor)} resor har lagts till!")
        st.rerun()
    else:
        st.error("Vänligen fyll i alla fält och välj minst ett datum.")

# 📤 Ladda upp körjournal från Excel
st.subheader("📤 Ladda upp körjournal från Excel")

uploaded_file = st.file_uploader("Välj Excel-fil (.xlsx)", type="xlsx")

if uploaded_file is not None:
    try:
        df_upload = pd.read_excel(uploaded_file, engine="openpyxl", parse_dates=["Datum"])
        
        # Show preview of data
        st.subheader("Förhandsgranskning av data:")
        st.dataframe(df_upload.head())
        
        if st.button("Importera data", key="import_excel"):
            # Convert to list of dicts and merge with existing data
            imported_data = df_upload.to_dict(orient="records")
            st.session_state.journey_log.extend(imported_data)
            
            # Save combined data to Excel
            df_combined = pd.DataFrame(st.session_state.journey_log)
            df_combined.to_excel(excel_fil, index=False, engine="openpyxl")
            
            st.success(f"Importerade {len(imported_data)} resor!")
            st.rerun()
            
    except Exception as e:
        st.error(f"Fel vid inläsning av filen: {e}")

# 📊 Visa och filtrera resor
st.markdown("---")
st.subheader("📊 Dina resor")

if st.session_state.journey_log:
    df = pd.DataFrame(st.session_state.journey_log)
    
    # Ensure Datum column is datetime
    if not pd.api.types.is_datetime64_any_dtype(df["Datum"]):
        df["Datum"] = pd.to_datetime(df["Datum"]).dt.date
    else:
        df["Datum"] = df["Datum"].dt.date
    
    # Filter sidebar
    with st.sidebar:
        st.header("Filter")
        
        # Date range filter
        min_date = df["Datum"].min()
        max_date = df["Datum"].max()
        
        date_range = st.date_input(
            "Välj datumintervall",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date
        )
        
        # Purpose filter
        unique_purposes = df["Syfte"].unique().tolist()
        selected_purposes = st.multiselect(
            "Filtrera på syfte",
            options=unique_purposes,
            default=unique_purposes
        )
    
    # Apply filters
    if len(date_range) == 2:
        mask = (df["Datum"] >= date_range[0]) & (df["Datum"] <= date_range[1])
        df_filtered = df[mask]
    else:
        df_filtered = df
    
    df_filtered = df_filtered[df_filtered["Syfte"].isin(selected_purposes)]
    
    # Debug info in sidebar
    st.sidebar.info(f"Filtrerade resor: {len(df_filtered)}")
    
    # Ta bort alla resor längst ner på sidopanelen
    if st.session_state.journey_log:
        st.sidebar.markdown("---")
        st.sidebar.warning("⚠️ Farlig zon")
        
        if st.sidebar.checkbox("Jag förstår att detta tar bort ALLA resor"):
            if st.sidebar.button("🗑️ Ta bort alla resor"):
                st.session_state.journey_log = []
                # Also clear the Excel file
                pd.DataFrame().to_excel(excel_fil, index=False, engine="openpyxl")
                st.sidebar.success("Alla resor har tagits bort!")
                st.rerun()
    
    # Display filtered data
    st.dataframe(df_filtered)
    
    # 📥 Ladda ner Excel-fil
    if st.button("Ladda ner som Excel"):
        df_download = pd.DataFrame(st.session_state.journey_log)
        df_download.to_excel("temp.xlsx", index=False, engine="openpyxl")
        
        with open("temp.xlsx", "rb") as file:
            st.download_button(
                label="💾 Ladda ner körjournal.xlsx",
                data=file,
                file_name="körjournal.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    # Statistics
    st.subheader("📈 Statistik")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        total_distance = df_filtered["Sträcka (km)"].sum()
        st.metric("Total sträcka", f"{total_distance:.1f} km")
    
    with col2:
        total_journeys = len(df_filtered)
        st.metric("Antal resor", total_journeys)
    
    with col3:
        if total_journeys > 0:
            avg_distance = total_distance / total_journeys
            st.metric("Genomsnittlig sträcka", f"{avg_distance:.1f} km")
    
    # Monthly statistics
    if not df_filtered.empty:
        df_stats = df_filtered.copy()
        df_stats["Månad"] = pd.to_datetime(df_stats["Datum"]).dt.to_period("M")
        monthly_stats = df_stats.groupby("Månad").agg({
            "Sträcka (km)": "sum",
            "Datum": "count"
        }).rename(columns={"Datum": "Antal resor"})
        
        # Convert period index to string with month names
        monthly_stats.index = monthly_stats.index.to_timestamp().strftime("%Y %B")
        
        st.subheader("📊 Månadsstatistik")
        st.bar_chart(monthly_stats["Sträcka (km)"])

# 🗑️ Ta bort resor
st.markdown("---")
st.subheader("🗑️ Hantera resor")

# Redigera specifik resa
if st.session_state.journey_log:
    st.subheader("✏️ Redigera resa")
    
    # Create a selectbox with journey info
    journey_options = []
    for i, journey in enumerate(st.session_state.journey_log):
        date_str = journey["Datum"].strftime("%Y-%m-%d") if hasattr(journey["Datum"], "strftime") else str(journey["Datum"])
        journey_str = f"{i}: {date_str} - {journey['Startplats']} → {journey['Slutplats']}"
        journey_options.append(journey_str)
    
    selected_journey_idx = st.selectbox("Välj resa att redigera", range(len(journey_options)), 
                                       format_func=lambda x: journey_options[x])
    
    if selected_journey_idx is not None:
        selected_journey = st.session_state.journey_log[selected_journey_idx]
        
        with st.form("edit_journey_form"):
            st.write(f"Redigerar resa {selected_journey_idx}")
            
            # Pre-fill form with existing data
            edit_datum = st.date_input("Datum", value=selected_journey["Datum"] if hasattr(selected_journey["Datum"], "date") else selected_journey["Datum"])
            edit_starttid = st.time_input("Starttid", value=datetime.strptime(selected_journey["Startid"], "%H:%M").time())
            edit_sluttid = st.time_input("Sluttid", value=datetime.strptime(selected_journey["Sluttid"], "%H:%M").time())
            edit_startplats = st.text_input("Startplats", value=selected_journey["Startplats"])
            edit_slutplats = st.text_input("Slutplats", value=selected_journey["Slutplats"])
            edit_stracka = st.number_input("Sträcka (km)", value=selected_journey["Sträcka (km)"], min_value=0.0, step=0.1)
            edit_syfte = st.text_input("Syfte", value=selected_journey["Syfte"])
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.form_submit_button("💾 Spara ändringar"):
                    # Calculate new travel time
                    restid = (datetime.combine(date.today(), edit_sluttid) - 
                             datetime.combine(date.today(), edit_starttid)).seconds / 60
                    
                    # Update the journey
                    st.session_state.journey_log[selected_journey_idx] = {
                        "Datum": edit_datum,
                        "Startid": edit_starttid.strftime("%H:%M"),
                        "Sluttid": edit_sluttid.strftime("%H:%M"),
                        "Restid (min)": int(restid),
                        "Startplats": edit_startplats,
                        "Slutplats": edit_slutplats,
                        "Sträcka (km)": edit_stracka,
                        "Syfte": edit_syfte
                    }
                    
                    # Save to Excel
                    df_to_save = pd.DataFrame(st.session_state.journey_log)
                    df_to_save.to_excel(excel_fil, index=False, engine="openpyxl")
                    
                    st.success("Resa uppdaterad!")
                    st.rerun()
            
            with col2:
                if st.form_submit_button("🗑️ Ta bort resa"):
                    # Remove the journey
                    del st.session_state.journey_log[selected_journey_idx]
                    
                    # Save to Excel
                    df_to_save = pd.DataFrame(st.session_state.journey_log)
                    df_to_save.to_excel(excel_fil, index=False, engine="openpyxl")
                    
                    st.success("Resa borttagen!")
                    st.rerun()

else:
    st.info("Ingen resa har loggats ännu.")
