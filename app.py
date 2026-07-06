import hashlib
import hmac
import secrets
import uuid
from datetime import date, datetime, timezone
from io import BytesIO

import altair as alt
import matplotlib
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from supabase import create_client


matplotlib.use("Agg")


# ------------------------------------------------------------
# Configuration
# ------------------------------------------------------------

st.set_page_config(
    page_title="Norcycle - Temps bénévole",
    layout="wide",
)

USERS_TABLE = "app_users"
VOLUNTEERS_TABLE = "volunteers"
TASKS_TABLE = "tasks"
HOURS_TABLE = "volunteer_hours"

ROLES = {
    "admin": "Administrateur",
    "user": "Usager",
}

SEASONS = ["Hiver", "Printemps", "Été", "Automne"]


# ------------------------------------------------------------
# Style
# ------------------------------------------------------------

st.markdown(
    """
    <style>
        .block-container {
            padding-top: 1.1rem;
            padding-bottom: 2rem;
            max-width: 96%;
        }

        h1 {
            font-size: 2.2rem !important;
            margin-bottom: 0.2rem !important;
        }

        .subtitle {
            color: #9ca3af;
            font-size: 0.95rem;
            margin-bottom: 1.1rem;
        }

        .soft-card {
            background: rgba(255, 255, 255, 0.035);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 16px;
            padding: 1rem;
            margin-bottom: 1rem;
        }

        .small-muted {
            color: #9ca3af;
            font-size: 0.82rem;
        }

        div.stButton > button,
        div.stDownloadButton > button,
        div[data-testid="stFormSubmitButton"] button {
            border-radius: 12px;
            min-height: 2.75rem;
            font-weight: 700;
        }

        div[data-testid="stMetric"] {
            background: rgba(255,255,255,0.035);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 14px;
            padding: 0.65rem;
        }

        section[data-testid="stSidebar"] {
            min-width: 340px !important;
        }

        @media screen and (max-width: 768px) {
            .block-container {
                padding-left: 0.55rem;
                padding-right: 0.55rem;
                max-width: 100%;
            }

            h1 {
                font-size: 1.6rem !important;
            }

            .subtitle {
                font-size: 0.82rem;
            }

            div.stButton > button,
            div.stDownloadButton > button,
            div[data-testid="stFormSubmitButton"] button {
                min-height: 3rem;
                font-size: 0.95rem;
            }

            section[data-testid="stSidebar"] {
                min-width: 300px !important;
            }
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# ------------------------------------------------------------
# Supabase
# ------------------------------------------------------------

@st.cache_resource
def get_supabase_client():
    url = st.secrets.get("SUPABASE_URL")
    key = st.secrets.get("SUPABASE_SERVICE_ROLE_KEY")

    if not url or not key:
        st.error(
            "Configuration Supabase manquante. "
            "Ajoute SUPABASE_URL et SUPABASE_SERVICE_ROLE_KEY dans les secrets Streamlit."
        )
        st.stop()

    url = str(url).strip().rstrip("/")
    key = str(key).strip()

    for suffix in ["/rest/v1", "/auth/v1", "/storage/v1", "/functions/v1"]:
        if url.endswith(suffix):
            url = url[: -len(suffix)]

    if "supabase.com/dashboard" in url:
        st.error(
            "SUPABASE_URL est une URL du dashboard. "
            "Utilise plutôt l'URL du projet : https://xxxx.supabase.co"
        )
        st.stop()

    if not url.startswith("https://") or ".supabase.co" not in url:
        st.error("SUPABASE_URL doit ressembler à https://xxxxxxxxxxxx.supabase.co")
        st.stop()

    return create_client(url, key)


def load_table(table_name, order_by=None, desc=False):
    supabase = get_supabase_client()

    query = supabase.table(table_name).select("*")

    if order_by:
        query = query.order(order_by, desc=desc)

    response = query.execute()
    return response.data or []


def insert_row(table_name, payload):
    supabase = get_supabase_client()
    supabase.table(table_name).insert(payload).execute()


def update_row(table_name, row_id, payload):
    supabase = get_supabase_client()
    payload["updated_at"] = datetime.now(timezone.utc).isoformat()

    (
        supabase
        .table(table_name)
        .update(payload)
        .eq("id", row_id)
        .execute()
    )


def delete_row(table_name, row_id):
    supabase = get_supabase_client()

    (
        supabase
        .table(table_name)
        .delete()
        .eq("id", row_id)
        .execute()
    )



def run_healthcheck_if_requested():
    """
    Healthcheck léger pour garder Streamlit Community Cloud et Supabase actifs.

    Appel recommandé :
    https://ton-app.streamlit.app/?health=1

    Ce mode :
    - initialise le client Supabase;
    - fait une petite requête sur les tables principales;
    - retourne OK;
    - arrête l'exécution avant la connexion, les statistiques et le PDF.
    """

    try:
        health_value = st.query_params.get("health", None)
    except Exception:
        health_value = None

    if isinstance(health_value, list):
        health_value = health_value[0] if health_value else None

    if str(health_value) != "1":
        return

    checked_at = datetime.now(timezone.utc).isoformat()

    try:
        supabase = get_supabase_client()

        checks = {}

        for table_name in [
            USERS_TABLE,
            VOLUNTEERS_TABLE,
            TASKS_TABLE,
            HOURS_TABLE,
        ]:
            response = (
                supabase
                .table(table_name)
                .select("id")
                .limit(1)
                .execute()
            )

            checks[table_name] = len(response.data or [])

        st.write("OK")
        st.caption(f"Healthcheck réussi à {checked_at}")

        for table_name, row_count in checks.items():
            st.caption(f"{table_name} ping : {row_count}")

    except Exception as exc:
        st.error("Healthcheck échoué.")
        st.exception(exc)

    st.stop()


# ------------------------------------------------------------
# Sécurité comptes
# ------------------------------------------------------------

def hash_password(password, salt_hex=None, iterations=260000):
    if not password:
        raise ValueError("Mot de passe vide.")

    if salt_hex is None:
        salt = secrets.token_bytes(16)
    else:
        salt = bytes.fromhex(salt_hex)

    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        iterations,
    )

    return f"pbkdf2_sha256${iterations}${salt.hex()}${password_hash.hex()}"


def verify_password(password, stored_hash):
    try:
        algorithm, iterations, salt_hex, expected_hash = stored_hash.split("$")
    except ValueError:
        return False

    if algorithm != "pbkdf2_sha256":
        return False

    candidate_hash = hash_password(
        password=password,
        salt_hex=salt_hex,
        iterations=int(iterations),
    )

    return hmac.compare_digest(candidate_hash, stored_hash)


def get_setup_key():
    return st.secrets.get("ADMIN_SETUP_KEY")


def count_users():
    return len(load_table(USERS_TABLE))


def create_user(username, display_name, password, role="user", active=True):
    username = username.strip().lower()
    display_name = display_name.strip()

    if not username:
        raise ValueError("Le nom d'utilisateur est obligatoire.")

    if not display_name:
        raise ValueError("Le nom affiché est obligatoire.")

    if role not in ROLES:
        raise ValueError("Rôle invalide.")

    payload = {
        "id": str(uuid.uuid4()),
        "username": username,
        "display_name": display_name,
        "password_hash": hash_password(password),
        "role": role,
        "active": active,
    }

    insert_row(USERS_TABLE, payload)


def authenticate(username, password):
    username = username.strip().lower()

    users = load_table(USERS_TABLE)

    for user in users:
        if user["username"] == username:
            if not user.get("active", True):
                return None

            if verify_password(password, user["password_hash"]):
                return {
                    "id": user["id"],
                    "username": user["username"],
                    "display_name": user["display_name"],
                    "role": user["role"],
                }

    return None


def current_user():
    return st.session_state.get("user")


def is_logged_in():
    return current_user() is not None


def is_admin():
    user = current_user()
    return bool(user and user.get("role") == "admin")


def logout():
    st.session_state.pop("user", None)
    st.rerun()


# ------------------------------------------------------------
# Listes et saisies
# ------------------------------------------------------------

def clean_text(value):
    if value is None:
        return ""

    try:
        if pd.isna(value):
            return ""
    except TypeError:
        pass

    return str(value).strip()


def load_volunteers(active_only=True):
    volunteers = load_table(VOLUNTEERS_TABLE, order_by="name")

    if active_only:
        volunteers = [v for v in volunteers if v.get("active", True)]

    return volunteers


def load_tasks(active_only=True):
    tasks = load_table(TASKS_TABLE, order_by="name")

    if active_only:
        tasks = [t for t in tasks if t.get("active", True)]

    return tasks


def maybe_add_volunteer(name):
    name = clean_text(name)

    if not name:
        return

    volunteers = load_table(VOLUNTEERS_TABLE)

    existing = [
        v for v in volunteers
        if clean_text(v.get("name")).lower() == name.lower()
    ]

    if existing:
        if not existing[0].get("active", True):
            update_row(VOLUNTEERS_TABLE, existing[0]["id"], {"active": True})
        return

    insert_row(
        VOLUNTEERS_TABLE,
        {
            "id": str(uuid.uuid4()),
            "name": name,
            "active": True,
        },
    )


def maybe_add_task(name):
    name = clean_text(name)

    if not name:
        return

    tasks = load_table(TASKS_TABLE)

    existing = [
        t for t in tasks
        if clean_text(t.get("name")).lower() == name.lower()
    ]

    if existing:
        if not existing[0].get("active", True):
            update_row(TASKS_TABLE, existing[0]["id"], {"active": True})
        return

    insert_row(
        TASKS_TABLE,
        {
            "id": str(uuid.uuid4()),
            "name": name,
            "active": True,
        },
    )


def add_time_entry(volunteer_name, task_name, hours, work_date, note, created_by):
    maybe_add_volunteer(volunteer_name)
    maybe_add_task(task_name)

    payload = {
        "id": str(uuid.uuid4()),
        "volunteer_name": volunteer_name.strip(),
        "task_name": task_name.strip(),
        "hours": float(hours),
        "work_date": work_date.isoformat(),
        "note": clean_text(note),
        "created_by": created_by,
    }

    insert_row(HOURS_TABLE, payload)


def load_entries():
    return load_table(HOURS_TABLE, order_by="work_date", desc=True)


def get_default_index(options, preferred_value):
    if preferred_value in options:
        return options.index(preferred_value)

    return 0


# ------------------------------------------------------------
# Dates, saisons, statistiques
# ------------------------------------------------------------

def get_season_from_date(dt):
    month = dt.month

    if month in [12, 1, 2]:
        return "Hiver"

    if month in [3, 4, 5]:
        return "Printemps"

    if month in [6, 7, 8]:
        return "Été"

    return "Automne"


def get_season_year(dt):
    if dt.month == 12:
        return dt.year + 1

    return dt.year


def make_entries_df(entries):
    df = pd.DataFrame(entries)

    if df.empty:
        return pd.DataFrame(
            columns=[
                "id",
                "volunteer_name",
                "task_name",
                "hours",
                "work_date",
                "note",
                "created_by",
                "created_at",
                "year",
                "season",
                "season_year",
            ]
        )

    df["work_date"] = pd.to_datetime(df["work_date"], errors="coerce")
    df["hours"] = pd.to_numeric(df["hours"], errors="coerce").fillna(0.0)
    df["year"] = df["work_date"].dt.year
    df["season"] = df["work_date"].apply(get_season_from_date)
    df["season_year"] = df["work_date"].apply(get_season_year)

    return df


def filter_stats_df(df, selected_years, selected_seasons):
    filtered = df.copy()

    if selected_years:
        filtered = filtered[filtered["year"].isin(selected_years)]

    if selected_seasons:
        filtered = filtered[filtered["season"].isin(selected_seasons)]

    return filtered


def make_pareto_df(df, dimension, top_n=20):
    if df.empty:
        return pd.DataFrame(columns=[dimension, "hours", "cum_hours", "cum_pct"])

    grouped = (
        df.groupby(dimension, dropna=False)["hours"]
        .sum()
        .reset_index()
        .sort_values("hours", ascending=False)
        .head(top_n)
    )

    grouped[dimension] = grouped[dimension].astype(str)
    grouped["cum_hours"] = grouped["hours"].cumsum()

    total = grouped["hours"].sum()

    if total > 0:
        grouped["cum_pct"] = grouped["cum_hours"] / total
    else:
        grouped["cum_pct"] = 0

    return grouped


def render_pareto(df, dimension, title, dimension_label):
    pareto = make_pareto_df(df, dimension)

    if pareto.empty:
        st.info("Aucune donnée pour ce graphique.")
        return

    bars = (
        alt.Chart(pareto)
        .mark_bar()
        .encode(
            x=alt.X(
                f"{dimension}:N",
                sort="-y",
                title=dimension_label,
                axis=alt.Axis(labelAngle=-35),
            ),
            y=alt.Y("hours:Q", title="Heures"),
            tooltip=[
                alt.Tooltip(f"{dimension}:N", title=dimension_label),
                alt.Tooltip("hours:Q", title="Heures", format=".2f"),
                alt.Tooltip("cum_pct:Q", title="Cumul %", format=".1%"),
            ],
        )
    )

    line = (
        alt.Chart(pareto)
        .mark_line(point=True)
        .encode(
            x=alt.X(f"{dimension}:N", sort="-y"),
            y=alt.Y(
                "cum_pct:Q",
                title="Cumul %",
                axis=alt.Axis(format="%"),
                scale=alt.Scale(domain=[0, 1]),
            ),
            tooltip=[
                alt.Tooltip(f"{dimension}:N", title=dimension_label),
                alt.Tooltip("cum_pct:Q", title="Cumul %", format=".1%"),
            ],
        )
    )

    chart = (
        alt.layer(bars, line)
        .resolve_scale(y="independent")
        .properties(height=390, title=title)
    )

    st.altair_chart(chart, use_container_width=True)


def render_year_season_chart(df):
    if df.empty:
        st.info("Aucune donnée pour le graphique annuel.")
        return

    chart_df = (
        df.groupby(["year", "season"])["hours"]
        .sum()
        .reset_index()
    )

    chart = (
        alt.Chart(chart_df)
        .mark_bar()
        .encode(
            x=alt.X("year:O", title="Année"),
            y=alt.Y("hours:Q", title="Heures"),
            color=alt.Color("season:N", title="Saison"),
            tooltip=[
                alt.Tooltip("year:O", title="Année"),
                alt.Tooltip("season:N", title="Saison"),
                alt.Tooltip("hours:Q", title="Heures", format=".2f"),
            ],
        )
        .properties(height=360, title="Heures par année et saison")
    )

    st.altair_chart(chart, use_container_width=True)


# ------------------------------------------------------------
# Rapport PDF
# ------------------------------------------------------------

def make_matplotlib_bar_chart(df, x_col, y_col, title, x_label, y_label):
    if df.empty:
        return None

    fig, ax = plt.subplots(figsize=(10, 5.2))

    ax.bar(df[x_col].astype(str), df[y_col])
    ax.set_title(title)
    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    ax.tick_params(axis="x", rotation=35)
    ax.grid(axis="y", alpha=0.25)

    fig.tight_layout()

    output = BytesIO()
    fig.savefig(output, format="png", dpi=170, bbox_inches="tight")
    plt.close(fig)

    output.seek(0)
    return output


def make_matplotlib_pareto_chart(df, dimension, title):
    pareto = make_pareto_df(df, dimension, top_n=15)

    if pareto.empty:
        return None

    fig, ax1 = plt.subplots(figsize=(10, 5.2))

    labels = pareto[dimension].astype(str)
    x = range(len(labels))

    ax1.bar(x, pareto["hours"])
    ax1.set_ylabel("Heures")
    ax1.set_xticks(list(x))
    ax1.set_xticklabels(labels, rotation=35, ha="right")
    ax1.grid(axis="y", alpha=0.25)

    ax2 = ax1.twinx()
    ax2.plot(x, pareto["cum_pct"] * 100, marker="o")
    ax2.set_ylabel("Cumul %")
    ax2.set_ylim(0, 105)

    ax1.set_title(title)

    fig.tight_layout()

    output = BytesIO()
    fig.savefig(output, format="png", dpi=170, bbox_inches="tight")
    plt.close(fig)

    output.seek(0)
    return output


def make_year_season_chart_image(df):
    if df.empty:
        return None

    chart_df = (
        df.groupby(["year", "season"])["hours"]
        .sum()
        .reset_index()
    )

    if chart_df.empty:
        return None

    pivot = (
        chart_df.pivot_table(
            index="year",
            columns="season",
            values="hours",
            aggfunc="sum",
            fill_value=0,
        )
        .reindex(columns=SEASONS, fill_value=0)
        .sort_index()
    )

    fig, ax = plt.subplots(figsize=(10, 5.2))

    pivot.plot(kind="bar", stacked=True, ax=ax)

    ax.set_title("Heures par année et saison")
    ax.set_xlabel("Année")
    ax.set_ylabel("Heures")
    ax.tick_params(axis="x", rotation=0)
    ax.grid(axis="y", alpha=0.25)
    ax.legend(title="Saison", loc="upper left", bbox_to_anchor=(1.0, 1.0))

    fig.tight_layout()

    output = BytesIO()
    fig.savefig(output, format="png", dpi=170, bbox_inches="tight")
    plt.close(fig)

    output.seek(0)
    return output


def make_monthly_chart_image(df):
    if df.empty:
        return None

    monthly = df.copy()
    monthly["month"] = monthly["work_date"].dt.to_period("M").astype(str)

    monthly_summary = (
        monthly.groupby("month")["hours"]
        .sum()
        .reset_index()
        .sort_values("month")
    )

    if monthly_summary.empty:
        return None

    return make_matplotlib_bar_chart(
        monthly_summary,
        x_col="month",
        y_col="hours",
        title="Heures par mois",
        x_label="Mois",
        y_label="Heures",
    )


def add_pdf_footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.drawRightString(
        letter[0] - 0.6 * inch,
        0.4 * inch,
        f"Page {doc.page}",
    )
    canvas.restoreState()


def add_image_to_story(story, image_buffer, max_width=7.2 * inch):
    if image_buffer is None:
        return

    img = Image(image_buffer)

    scale = max_width / img.drawWidth
    img.drawWidth = img.drawWidth * scale
    img.drawHeight = img.drawHeight * scale

    story.append(img)
    story.append(Spacer(1, 0.25 * inch))


def make_summary_table(filtered_df):
    if filtered_df.empty:
        total_hours = 0
        total_entries = 0
        volunteer_count = 0
        task_count = 0
    else:
        total_hours = filtered_df["hours"].sum()
        total_entries = len(filtered_df)
        volunteer_count = filtered_df["volunteer_name"].nunique()
        task_count = filtered_df["task_name"].nunique()

    data = [
        ["Indicateur", "Valeur"],
        ["Heures totales", f"{total_hours:.2f}"],
        ["Nombre de saisies", str(total_entries)],
        ["Bénévoles distincts", str(volunteer_count)],
        ["Tâches distinctes", str(task_count)],
    ]

    table = Table(data, colWidths=[3.2 * inch, 2.0 * inch])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )

    return table


def make_top_table(df, dimension, title, limit=10):
    if df.empty:
        return None

    summary = (
        df.groupby(dimension)["hours"]
        .sum()
        .reset_index()
        .sort_values("hours", ascending=False)
        .head(limit)
    )

    if summary.empty:
        return None

    data = [[title, "Heures"]]

    for _, row in summary.iterrows():
        data.append([str(row[dimension]), f"{row['hours']:.2f}"])

    table = Table(data, colWidths=[4.2 * inch, 1.2 * inch])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )

    return table


def generate_stats_pdf_report(filtered_df, selected_years, selected_seasons):
    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.55 * inch,
        leftMargin=0.55 * inch,
        topMargin=0.6 * inch,
        bottomMargin=0.6 * inch,
        title="Norcycle - Rapport des heures bénévoles",
    )

    styles = getSampleStyleSheet()

    title_style = styles["Title"]

    heading_style = ParagraphStyle(
        "ReportHeading",
        parent=styles["Heading2"],
        fontSize=14,
        leading=17,
        spaceBefore=12,
        spaceAfter=8,
    )

    normal_style = ParagraphStyle(
        "ReportNormal",
        parent=styles["Normal"],
        fontSize=9,
        leading=12,
        spaceAfter=6,
    )

    story = []

    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")

    years_text = ", ".join(str(y) for y in selected_years) if selected_years else "Toutes"
    seasons_text = ", ".join(selected_seasons) if selected_seasons else "Toutes"

    story.append(Paragraph("Norcycle - Rapport des heures bénévoles", title_style))
    story.append(
        Paragraph(
            f"Rapport généré le {generated_at}",
            normal_style,
        )
    )
    story.append(
        Paragraph(
            f"Filtres appliqués - Années : {years_text} | Saisons : {seasons_text}",
            normal_style,
        )
    )
    story.append(Spacer(1, 0.15 * inch))

    story.append(Paragraph("Résumé", heading_style))
    story.append(make_summary_table(filtered_df))
    story.append(Spacer(1, 0.25 * inch))

    top_volunteers_table = make_top_table(
        filtered_df,
        dimension="volunteer_name",
        title="Top bénévoles",
    )

    top_tasks_table = make_top_table(
        filtered_df,
        dimension="task_name",
        title="Top tâches",
    )

    if top_volunteers_table or top_tasks_table:
        story.append(Paragraph("Top 10", heading_style))

        if top_volunteers_table:
            story.append(top_volunteers_table)
            story.append(Spacer(1, 0.18 * inch))

        if top_tasks_table:
            story.append(top_tasks_table)
            story.append(Spacer(1, 0.18 * inch))

    story.append(PageBreak())

    story.append(Paragraph("Pareto des heures par bénévole", heading_style))
    volunteer_chart = make_matplotlib_pareto_chart(
        filtered_df,
        dimension="volunteer_name",
        title="Pareto des heures par bénévole",
    )
    add_image_to_story(story, volunteer_chart)

    story.append(Paragraph("Pareto des heures par tâche", heading_style))
    task_chart = make_matplotlib_pareto_chart(
        filtered_df,
        dimension="task_name",
        title="Pareto des heures par tâche",
    )
    add_image_to_story(story, task_chart)

    story.append(PageBreak())

    story.append(Paragraph("Évolution temporelle", heading_style))

    year_season_chart = make_year_season_chart_image(filtered_df)
    add_image_to_story(story, year_season_chart)

    monthly_chart = make_monthly_chart_image(filtered_df)
    add_image_to_story(story, monthly_chart)

    if filtered_df.empty:
        story.append(
            Paragraph(
                "Aucune donnée disponible pour les filtres sélectionnés.",
                normal_style,
            )
        )

    doc.build(
        story,
        onFirstPage=add_pdf_footer,
        onLaterPages=add_pdf_footer,
    )

    buffer.seek(0)
    return buffer.getvalue()


# ------------------------------------------------------------
# Excel export / import
# ------------------------------------------------------------

def export_to_excel(entries_df, volunteers, tasks, users):
    output = BytesIO()

    clean_users = pd.DataFrame(users)

    if not clean_users.empty and "password_hash" in clean_users.columns:
        clean_users = clean_users.drop(columns=["password_hash"])

    export_entries = entries_df.copy()

    if not export_entries.empty:
        export_entries["work_date"] = export_entries["work_date"].dt.date

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        export_entries.to_excel(writer, sheet_name="Temps benevole", index=False)
        pd.DataFrame(volunteers).to_excel(writer, sheet_name="Benevoles", index=False)
        pd.DataFrame(tasks).to_excel(writer, sheet_name="Taches", index=False)
        clean_users.to_excel(writer, sheet_name="Usagers", index=False)

    output.seek(0)
    return output.getvalue()


def parse_excel_date(value):
    if value is None:
        return None

    try:
        if pd.isna(value):
            return None
    except TypeError:
        pass

    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    if isinstance(value, (int, float)):
        return pd.to_datetime(
            value,
            unit="D",
            origin="1899-12-30",
            errors="coerce",
        ).date()

    parsed = pd.to_datetime(value, errors="coerce")

    if pd.isna(parsed):
        return None

    return parsed.date()


def read_old_excel(uploaded_file):
    excel = pd.ExcelFile(uploaded_file)
    sheet_name = "Inscription" if "Inscription" in excel.sheet_names else excel.sheet_names[0]

    raw = pd.read_excel(uploaded_file, sheet_name=sheet_name, header=None)

    header_index = None

    for idx, row in raw.iterrows():
        values = [clean_text(v).lower() for v in row.tolist()]
        has_name = any("nom" in v for v in values)
        has_hours = any("heure" in v for v in values)

        if has_name and has_hours:
            header_index = idx
            break

    if header_index is None:
        raise ValueError("Impossible de trouver la ligne d'en-tête dans le fichier Excel.")

    headers = [clean_text(v) for v in raw.iloc[header_index].tolist()]
    df = raw.iloc[header_index + 1:].copy()
    df.columns = headers

    column_map = {}

    for col in df.columns:
        low = clean_text(col).lower()

        if "nom" in low:
            column_map["volunteer_name"] = col
        elif "activ" in low or "tâche" in low or "tache" in low:
            column_map["task_name"] = col
        elif "heure" in low:
            column_map["hours"] = col
        elif "date" in low:
            column_map["work_date"] = col

    missing = [
        key for key in ["volunteer_name", "task_name", "hours", "work_date"]
        if key not in column_map
    ]

    if missing:
        raise ValueError(
            "Colonnes manquantes dans l'import : "
            + ", ".join(missing)
        )

    rows = []

    for _, row in df.iterrows():
        volunteer_name = clean_text(row.get(column_map["volunteer_name"]))
        task_name = clean_text(row.get(column_map["task_name"]))
        hours = pd.to_numeric(row.get(column_map["hours"]), errors="coerce")
        work_date = parse_excel_date(row.get(column_map["work_date"]))

        if not volunteer_name or not task_name or pd.isna(hours) or not work_date:
            continue

        if float(hours) <= 0:
            continue

        rows.append(
            {
                "volunteer_name": volunteer_name,
                "task_name": task_name,
                "hours": float(hours),
                "work_date": work_date,
                "note": "",
            }
        )

    return pd.DataFrame(rows)


# ------------------------------------------------------------
# Premier admin / connexion
# ------------------------------------------------------------

def render_first_admin_setup():
    st.markdown("# Norcycle - Temps bénévole")
    st.markdown(
        """
        <div class="subtitle">
            Première configuration administrateur
        </div>
        """,
        unsafe_allow_html=True,
    )

    setup_key = get_setup_key()

    if not setup_key:
        st.error(
            "ADMIN_SETUP_KEY est manquant dans les secrets Streamlit. "
            "Ajoute-le avant de créer le premier administrateur."
        )
        st.stop()

    with st.form("first_admin_form"):
        entered_key = st.text_input("Code de configuration", type="password")
        display_name = st.text_input("Nom affiché", placeholder="Ex: Sébastien Bujold")
        username = st.text_input("Nom d'utilisateur", placeholder="Ex: sebastien")
        password = st.text_input("Mot de passe admin", type="password")
        password_confirm = st.text_input("Confirmer le mot de passe", type="password")

        submitted = st.form_submit_button(
            "Créer le premier administrateur",
            use_container_width=True,
        )

        if submitted:
            if entered_key != setup_key:
                st.error("Code de configuration invalide.")
            elif password != password_confirm:
                st.error("Les mots de passe ne correspondent pas.")
            elif len(password) < 8:
                st.error("Le mot de passe doit contenir au moins 8 caractères.")
            else:
                try:
                    create_user(
                        username=username,
                        display_name=display_name,
                        password=password,
                        role="admin",
                        active=True,
                    )
                    maybe_add_volunteer(display_name)
                    st.success("Administrateur créé. Connecte-toi maintenant.")
                    st.rerun()
                except Exception as exc:
                    st.error("Impossible de créer l'administrateur.")
                    st.exception(exc)


def render_login():
    st.markdown("# Norcycle - Temps bénévole")
    st.markdown(
        """
        <div class="subtitle">
            Connexion requise pour saisir ou consulter les heures bénévoles
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_login, col_info = st.columns([1, 1])

    with col_login:
        with st.form("login_form"):
            username = st.text_input("Nom d'utilisateur")
            password = st.text_input("Mot de passe", type="password")

            submitted = st.form_submit_button("Se connecter", use_container_width=True)

            if submitted:
                user = authenticate(username, password)

                if user:
                    st.session_state["user"] = user
                    st.rerun()
                else:
                    st.error("Connexion invalide.")

    with col_info:
        st.markdown(
            """
            <div class="soft-card">
                <b>Saisie rapide</b><br><br>
                Chaque usager peut saisir une entrée avec :
                <ul>
                    <li>le nom du bénévole;</li>
                    <li>la date;</li>
                    <li>le nombre d'heures;</li>
                    <li>la tâche effectuée.</li>
                </ul>
            </div>
            """,
            unsafe_allow_html=True,
        )


# ------------------------------------------------------------
# Pages
# ------------------------------------------------------------

def render_entry_page(entries_df):
    st.header("Saisie rapide")

    volunteers = load_volunteers(active_only=True)
    tasks = load_tasks(active_only=True)

    volunteer_names = [v["name"] for v in volunteers]
    task_names = [t["name"] for t in tasks]

    user = current_user()
    preferred_name = user["display_name"]

    volunteer_options = volunteer_names + ["➕ Nouveau bénévole"]
    task_options = task_names + ["➕ Nouvelle tâche"]

    if not volunteer_names:
        volunteer_options = ["➕ Nouveau bénévole"]

    if not task_names:
        task_options = ["➕ Nouvelle tâche"]

    with st.form("time_entry_form"):
        col1, col2 = st.columns(2)

        with col1:
            selected_volunteer = st.selectbox(
                "Nom de la personne",
                options=volunteer_options,
                index=get_default_index(volunteer_options, preferred_name),
            )

            if selected_volunteer == "➕ Nouveau bénévole":
                volunteer_name = st.text_input("Nouveau bénévole")
            else:
                volunteer_name = selected_volunteer

        with col2:
            work_date = st.date_input("Date", value=date.today())

        col3, col4 = st.columns(2)

        with col3:
            hours = st.number_input(
                "Temps bénévole",
                min_value=0.25,
                max_value=24.0,
                value=1.0,
                step=0.25,
                format="%.2f",
            )

        with col4:
            selected_task = st.selectbox(
                "Tâche",
                options=task_options,
            )

            if selected_task == "➕ Nouvelle tâche":
                task_name = st.text_input("Nouvelle tâche")
            else:
                task_name = selected_task

        note = st.text_area("Note optionnelle", placeholder="Détails, lieu, commentaire...")

        submitted = st.form_submit_button("Enregistrer le temps", use_container_width=True)

        if submitted:
            volunteer_name = clean_text(volunteer_name)
            task_name = clean_text(task_name)

            if not volunteer_name:
                st.error("Le nom de la personne est obligatoire.")
            elif not task_name:
                st.error("La tâche est obligatoire.")
            else:
                try:
                    add_time_entry(
                        volunteer_name=volunteer_name,
                        task_name=task_name,
                        hours=hours,
                        work_date=work_date,
                        note=note,
                        created_by=user["username"],
                    )
                    st.success("Temps bénévole enregistré.")
                    st.rerun()
                except Exception as exc:
                    st.error("Impossible d'enregistrer l'entrée.")
                    st.exception(exc)

    st.divider()

    st.subheader("Dernières saisies")

    if entries_df.empty:
        st.info("Aucune saisie pour l'instant.")
    else:
        latest = entries_df.sort_values("work_date", ascending=False).head(20).copy()
        latest["work_date"] = latest["work_date"].dt.date

        st.dataframe(
            latest[
                [
                    "work_date",
                    "volunteer_name",
                    "task_name",
                    "hours",
                    "note",
                    "created_by",
                ]
            ],
            use_container_width=True,
            hide_index=True,
        )


def render_stats_page(entries_df):
    st.header("Statistiques")

    if entries_df.empty:
        st.info("Aucune donnée à analyser pour l'instant.")
        return

    years = sorted([int(y) for y in entries_df["year"].dropna().unique()])
    seasons = SEASONS

    with st.expander("Filtres statistiques", expanded=True):
        col1, col2 = st.columns(2)

        with col1:
            selected_years = st.multiselect(
                "Années",
                options=years,
                default=years,
            )

        with col2:
            selected_seasons = st.multiselect(
                "Saisons",
                options=seasons,
                default=seasons,
            )

    filtered = filter_stats_df(entries_df, selected_years, selected_seasons)

    total_hours = filtered["hours"].sum()
    total_entries = len(filtered)
    volunteer_count = filtered["volunteer_name"].nunique()
    task_count = filtered["task_name"].nunique()

    kpi1, kpi2, kpi3, kpi4 = st.columns(4)

    with kpi1:
        st.metric("Heures totales", f"{total_hours:.2f}")

    with kpi2:
        st.metric("Saisies", total_entries)

    with kpi3:
        st.metric("Bénévoles", volunteer_count)

    with kpi4:
        st.metric("Tâches", task_count)

    st.divider()

    report_pdf = generate_stats_pdf_report(
        filtered_df=filtered,
        selected_years=selected_years,
        selected_seasons=selected_seasons,
    )

    st.download_button(
        label="Exporter le rapport PDF",
        data=report_pdf,
        file_name="norcycle_rapport_temps_benevole.pdf",
        mime="application/pdf",
        use_container_width=True,
    )

    st.caption(
        "Le rapport PDF utilise les filtres sélectionnés ci-dessus. "
        "Les graphiques sont régénérés pour le PDF, parce que copier un graphique interactif dans un PDF "
        "est un sport que personne ne mérite."
    )

    st.divider()

    tab_overview, tab_people, tab_tasks, tab_time = st.tabs(
        [
            "Vue globale",
            "Pareto bénévoles",
            "Pareto tâches",
            "Années / saisons",
        ]
    )

    with tab_overview:
        st.subheader("Résumé filtré")

        summary_by_year = (
            filtered.groupby(["year", "season"])["hours"]
            .sum()
            .reset_index()
            .sort_values(["year", "season"])
        )

        st.dataframe(summary_by_year, use_container_width=True, hide_index=True)

        render_year_season_chart(filtered)

    with tab_people:
        render_pareto(
            filtered,
            dimension="volunteer_name",
            title="Pareto des heures par bénévole",
            dimension_label="Bénévole",
        )

    with tab_tasks:
        render_pareto(
            filtered,
            dimension="task_name",
            title="Pareto des heures par tâche",
            dimension_label="Tâche",
        )

    with tab_time:
        render_year_season_chart(filtered)

        monthly = filtered.copy()
        monthly["month"] = monthly["work_date"].dt.to_period("M").astype(str)

        monthly_summary = (
            monthly.groupby("month")["hours"]
            .sum()
            .reset_index()
            .sort_values("month")
        )

        if not monthly_summary.empty:
            chart = (
                alt.Chart(monthly_summary)
                .mark_bar()
                .encode(
                    x=alt.X("month:N", title="Mois", axis=alt.Axis(labelAngle=-35)),
                    y=alt.Y("hours:Q", title="Heures"),
                    tooltip=[
                        alt.Tooltip("month:N", title="Mois"),
                        alt.Tooltip("hours:Q", title="Heures", format=".2f"),
                    ],
                )
                .properties(height=340, title="Heures par mois")
            )

            st.altair_chart(chart, use_container_width=True)


def render_admin_page(entries_df):
    if not is_admin():
        st.warning("Cette page est réservée aux administrateurs.")
        return

    st.header("Administration")

    tab_users, tab_lists, tab_entries = st.tabs(
        [
            "Comptes",
            "Bénévoles / tâches",
            "Saisies",
        ]
    )

    with tab_users:
        st.subheader("Créer un compte")

        with st.form("create_user_form"):
            col1, col2 = st.columns(2)

            with col1:
                display_name = st.text_input("Nom affiché")
                username = st.text_input("Nom d'utilisateur")

            with col2:
                role = st.selectbox(
                    "Rôle",
                    options=list(ROLES.keys()),
                    format_func=lambda r: ROLES[r],
                    index=1,
                )
                password = st.text_input("Mot de passe temporaire", type="password")

            submitted = st.form_submit_button("Créer le compte", use_container_width=True)

            if submitted:
                try:
                    create_user(
                        username=username,
                        display_name=display_name,
                        password=password,
                        role=role,
                        active=True,
                    )
                    maybe_add_volunteer(display_name)
                    st.success("Compte créé.")
                    st.rerun()
                except Exception as exc:
                    st.error("Création impossible.")
                    st.exception(exc)

        st.divider()

        users = load_table(USERS_TABLE, order_by="username")

        clean_users = pd.DataFrame(users)

        if not clean_users.empty:
            clean_users = clean_users.drop(columns=["password_hash"], errors="ignore")

            st.dataframe(clean_users, use_container_width=True, hide_index=True)

            st.subheader("Modifier un compte")

            user_by_id = {u["id"]: u for u in users}
            selected_user_id = st.selectbox(
                "Compte",
                options=list(user_by_id.keys()),
                format_func=lambda user_id: (
                    f"{user_by_id[user_id]['username']} - "
                    f"{user_by_id[user_id]['display_name']}"
                ),
            )

            selected_user = user_by_id[selected_user_id]

            col_a, col_b = st.columns(2)

            with col_a:
                new_role = st.selectbox(
                    "Nouveau rôle",
                    options=list(ROLES.keys()),
                    format_func=lambda r: ROLES[r],
                    index=list(ROLES.keys()).index(selected_user["role"]),
                    key="admin_edit_role",
                )

                new_active = st.checkbox(
                    "Compte actif",
                    value=selected_user.get("active", True),
                    key="admin_edit_active",
                )

                if st.button("Mettre à jour le compte", use_container_width=True):
                    update_row(
                        USERS_TABLE,
                        selected_user_id,
                        {
                            "role": new_role,
                            "active": new_active,
                        },
                    )
                    st.success("Compte mis à jour.")
                    st.rerun()

            with col_b:
                new_password = st.text_input(
                    "Nouveau mot de passe",
                    type="password",
                    key="admin_reset_password",
                )

                if st.button("Réinitialiser le mot de passe", use_container_width=True):
                    if len(new_password) < 8:
                        st.error("Minimum 8 caractères.")
                    else:
                        update_row(
                            USERS_TABLE,
                            selected_user_id,
                            {
                                "password_hash": hash_password(new_password),
                            },
                        )
                        st.success("Mot de passe réinitialisé.")

    with tab_lists:
        st.subheader("Ajouter un bénévole")

        with st.form("add_volunteer_form"):
            volunteer_name = st.text_input("Nom du bénévole")
            submitted = st.form_submit_button("Ajouter le bénévole", use_container_width=True)

            if submitted:
                maybe_add_volunteer(volunteer_name)
                st.success("Bénévole ajouté.")
                st.rerun()

        st.subheader("Ajouter une tâche")

        with st.form("add_task_form"):
            task_name = st.text_input("Nom de la tâche")
            submitted = st.form_submit_button("Ajouter la tâche", use_container_width=True)

            if submitted:
                maybe_add_task(task_name)
                st.success("Tâche ajoutée.")
                st.rerun()

        st.divider()

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### Bénévoles")
            volunteers = load_table(VOLUNTEERS_TABLE, order_by="name")
            st.dataframe(
                pd.DataFrame(volunteers),
                use_container_width=True,
                hide_index=True,
            )

        with col2:
            st.markdown("### Tâches")
            tasks = load_table(TASKS_TABLE, order_by="name")
            st.dataframe(
                pd.DataFrame(tasks),
                use_container_width=True,
                hide_index=True,
            )

    with tab_entries:
        st.subheader("Gérer les saisies")

        if entries_df.empty:
            st.info("Aucune saisie.")
            return

        display = entries_df.copy()
        display["work_date"] = display["work_date"].dt.date

        st.dataframe(
            display[
                [
                    "id",
                    "work_date",
                    "volunteer_name",
                    "task_name",
                    "hours",
                    "note",
                    "created_by",
                ]
            ],
            use_container_width=True,
            hide_index=True,
        )

        entry_by_id = {
            row["id"]: row
            for _, row in display.iterrows()
        }

        selected_entry_id = st.selectbox(
            "Saisie à supprimer",
            options=list(entry_by_id.keys()),
            format_func=lambda entry_id: (
                f"{entry_by_id[entry_id]['work_date']} - "
                f"{entry_by_id[entry_id]['volunteer_name']} - "
                f"{entry_by_id[entry_id]['hours']} h"
            ),
        )

        if st.button("Supprimer cette saisie", use_container_width=True):
            delete_row(HOURS_TABLE, selected_entry_id)
            st.success("Saisie supprimée.")
            st.rerun()


def render_data_page(entries_df):
    st.header("Import / export")

    volunteers = load_table(VOLUNTEERS_TABLE, order_by="name")
    tasks = load_table(TASKS_TABLE, order_by="name")
    users = load_table(USERS_TABLE, order_by="username")

    excel_bytes = export_to_excel(entries_df, volunteers, tasks, users)

    st.download_button(
        "Exporter toutes les données en Excel",
        data=excel_bytes,
        file_name="norcycle_temps_benevole.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )

    st.caption(
        "Export complet : saisies, bénévoles, tâches et comptes sans les mots de passe."
    )

    st.divider()

    if not is_admin():
        st.info("L'import Excel est réservé aux administrateurs.")
        return

    st.subheader("Importer l'ancien fichier Excel")

    uploaded_file = st.file_uploader(
        "Fichier Excel",
        type=["xlsx"],
        help="Compatible avec l'ancien fichier Norcycle contenant la feuille Inscription.",
    )

    if uploaded_file is not None:
        try:
            imported_df = read_old_excel(uploaded_file)

            st.write(f"Entrées détectées : **{len(imported_df)}**")

            st.dataframe(
                imported_df.head(50),
                use_container_width=True,
                hide_index=True,
            )

            if st.button("Importer ces entrées", type="primary", use_container_width=True):
                for _, row in imported_df.iterrows():
                    add_time_entry(
                        volunteer_name=row["volunteer_name"],
                        task_name=row["task_name"],
                        hours=row["hours"],
                        work_date=row["work_date"],
                        note=row.get("note", ""),
                        created_by=current_user()["username"],
                    )

                st.success("Import terminé.")
                st.rerun()

        except Exception as exc:
            st.error("Import impossible.")
            st.exception(exc)


# ------------------------------------------------------------
# Bootstrap app
# ------------------------------------------------------------

run_healthcheck_if_requested()

try:
    user_count = count_users()
except Exception as exc:
    st.error(
        "Impossible d'accéder aux tables Supabase. "
        "Vérifie que le script SQL a été exécuté et que les secrets sont configurés."
    )
    st.exception(exc)
    st.stop()

if user_count == 0:
    render_first_admin_setup()
    st.stop()

if not is_logged_in():
    render_login()
    st.stop()


# ------------------------------------------------------------
# App connectée
# ------------------------------------------------------------

user = current_user()

with st.sidebar:
    st.markdown("## Norcycle")
    st.caption("Temps bénévole")

    st.success(f"Connecté : {user['display_name']}")
    st.caption(f"Rôle : {ROLES.get(user['role'], user['role'])}")

    if st.button("Se déconnecter", use_container_width=True):
        logout()

    st.divider()

    pages = ["Saisie", "Statistiques", "Import / export"]

    if is_admin():
        pages.append("Administration")

    selected_page = st.radio(
        "Navigation",
        options=pages,
        index=0,
    )


entries = load_entries()
entries_df = make_entries_df(entries)

st.markdown("# Norcycle - Temps bénévole")
st.markdown(
    """
    <div class="subtitle">
        Saisie des heures bénévoles · Statistiques · Pareto · Rapport PDF · Supabase
    </div>
    """,
    unsafe_allow_html=True,
)

total_hours = entries_df["hours"].sum() if not entries_df.empty else 0
total_entries = len(entries_df)
total_volunteers = entries_df["volunteer_name"].nunique() if not entries_df.empty else 0
total_tasks = entries_df["task_name"].nunique() if not entries_df.empty else 0

kpi1, kpi2, kpi3, kpi4 = st.columns(4)

with kpi1:
    st.metric("Heures totales", f"{total_hours:.2f}")

with kpi2:
    st.metric("Saisies", total_entries)

with kpi3:
    st.metric("Bénévoles", total_volunteers)

with kpi4:
    st.metric("Tâches", total_tasks)

st.divider()

if selected_page == "Saisie":
    render_entry_page(entries_df)

elif selected_page == "Statistiques":
    render_stats_page(entries_df)

elif selected_page == "Import / export":
    render_data_page(entries_df)

elif selected_page == "Administration":
    render_admin_page(entries_df)
