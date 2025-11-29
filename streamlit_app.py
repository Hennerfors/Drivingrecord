import streamlit as st
import pandas as pd
from datetime import date, datetime
import io
import os

# Försök importera Github (krävs för moln-sparande)
try:
    from github import Github
    GITHUB_AVAILABLE = True
except ImportError:
    GITHUB_AVAILABLE = False

# --- KONFIGURATION ---
st.set_page_config(page_title="Körjournal", page_icon="🚗", layout="wide")

EXCEL_FIL = "korjournal.xlsx"

# --- GITHUB FUNKTIONER ---
def sync_to_github(df):
    """Sparar dataframe till GitHub för permanent lagring."""
    if not GITHUB_AVAILABLE:
        return False, "PyGithub saknas."
    
    token = st.secrets.get("GITHUB_TOKEN")
    repo_name = st.secrets.get("REPO_NAME")
    
    if not token or not repo_name:
        return False, "Saknar GITHUB_TOKEN eller REPO_NAME i secrets."

    try:
        g = Github(token)
        repo = g.get_repo(repo_name)
        
        # Skapa Excel-fil i minnet
        buffer = io.BytesIO()
        df_save = df.copy()
        
        # Snygga till datum för Excel
        if "Datum" in df_save.columns:
            df_save["Datum"] = pd.to_datetime(df_save["Datum"]).dt.strftime("%Y-%m-%d")
            
        df_save.to_excel(buffer, index=False, engine="openpyxl")
        content = buffer.getvalue()
        
        # Uppdatera eller skapa fil på GitHub
        try:
            contents = repo.get_contents(EXCEL_FIL)
            repo.update_file(contents.path, f"Uppdaterad {datetime.now()}", content, contents.sha)
        except:
            repo.create_file(EXCEL_FIL, "Skapade körjournal", content)
            
        return True, "Sparat till GitHub!"
    except Exception as e:
        return False, f"GitHub-fel: {e}"

def spara_och_synka(resa_lista, action_namn):
    """
    Central funktion som sparar till:
    1. Session State
    2. Lokal fil (för snabbhet)
    3. GitHub (för säkerhet)
    """
    # 1. Uppdatera Session State
    st.session_state.journey_log = resa_lista
    
    # 2. Skapa DataFrame
    df = pd.DataFrame(resa_lista)
    
    # 3. Spara lokalt
    try:
        df_local = df.copy()
        if "Datum" in df_local.columns:
            df_local["Datum"] = pd.to_datetime(df_local["Datum"]).dt.strftime("%Y-%m-%d")
        df_local.to_excel(EXCEL_FIL, index=False, engine="openpyxl")
    except:
        pass # Ignorera lokala fel
        
    # 4. Spara till GitHub (Visa spinner)
    with st.spinner(f"Sparar '{action_namn}' till molnet..."):
        success, msg = sync_to_github(df)
        
    if success:
        st.toast(f"✅ {action_namn}: Sparat i molnet!", icon="☁️")
    else:
        st.error(f"⚠️ Kunde inte spara till GitHub: {msg}")

# --- LADDA DATA ---
def ladda_data():
    try:
        # Läs lokal fil (som Streamlit hämtat från GitHub vid start)
        df = pd.read_excel(EXCEL_FIL, engine="openpyxl")
        
        if df.empty: return []

        # Fixa datumformat
        if "Datum" in df.columns:
            df["Datum"] = pd.to_datetime(df["Datum"]).dt.date
            
        # Fixa tider till strängar (HH:MM) för konsekvens
        for col in ["Startid", "Sluttid"]:
            if col in df.columns:
                df[col] = df[col].apply(lambda x: x.strftime("%H:%M") if hasattr(x, "strftime") else str(x))

        return df.to_dict(orient="records")
    except FileNotFoundError:
        st.info("Ingen historik hittades. En ny fil skapas vid första sparning.")
        return []
    except Exception as e:
        st.error(f"Kunde inte ladda data: {e}")
        return []

# --- HUVUDPROGRAM ---

# Initiera data
if "journey_log" not in st.session_state:
    st.session_state.journey_log = ladda_data()

st.title("🚗 Körjournal")
st.markdown("---")

