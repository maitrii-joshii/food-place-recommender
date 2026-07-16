import streamlit as st
from src.data import load_and_preprocess
from src.filters import filter_restaurants, NoResultsError
from src.filters.preferences import validate_preferences
from src.prompt import build_system_prompt, build_user_prompt, NoCandidatesError
from src.groq_client import GroqClient, GroqClientError
from src.formatter import parse_llm_response, FormatterError

st.set_page_config(page_title="Food Recommender", page_icon="🍽️", layout="centered")

st.title("🍽️ Food Recommender")
st.markdown("AI-powered dining recommendations tailored for you.")


# --- Initialization and Caching ---
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

# --- Metadata for Form ---
cities = sorted(df["location"].dropna().unique().tolist())
all_cuisines = set(c for sublist in df["cuisines"].dropna() for c in sublist)
cuisines = sorted(list(all_cuisines))

# --- UI Form ---
with st.form("preferences_form"):
    st.subheader("Your Preferences")

    location = st.selectbox("City / Location", options=[""] + cities)
    budget = st.selectbox(
        "Budget",
        options=["low", "medium", "high"],
        format_func=lambda x: {
            "low": "Low (Affordable)",
            "medium": "Medium (Moderate)",
            "high": "High (Premium)",
        }.get(x, x),
    )

    # We allow typing custom cuisines or selecting from existing ones
    cuisine = st.selectbox("Cuisine (Optional)", options=[""] + cuisines)
    min_rating = st.slider(
        "Minimum Rating (0 - 5)", min_value=0.0, max_value=5.0, value=4.0, step=0.1
    )
    extra_preferences = st.text_input(
        "Extra Preferences (Optional)",
        placeholder="e.g., outdoor seating, family-friendly, live music",
    )

    submit = st.form_submit_button("Find Places")

# --- Recommendation Logic ---
if submit:
    if not location:
        st.warning("Please select a City / Location.")
    else:
        with st.spinner("Finding the best places for you..."):
            try:
                # 1. Validate Preferences
                prefs = validate_preferences(
                    location=location,
                    budget=budget,
                    cuisine=cuisine if cuisine else "",
                    min_rating=str(min_rating),
                    extra_preferences=extra_preferences,
                )

                # 2. Filter Restaurants
                candidates = filter_restaurants(df, prefs, max_results=20)

                # 3. Build Prompts
                system_prompt = build_system_prompt()
                user_prompt = build_user_prompt(prefs, candidates)

                # 4. Generate Recommendations via LLM
                raw_response = llm_client.generate_recommendations(
                    system_prompt, user_prompt
                )

                # 5. Parse
                parsed_data = parse_llm_response(raw_response)

                st.success("Here are your top recommendations!")

                for idx, rec in enumerate(parsed_data):
                    with st.expander(
                        f"{idx+1}. {rec.get('name', 'Unknown')}", expanded=True
                    ):
                        st.write(
                            f"**Why we recommend it:** {rec.get('explanation', 'No explanation provided.')}"
                        )

            except NoResultsError as e:
                st.warning(str(e))
            except NoCandidatesError as e:
                st.warning(str(e))
            except FormatterError:
                # Fallback to returning raw if parsing fails
                st.success("Here are your top recommendations!")
                st.write(raw_response)
            except Exception as e:
                st.error(f"An unexpected error occurred: {e}")
