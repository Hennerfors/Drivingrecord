import streamlit as st
import pandas as pd
from datetime import date, datetime
import io
import os

# Försök importera Github, men krascha inte om det saknas lokalt
try:
    from github import Github
    GITHUB_AVAILABLE = True
except ImportError:
    GITHUB_AVAILABLE = False

# Konfigurera sidlayout
st.set_page_config(page_title="Körjournal", page_icon="🚗", layout="wide")

excel_fil = "korjournal.xlsx"

# --- NY FUNKTION: SPARA TILL GITHUB ---
def save_to_github(df):
    """Sparar dataframe direkt till GitHub-repo."""
    if not GITHUB_AVAILABLE:
        return False, "PyGithub saknas i requirements.txt"
    
    # Hämta hemligheter
    token = st.secrets.get("GITHUB_TOKEN")
    repo_name = st.secrets.get("REPO_NAME")
    
    if not token or not repo_name:
        return False, "Saknar GITHUB_TOKEN eller REPO_NAME i secrets."

    try:
        g = Github(token)
        repo = g.get_repo(repo_name)
        
        # Konvertera DataFrame till Excel i minnet (buffer)
        buffer = io.BytesIO()
        
        # Formatera datum till strängar för snygg Excel
        df_save = df.copy()
        if "Datum" in df_save.columns:
            df_save["Datum"] = pd.to_datetime(df_save["Datum"]).dt.strftime("%Y-%m-%d")
            
        df_save.to_excel(buffer, index=False, engine="openpyxl")
        content = buffer.getvalue()
        
        file_path = excel_fil
        
        # Försök uppdatera filen
        try:
            contents = repo.get_contents(file_path)
            repo.update_file(contents.path, f"Uppdaterad {datetime.now()}", content, contents.sha)
            return True, "Uppdaterade filen på GitHub!"
        except:
            # Filen finns inte, skapa den
            repo.create_file(file_path, "Skapade körjournal", content)
            return True, "Skapade ny fil på GitHub!"
            
    except Exception as e:
        return False, f"GitHub-fel: {str(e)}"

# Funktion för att ladda data
def ladda_data():
    try:
        df = pd.read_excel(excel_fil, engine="openpyxl", parse_dates=["Datum"])
        if df.empty: return []
        
        if "Datum" in df.columns:
            df["Datum"] = df["Datum"].dt.date
        
        # Tider till strängar
        for col in ["Startid", "Sluttid"]:
            if col in df.columns:
                df[col] = df[col].apply(lambda x: x.strftime("%H:%M") if hasattr(x, "strftime") else str(x))

        return df.to_dict(orient="records")
    except FileNotFoundError:
        st.info("Ingen lokal fil hittades. (Om du nyss startat appen hämtas data från GitHub vid omstart).")
        return []
    except Exception as e:
        st.error(f"Fel vid inladdning: {e}")
        return []

# Gemensam spar-funktion
def spara_allt(data, action_namn):
    # 1. Uppdatera Session State
    st.session_state.journey_log = data
    
    # 2. Skapa DataFrame
    df = pd.DataFrame(data)
    
    # 3. Spara lokalt (för snabbhet)
    try:
        df_temp = df.copy()
        if "Datum" in df_temp.columns:
            df_temp["Datum"] = pd.to_datetime(df_temp["Datum"]).dt.strftime("%Y-%m-%d")
        df_temp.to_excel(excel_fil, index=False, engine="openpyxl")
    except:
        pass # Ignorera lokala fel i molnet
    
    # 4. SPARA TILL GITHUB (Det viktiga!)
    with st.spinner("Sparar till GitHub (molnet)..."):
        success, msg = save_to_github(df)
        
    if success:
        st.success(f"✅ {action_namn}: Sparat säkert i molnet!")
        st.balloons()
    else:
        st.warning(f"⚠️ Sparad lokalt, men GitHub misslyckades: {msg}")

# --- HUVUDPROGRAM ---

if "journey_log" not in st.session_state:
    st.session_state.journey_log = ladda_data()

