import streamlit as st
import pandas as pd
import pydeck as pdk
from datetime import date
from datetime import datetime

# Define the Excel file path
excel_fil = "korjournal.xlsx"

# Function to load data (moved to top)
def ladda_data():
    try:
        return pd.read_excel(excel_fil, engine="openpyxl", parse_dates=["Datum"])
    except FileNotFoundError:
        return pd.DataFrame(columns=["Datum", "Startplats", "Slutplats", "Sträcka (km)", "Syfte"])

# Load existing data and initialize session state
df = ladda_data()
if 'journey_log' not in st.session_state:
    if not df.empty:
        st.session_state.journey_log = df.to_dict(orient="records")
    else:
        st.session_state.journey_log = []

st.title("📘 Avancerad Körjournal")

# ➕ Formulär för att lägga till ny resa
with st.form("add_journey"):
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

# � Ladda upp körjournal från Excel
st.subheader("📤 Ladda upp körjournal från Excel")

excel_upload_fil = st.file_uploader("Välj en Excel-fil (.xlsx)", type=["xlsx"])
if excel_upload_fil is not None:
    try:
        uppladdad_df = pd.read_excel(excel_upload_fil, engine="openpyxl", parse_dates=["Datum"])
        
        # Add uploaded data to session state
        uploaded_records = uppladdad_df.to_dict(orient="records")
        st.session_state.journey_log.extend(uploaded_records)
        
        # Save combined data to Excel
        df_to_save = pd.DataFrame(st.session_state.journey_log)
        df_to_save.to_excel(excel_fil, index=False, engine="openpyxl")
        
        st.success(f"{len(uppladdad_df)} resor importerades!")
        st.rerun()
    except Exception as e:
        st.error(f"Fel vid import: {e}")


if st.session_state.journey_log:
    df = pd.DataFrame(st.session_state.journey_log)

    # 🔍 Filter
    st.sidebar.header("Filtrera resor")
    start_filter = st.sidebar.date_input("Från datum", value=pd.to_datetime(df["Datum"]).min().date(), key="filter_start_date")
    end_filter = st.sidebar.date_input("Till datum", value=pd.to_datetime(df["Datum"]).max().date(), key="filter_end_date")
    syfte_filter = st.sidebar.text_input("Syfte (valfri)", key="filter_syfte")

    # Convert dates for comparison
    df["Datum"] = pd.to_datetime(df["Datum"]).dt.date
    
    filtered_df = df[
        (df["Datum"] >= start_filter) &
        (df["Datum"] <= end_filter)
    ]
    if syfte_filter:
        filtered_df = filtered_df[filtered_df["Syfte"].str.contains(syfte_filter, case=False, na=False)]

    st.subheader("📊 Statistik")
    st.metric("Total sträcka", f"{filtered_df['Sträcka (km)'].sum():.1f} km")
    st.metric("Antal resor", len(filtered_df))
    if len(filtered_df) > 0:
        st.metric("Snittsträcka per resa", f"{filtered_df['Sträcka (km)'].mean():.1f} km")

        # Resor per månad
        filtered_df["Månad"] = pd.to_datetime(filtered_df["Datum"]).dt.strftime("%Y-%m (%B)")
        månad_stat = filtered_df.groupby("Månad").size()
        st.bar_chart(månad_stat)

st.subheader("📜 Filtrerade resor")


# Add delete functionality
if len(filtered_df) > 0:
        # Display the dataframe
        st.dataframe(filtered_df)
        
        # Edit and Delete journey sections
        col_edit, col_delete = st.columns(2)
        
        with col_edit:
            st.subheader("✏️ Redigera resa")
            edit_index = st.selectbox(
                "Välj resa att redigera:",
                options=range(len(filtered_df)),
                format_func=lambda x: f"{filtered_df.iloc[x]['Datum']} - {filtered_df.iloc[x]['Startplats']} → {filtered_df.iloc[x]['Slutplats']}",
                key="edit_selectbox"
            )
            
            if st.button("✏️ Redigera", type="primary", key="edit_button"):
                st.session_state.editing_journey = True
                st.session_state.edit_index = edit_index
                st.session_state.journey_to_edit = filtered_df.iloc[edit_index].to_dict()
                st.rerun()
        
        with col_delete:
            st.subheader("🗑️ Ta bort resa")
            delete_index = st.selectbox(
                "Välj resa att ta bort:",
                options=range(len(filtered_df)),
                format_func=lambda x: f"{filtered_df.iloc[x]['Datum']} - {filtered_df.iloc[x]['Startplats']} → {filtered_df.iloc[x]['Slutplats']}",
                key="delete_selectbox"
            )
            
            if st.button("🗑️ Ta bort", type="secondary", key="delete_button"):
                if len(filtered_df) > 0:
                    # Find the original index in the full journey log
                    journey_to_delete = filtered_df.iloc[delete_index]
                    
                    # Find and remove from session state with more flexible matching
                    for i, journey in enumerate(st.session_state.journey_log):
                        # Convert both dates to comparable format
                        journey_date = journey['Datum']
                        if isinstance(journey_date, str):
                            journey_date = pd.to_datetime(journey_date).date()
                        elif hasattr(journey_date, 'date'):
                            journey_date = journey_date.date()
                        
                        delete_date = journey_to_delete['Datum']
                        if hasattr(delete_date, 'delete'):
                            delete_date = delete_date.date()
                        
                        # More flexible matching - only check core fields that should exist
                        if (journey_date == delete_date and 
                            journey['Startplats'] == journey_to_delete['Startplats'] and
                            journey['Slutplats'] == journey_to_delete['Slutplats'] and
                            journey['Sträcka (km)'] == journey_to_delete['Sträcka (km)'] and
                            journey['Syfte'] == journey_to_delete['Syfte']):
                            del st.session_state.journey_log[i]
                            break
                    
                    # Save updated data to Excel
                    if st.session_state.journey_log:
                        df_to_save = pd.DataFrame(st.session_state.journey_log)
                        df_to_save.to_excel(excel_fil, index=False, engine="openpyxl")
                    else:
                        # If no journeys left, create empty file
                        empty_df = pd.DataFrame(columns=["Datum", "Startplats", "Slutplats", "Sträcka (km)", "Syfte"])
                        empty_df.to_excel(excel_fil, index=False, engine="openpyxl")
                    
                    st.success("Resa borttagen!")
                    st.rerun()