# --- 1. SNABBREGISTRERING ---
st.subheader("🏢 Snabbregistrera arbetsdagens resor")
favoritresor = {
    "Till jobbet": {"Startplats": "Bruksgatan 4D, 78474 Borlänge", "Slutplats": "Kajvägen 13 Parking, Ludvika", "Starttid": "00:30", "Sluttid": "01:07", "Sträcka (km)": 45.7, "Syfte": "Resa till jobbet"},
    "Från jobbet": {"Startplats": "Kajvägen 13 Parking, Ludvika", "Slutplats": "Bruksgatan 4D, 78474 Borlänge", "Starttid": "22:10", "Sluttid": "22:47", "Sträcka (km)": 45.7, "Syfte": "Resa hem från jobbet"}
}

work_datum = st.date_input("Datum för arbetsdagen", value=date.today(), key="work_date")

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
    spara_och_synka(st.session_state.journey_log, "Jobbresor")
    st.rerun()

st.markdown("---")

# --- 2. STATISTIK & DIAGNOSTIK (Återställt från din originalkod) ---
# Sidopanel
st.sidebar.title("📊 Diagnostik")
st.sidebar.info(f"Antal resor: {len(st.session_state.journey_log)}")

if st.session_state.journey_log:
    # Visa senaste 5 i sidebar
    st.sidebar.markdown("**Senaste 5 resor:**")
    for i, resa in enumerate(st.session_state.journey_log[-5:]):
        d = resa.get("Datum", "?")
        s = resa.get("Startplats", "?")
        st.sidebar.text(f"{d}: {s}")

if st.sidebar.button("Synkronisera från fil"):
    st.session_state.journey_log = ladda_data()
    st.rerun()

# --- 3. LÄGG TILL MANUELL RESA (Originalformulär) ---
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
    
    if st.form_submit_button("Lägg till"):
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
        spara_och_synka(st.session_state.journey_log, "Ny resa")
        st.rerun()

# --- 4. FLERA RESOR (Återställt) ---
with st.expander("📅 Lägg till flera resor (Kalender)"):
    datum_lista = st.multiselect("Välj datum", options=[d.date() for d in pd.date_range(date(2024, 1, 1), date.today())])
    st_m = st.time_input("Starttid", key="m_start")
    sl_m = st.time_input("Sluttid", key="m_slut")
    sp_m = st.text_input("Startplats", key="m_startp")
    ep_m = st.text_input("Slutplats", key="m_slutp")
    km_m = st.number_input("Sträcka (km)", key="m_km")
    sy_m = st.text_input("Syfte", key="m_syfte")
    
    if st.button("Lägg till batch"):
        batch_resor = []
        for d in datum_lista:
            t1 = datetime.combine(d, st_m)
            t2 = datetime.combine(d, sl_m)
            restid = (t2 - t1).seconds / 60
            batch_resor.append({
                "Datum": d, "Startid": st_m.strftime("%H:%M"), "Sluttid": sl_m.strftime("%H:%M"),
                "Restid (min)": int(restid), "Startplats": sp_m, "Slutplats": ep_m,
                "Sträcka (km)": km_m, "Syfte": sy_m
            })
        st.session_state.journey_log.extend(batch_resor)
        spara_och_synka(st.session_state.journey_log, "Batch-resor")
        st.rerun()

# --- 5. STATISTIK & FILTER (Återställt) ---
st.markdown("---")
st.subheader("📊 Dina resor")