st.title("🚗 Körjournal (Auto-Sync)")
st.markdown("---")

# 🏢 Snabbregistrera
st.subheader("🏢 Snabbregistrera arbetsdagens resor")
favoritresor = {
    "Till jobbet": {"Startplats": "Bruksgatan 4D, 78474 Borlänge", "Slutplats": "Kajvägen 13 Parking, Ludvika", "Starttid": "00:30", "Sluttid": "01:07", "Sträcka (km)": 45.7, "Syfte": "Resa till jobbet"},
    "Från jobbet": {"Startplats": "Kajvägen 13 Parking, Ludvika", "Slutplats": "Bruksgatan 4D, 78474 Borlänge", "Starttid": "22:10", "Sluttid": "22:47", "Sträcka (km)": 45.7, "Syfte": "Resa hem från jobbet"}
}

work_datum = st.date_input("Datum för arbetsdagen", value=date.today())

if st.button("Registrera arbetsdagens resor"):
    nya_resor = []
    for namn, resa in favoritresor.items():
        t1 = datetime.strptime(resa["Starttid"], "%H:%M")
        t2 = datetime.strptime(resa["Sluttid"], "%H:%M")
        restid = (t2 - t1).seconds / 60
        ny_resa = {
            "Datum": work_datum, "Startid": resa["Starttid"], "Sluttid": resa["Sluttid"],
            "Restid (min)": int(restid), "Startplats": resa["Startplats"], "Slutplats": resa["Slutplats"],
            "Sträcka (km)": resa["Sträcka (km)"], "Syfte": resa["Syfte"]
        }
        nya_resor.append(ny_resa)

    st.session_state.journey_log.extend(nya_resor)
    spara_allt(st.session_state.journey_log, "Jobbresor")
    st.rerun() # Ladda om för att visa ändringar

st.markdown("---")

# 📊 Visa data
st.subheader("📊 Dina resor")
if st.session_state.journey_log:
    df = pd.DataFrame(st.session_state.journey_log)
    st.dataframe(df)
    
    # Statistik
    total_dist = df["Sträcka (km)"].sum()
    st.metric("Total sträcka", f"{total_dist:.1f} km")

# Formulär för ny resa
st.markdown("---")
with st.form("add_journey_form"):
    st.subheader("Lägg till ny resa")
    datum = st.date_input("Datum", value=date.today())
    c1, c2 = st.columns(2)
    starttid = c1.time_input("Starttid")
    sluttid = c2.time_input("Sluttid")
    startplats = st.text_input("Startplats")
    slutplats = st.text_input("Slutplats")
    stracka = st.number_input("Sträcka (km)", min_value=0.0, step=0.1)
    syfte = st.text_input("Syfte")
    
    if st.form_submit_button("Spara resa"):
        t1 = datetime.combine(date.today(), starttid)
        t2 = datetime.combine(date.today(), sluttid)
        restid = (t2 - t1).seconds / 60
        
        ny_resa = {
            "Datum": datum,
            "Startid": starttid.strftime("%H:%M"),
            "Sluttid": sluttid.strftime("%H:%M"),
            "Restid (min)": int(restid),
            "Startplats": startplats, "Slutplats": slutplats,
            "Sträcka (km)": stracka, "Syfte": syfte
        }
        st.session_state.journey_log.append(ny_resa)
        spara_allt(st.session_state.journey_log, "Ny resa")
        st.rerun()

# 🗑️ Hantera (Ta bort sista)
if st.session_state.journey_log:
    st.markdown("---")
    if st.checkbox("Visa avancerat (Ta bort resor)"):
        journey_options = [f"{i}: {r['Datum']} {r.get('Startplats','?')}" for i, r in enumerate(st.session_state.journey_log)]
        selected = st.selectbox("Välj resa att radera", range(len(journey_options)), format_func=lambda x: journey_options[x])
        
        if st.button("🗑️ Ta bort vald resa"):
            del st.session_state.journey_log[selected]
            spara_allt(st.session_state.journey_log, "Borttagning")
            st.rerun()