# 📥 Ladda ner Excel
if st.session_state.journey_log and len(filtered_df) > 0:
    excel_buffer = pd.ExcelWriter("temp.xlsx", engine="openpyxl")
    filtered_df.to_excel(excel_buffer, index=False)
    excel_buffer.close()
    
    with open("temp.xlsx", "rb") as file:
        st.download_button(
            "Ladda ner Excel", 
            data=file.read(), 
            file_name="korjournal.xlsx", 
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="download_button"
        )

# Edit journey form
if st.session_state.get('editing_journey', False):
    st.subheader("✏️ Redigera vald resa")
    journey_to_edit = st.session_state.journey_to_edit
    
    with st.form("edit_journey"):
        # Pre-populate form with existing data
        edit_datum = st.date_input("Datum", value=pd.to_datetime(journey_to_edit['Datum']).date(), key="edit_datum")
        
        # Handle time fields if they exist
        if 'Startid' in journey_to_edit and journey_to_edit['Startid']:
            try:
                start_time = datetime.strptime(str(journey_to_edit['Startid']), "%H:%M").time()
            except:
                start_time = datetime.strptime("08:00", "%H:%M").time()
        else:
            start_time = datetime.strptime("08:00", "%H:%M").time()
            
        if 'Sluttid' in journey_to_edit and journey_to_edit['Sluttid']:
            try:
                end_time = datetime.strptime(str(journey_to_edit['Sluttid']), "%H:%M").time()
            except:
                end_time = datetime.strptime("09:00", "%H:%M").time()
        else:
            end_time = datetime.strptime("09:00", "%H:%M").time()
        
        edit_starttid = st.time_input("Starttid", value=start_time, key="edit_starttid")
        edit_sluttid = st.time_input("Sluttid", value=end_time, key="edit_sluttid")
        edit_startplats = st.text_input("Startplats", value=journey_to_edit['Startplats'], key="edit_startplats")
        edit_slutplats = st.text_input("Slutplats", value=journey_to_edit['Slutplats'], key="edit_slutplats")
        edit_stracka = st.number_input("Sträcka (km)", value=float(journey_to_edit['Sträcka (km)']), min_value=0.0, step=0.1, key="edit_stracka")
        edit_syfte = st.text_input("Syfte", value=journey_to_edit['Syfte'], key="edit_syfte")
        
        col1, col2 = st.columns(2)
        with col1:
            update_submitted = st.form_submit_button("💾 Uppdatera", type="primary")
        with col2:
            cancel_edit = st.form_submit_button("❌ Avbryt")
        
        if update_submitted and edit_startplats and edit_slutplats and edit_stracka > 0:
            # Calculate travel time
            tid_format = "%H:%M"
            restid = (datetime.strptime(edit_sluttid.strftime(tid_format), tid_format) -
                      datetime.strptime(edit_starttid.strftime(tid_format), tid_format)).seconds / 60  # minuter
            
            updated_journey = {
                "Datum": edit_datum,
                "Startid": edit_starttid.strftime("%H:%M"),
                "Sluttid": edit_sluttid.strftime("%H:%M"),
                "Restid (min)": int(restid),
                "Startplats": edit_startplats,
                "Slutplats": edit_slutplats,
                "Sträcka (km)": edit_stracka,
                "Syfte": edit_syfte
            }
            
            # Find and update the journey in session state
            original_journey = journey_to_edit
            for i, journey in enumerate(st.session_state.journey_log):
                # Convert dates for comparison
                journey_date = journey['Datum']
                if isinstance(journey_date, str):
                    journey_date = pd.to_datetime(journey_date).date()
                elif hasattr(journey_date, 'date'):
                    journey_date = journey_date.date()
                
                original_date = pd.to_datetime(original_journey['Datum']).date()
                
                # Match the journey to update
                if (journey_date == original_date and 
                    journey['Startplats'] == original_journey['Startplats'] and
                    journey['Slutplats'] == original_journey['Slutplats'] and
                    journey['Sträcka (km)'] == original_journey['Sträcka (km)'] and
                    journey['Syfte'] == original_journey['Syfte']):
                    st.session_state.journey_log[i] = updated_journey
                    break
            
            # Save to Excel
            df_to_save = pd.DataFrame(st.session_state.journey_log)
            df_to_save.to_excel(excel_fil, index=False, engine="openpyxl")
            
            # Clear edit state
            st.session_state.editing_journey = False
            if 'journey_to_edit' in st.session_state:
                del st.session_state['journey_to_edit']
            if 'edit_index' in st.session_state:
                del st.session_state['edit_index']
            
            st.success("Resa uppdaterad!")
            st.rerun()
        
        if cancel_edit:
            # Clear edit state
            st.session_state.editing_journey = False
            if 'journey_to_edit' in st.session_state:
                del st.session_state['journey_to_edit']
            if 'edit_index' in st.session_state:
                del st.session_state['edit_index']
            st.rerun()


else:
    st.info("Ingen resa har loggats ännu.")