if st.session_state.journey_log:
    df = pd.DataFrame(st.session_state.journey_log)
    if "Datum" in df.columns:
        df["Datum"] = pd.to_datetime(df["Datum"]).dt.date

    # Filter
    with st.sidebar:
        st.header("Filter")
        if not df.empty:
            min_d, max_d = df["Datum"].min(), df["Datum"].max()
            dr = st.date_input("Intervall", (min_d, max_d))
            # Hantera om användaren bara väljer ett datum
            if isinstance(dr, tuple) and len(dr) == 2:
                mask = (df["Datum"] >= dr[0]) & (df["Datum"] <= dr[1])
                df_filtered = df[mask]
            else:
                df_filtered = df
        else:
            df_filtered = df

    # Visa tabell
    st.dataframe(df_filtered)

    # Ladda ner knapp
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df_filtered.to_excel(writer, index=False)
        
    st.download_button(
        label="💾 Ladda ner Excel",
        data=buffer.getvalue(),
        file_name="korjournal.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # --- STATISTIK (Grafer & Siffror) ---
    st.subheader("📈 Statistik")
    if not df_filtered.empty:
        c1, c2, c3 = st.columns(3)
        tot_km = df_filtered["Sträcka (km)"].sum()
        count = len(df_filtered)
        
        c1.metric("Total sträcka", f"{tot_km:.1f} km")
        c2.metric("Antal resor", count)
        c3.metric("Snitt per resa", f"{(tot_km/count):.1f} km" if count > 0 else "0")

        # Månadsstatistik (Bar chart)
        try:
            df_chart = df_filtered.copy()
            df_chart["Månad"] = pd.to_datetime(df_chart["Datum"]).dt.strftime("%Y-%m")
            monthly = df_chart.groupby("Månad")["Sträcka (km)"].sum()
            
            st.write("Kilometer per månad:")
            st.bar_chart(monthly)
        except Exception as e:
            st.warning(f"Kunde inte rita graf: {e}")

# --- 6. REDIGERA / TA BORT (Originalfunktionen) ---
st.markdown("---")
st.subheader("🗑️ Hantera resor (Redigera/Ta bort)")

if st.session_state.journey_log:
    # Skapa lista för Selectbox
    opts = []
    for i, r in enumerate(st.session_state.journey_log):
        opts.append(f"{i}: {r['Datum']} | {r.get('Startplats','?')} -> {r.get('Slutplats','?')}")
    
    sel_idx = st.selectbox("Välj resa att ändra", range(len(opts)), format_func=lambda x: opts[x])
    
    if sel_idx is not None:
        sel_resa = st.session_state.journey_log[sel_idx]
        
        with st.form("edit_form"):
            st.write(f"Redigerar resa nr {sel_idx}")
            
            # Helper för tider
            def to_time(val):
                if isinstance(val, str): return datetime.strptime(val, "%H:%M").time()
                return val

            e_dat = st.date_input("Datum", sel_resa["Datum"])
            e_start = st.time_input("Start", to_time(sel_resa["Startid"]))
            e_slut = st.time_input("Slut", to_time(sel_resa["Sluttid"]))
            e_sp = st.text_input("Startplats", sel_resa["Startplats"])
            e_ep = st.text_input("Slutplats", sel_resa["Slutplats"])
            e_km = st.number_input("Km", value=float(sel_resa["Sträcka (km)"]))
            e_sy = st.text_input("Syfte", sel_resa["Syfte"])
            
            c_save, c_del = st.columns(2)
            
            if c_save.form_submit_button("💾 Spara ändring"):
                # Uppdatera objektet
                t1 = datetime.combine(e_dat, e_start)
                t2 = datetime.combine(e_dat, e_slut)
                diff = (t2 - t1).seconds / 60
                
                updated = {
                    "Datum": e_dat,
                    "Startid": e_start.strftime("%H:%M"),
                    "Sluttid": e_slut.strftime("%H:%M"),
                    "Restid (min)": int(diff),
                    "Startplats": e_sp, "Slutplats": e_ep,
                    "Sträcka (km)": e_km, "Syfte": e_sy
                }
                
                st.session_state.journey_log[sel_idx] = updated
                spara_och_synka(st.session_state.journey_log, "Redigerad resa")
                st.rerun()
                
            if c_del.form_submit_button("🗑️ Ta bort resa"):
                del st.session_state.journey_log[sel_idx]
                spara_och_synka(st.session_state.journey_log, "Borttagen resa")
                st.rerun()
else:
    st.info("Inga resor registrerade än.")

# --- 7. LADDA UPP EXCEL (För import) ---
with st.expander("📤 Importera gammal Excel-fil"):
    up_file = st.file_uploader("Välj fil", type="xlsx")
    if up_file and st.button("Importera"):
        try:
            new_data = pd.read_excel(up_file, engine="openpyxl").to_dict(orient="records")
            # Enkel tvätt av datum
            for x in new_data:
                if isinstance(x.get("Datum"), pd.Timestamp):
                    x["Datum"] = x["Datum"].date()
            
            st.session_state.journey_log.extend(new_data)
            spara_och_synka(st.session_state.journey_log, "Import")
            st.rerun()
        except Exception as e:
            st.error(f"Fel: {e}")
