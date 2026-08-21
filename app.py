import streamlit as st

from src.data import load_and_preprocess
from src.filters import filter_restaurants, NoResultsError
from src.filters.preferences import validate_preferences
from src.formatter import parse_llm_response, FormatterError
from src.groq_client import GroqClient, GroqClientError
from src.prompt import build_system_prompt, build_user_prompt, NoCandidatesError

st.set_page_config(page_title="Food Recommender", page_icon="🍽️", layout="centered")

# ── Custom CSS ──────────────────────────────────────────────────────────────
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

/* ── Global ── */
html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}
.stApp {
    background: #0d0f1e;
    color: #e2e8f0;
}

/* hide default streamlit header/footer */
#MainMenu, footer, header { visibility: hidden; }

/* ── Hero ── */
.hero-title {
    text-align: center;
    font-size: 2.8rem;
    font-weight: 800;
    background: linear-gradient(90deg, #a855f7, #ec4899);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 0.4rem;
    line-height: 1.2;
}
.hero-sub {
    text-align: center;
    color: #94a3b8;
    font-size: 1rem;
    margin-bottom: 2rem;
    line-height: 1.6;
}

/* ── Card ── */
.form-card {
    background: #151728;
    border: 1px solid #1e2340;
    border-radius: 16px;
    padding: 2rem 2.2rem 2.4rem;
    max-width: 760px;
    margin: 0 auto;
}

/* ── Field labels ── */
.field-label {
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    color: #94a3b8;
    text-transform: uppercase;
    display: flex;
    align-items: center;
    gap: 6px;
    margin-bottom: 0.4rem;
}

/* ── Streamlit widget overrides ── */
div[data-testid="stSelectbox"] > div > div {
    background: #1e2340 !important;
    border: 1px solid #2d3561 !important;
    border-radius: 10px !important;
    color: #e2e8f0 !important;
}
div[data-testid="stTextInput"] > div > div > input,
div[data-testid="stTextArea"] textarea {
    background: #1e2340 !important;
    border: 1px solid #2d3561 !important;
    border-radius: 10px !important;
    color: #e2e8f0 !important;
}
div[data-testid="stTextInput"] > div > div > input::placeholder,
div[data-testid="stTextArea"] textarea::placeholder {
    color: #4b5280 !important;
}

/* ── Budget radio → pill buttons ── */
div[data-testid="stRadio"] > div {
    display: flex !important;
    flex-direction: row !important;
    gap: 0.5rem !important;
}
div[data-testid="stRadio"] > div > label {
    background: #1e2340 !important;
    border: 1px solid #2d3561 !important;
    border-radius: 8px !important;
    padding: 0.45rem 1.4rem !important;
    color: #94a3b8 !important;
    cursor: pointer;
    font-weight: 500;
    font-size: 0.9rem;
    transition: all 0.2s;
}
div[data-testid="stRadio"] > div > label:has(input:checked) {
    background: #312060 !important;
    border-color: #a855f7 !important;
    color: #e2e8f0 !important;
}

/* ── Slider ── */
div[data-testid="stSlider"] div[role="slider"] {
    background: #a855f7 !important;
    border-color: #a855f7 !important;
}

/* ── Submit button ── */
div[data-testid="stFormSubmitButton"] > button {
    width: 100% !important;
    background: linear-gradient(90deg, #7c3aed, #db2777) !important;
    color: white !important;
    font-weight: 700 !important;
    font-size: 1.05rem !important;
    border: none !important;
    border-radius: 12px !important;
    padding: 0.75rem 1rem !important;
    margin-top: 0.5rem;
    cursor: pointer;
    transition: opacity 0.2s;
}
div[data-testid="stFormSubmitButton"] > button:hover {
    opacity: 0.9 !important;
}

/* ── Recommendation cards ── */
.rec-card {
    background: #151728;
    border: 1px solid #1e2340;
    border-radius: 14px;
    padding: 1.2rem 1.5rem;
    margin-bottom: 1rem;
}
.rec-rank {
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #a855f7;
    margin-bottom: 0.3rem;
}
.rec-name {
    font-size: 1.2rem;
    font-weight: 700;
    color: #e2e8f0;
    margin-bottom: 0.5rem;
}
.rec-explanation {
    color: #94a3b8;
    font-size: 0.95rem;
    line-height: 1.6;
}
</style>
""",
    unsafe_allow_html=True,
)

# ── Initialization & Caching ────────────────────────────────────────────────


@st.cache_data(show_spinner=False)
def load_data():
    return load_and_preprocess()


@st.cache_resource(show_spinner=False)
def init_groq():
    return GroqClient()


try:
    with st.spinner("Loading dataset..."):
        df = load_data()
except Exception as e:
    st.error(f"Failed to load dataset: {e}")
    st.stop()

try:
    llm_client = init_groq()
except GroqClientError as e:
    st.error(
        f"Failed to initialize Groq API client: {e}. Please check your GROQ_API_KEY secret."
    )
    st.stop()

# ── Metadata ────────────────────────────────────────────────────────────────
# Build a map: display name (Title Case) → raw value (lowercase for matching)
cities_raw = sorted(df["location"].dropna().unique().tolist())
# Filter out any empty strings that might act as a placeholder option
cities_display = [c.title() for c in cities_raw if c]
cities_map = {c.title(): c for c in cities_raw if c}

# ── Hero Section ────────────────────────────────────────────────────────────
st.markdown(
    '<div class="hero-title">Discover Your Next Meal</div>', unsafe_allow_html=True
)
st.markdown(
    '<div class="hero-sub">Tell us what you\'re craving, and our AI will curate<br>the perfect dining experience for you.</div>',
    unsafe_allow_html=True,
)

# ── Form ────────────────────────────────────────────────────────────────────
st.markdown('<div class="form-card">', unsafe_allow_html=True)

with st.form("preferences_form"):
    st.markdown(
        '<p style="color:#cbd5e1;font-size:0.95rem;margin-bottom:1rem;">'
        '🗺️ Start by choosing your <strong style="color:#e2e8f0;">city</strong> and '
        '<strong style="color:#e2e8f0;">budget</strong> — we\'ll handle the rest.</p>',
        unsafe_allow_html=True,
    )
    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown(
            '<div class="field-label">📍 City (Required)</div>',
            unsafe_allow_html=True,
        )
        location = st.selectbox(
            "city",
            options=cities_display,
            index=0,
            label_visibility="collapsed",
        )

    with col2:
        st.markdown(
            '<div class="field-label">💰 Budget (Required)</div>',
            unsafe_allow_html=True,
        )
        budget = st.radio(
            "budget",
            options=["low", "medium", "high"],
            format_func=lambda x: {"low": "Low", "medium": "Med", "high": "High"}[x],
            horizontal=True,
            label_visibility="collapsed",
        )

    st.markdown(
        '<div class="field-label">✕ Cuisine (Optional)</div>', unsafe_allow_html=True
    )
    cuisine = st.text_input(
        "cuisine",
        placeholder="e.g. Italian, Sushi, Vegan",
        label_visibility="collapsed",
    )

    st.markdown(
        '<div class="field-label">★ Minimum Rating</div>', unsafe_allow_html=True
    )
    min_rating = st.slider(
        "min_rating",
        min_value=0.0,
        max_value=5.0,
        value=4.0,
        step=0.1,
        label_visibility="collapsed",
    )

    st.markdown(
        '<div class="field-label">⚡ Extra Preferences</div>', unsafe_allow_html=True
    )
    extra_preferences = st.text_area(
        "extra_preferences",
        placeholder="Tell us more... (e.g. quiet atmosphere, dog friendly, outdoor seating)",
        label_visibility="collapsed",
        height=100,
    )

    submit = st.form_submit_button("✦ Find Places")

st.markdown("</div>", unsafe_allow_html=True)

# ── Recommendation Logic ─────────────────────────────────────────────────────
if submit:
    try:
        prefs = validate_preferences(
            location=cities_map[location],
            budget=budget,
            cuisine=cuisine if cuisine else "",
            min_rating=str(min_rating),
            extra_preferences=extra_preferences,
        )

        candidates = filter_restaurants(df, prefs, max_results=20)
        system_prompt = build_system_prompt()
        user_prompt = build_user_prompt(prefs, candidates)
        raw_response = llm_client.generate_recommendations(system_prompt, user_prompt)
        parsed_data = parse_llm_response(raw_response)

        medals = ["🥇", "🥈", "🥉"]
        st.markdown("---")
        st.markdown(
            '<p style="color:#a855f7;font-weight:700;font-size:0.8rem;letter-spacing:0.1em;text-transform:uppercase;text-align:center;">Top Recommendations</p>',
            unsafe_allow_html=True,
        )
        for idx, rec in enumerate(parsed_data):
            medal = medals[idx] if idx < 3 else f"#{idx+1}"
            st.markdown(
                f"""
                <div class="rec-card">
                    <div class="rec-rank">{medal} Recommendation {idx+1}</div>
                    <div class="rec-name">{rec.get('name', 'Unknown')}</div>
                    <div class="rec-explanation">{rec.get('explanation', 'No explanation provided.')}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    except NoResultsError:
        st.warning(
            "😕 No restaurants found matching your preferences. "
            "Try a different cuisine, lower the minimum rating, or broaden your budget."
        )
    except NoCandidatesError:
        st.warning(
            "😕 Not enough candidates to generate recommendations. "
            "Try relaxing your filters."
        )
    except FormatterError:
        st.success("Here are your top recommendations!")
        st.write(raw_response)
    except Exception as e:
        st.error(f"Something went wrong. Please try again. (Details: {e})")
