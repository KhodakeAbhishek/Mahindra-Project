import streamlit as st
import pandas as pd
import json
import os
import re
import hashlib
import time

from google import genai
from google.genai import types
from tavily import TavilyClient
from pydantic import BaseModel


# ============================================================
# STREAMLIT CONFIG
# ============================================================

st.set_page_config(
    page_title="Global Tractor Dealer Intelligence",
    page_icon="🚜",
    layout="wide"
)


# ============================================================
# CONSTANTS
# ============================================================

GEMINI_MODEL = "gemini-3.6-flash"

CACHE_FILE = "dealer_search_cache.json"

TRACTOR_BRANDS = [
    "Mahindra",
    "Escorts Kubota",
    "Sonalika",
    "TAFE",
    "Swaraj",
    "John Deere",
    "Kubota",
    "New Holland",
    "Case IH",
    "Massey Ferguson",
    "Fendt",
    "Deutz-Fahr",
    "Claas",
    "Kioti",
    "Valtra",
    "McCormick",
    "Same",
    "Zetor"
]

OUTPUT_COLUMNS = [
    "Company Name",
    "Dealer Name",
    "Country",
    "State / Province",
    "City",
    "Address",
    "Phone",
    "Email"
]


# ============================================================
# API KEYS
# ============================================================

GEMINI_API_KEY = "AQ.Ab8RN6JqN0uMIe55uhYzQttoiJH4F99p_wSO93ZgQpanBBI_Og"
TAVILY_API_KEY = "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"

gemini_client = genai.Client(
    api_key=GEMINI_API_KEY
)
#genai.configure(api_key=GEMINI_API_KEY)
tavily_client = TavilyClient(api_key=TAVILY_API_KEY)



# ============================================================
# CLIENTS
# ============================================================

try:

    gemini_client = genai.Client(
        api_key=GEMINI_API_KEY
    )

    tavily_client = TavilyClient(
        api_key=TAVILY_API_KEY
    )

except Exception as e:

    st.error(
        f"Could not initialize API clients: {e}"
    )

    st.stop()


# ============================================================
# GEMINI STRUCTURED OUTPUT SCHEMA
# ============================================================

class Dealer(BaseModel):

    Company_Name: str
    Dealer_Name: str
    Country: str
    State_Province: str
    City: str
    Address: str
    Phone: str
    Email: str


class DealerResults(BaseModel):

    dealers: list[Dealer]


# ============================================================
# TEXT CLEANING
# ============================================================

def clean_text(value):

    if value is None:
        return ""

    value = str(value)

    value = value.replace(
        "\n",
        " "
    )

    value = re.sub(
        r"\s+",
        " ",
        value
    )

    return value.strip()


# ============================================================
# NORMALIZE COUNTRY
#
# This prevents:
#
# Brazil / Brasil
# Germany / Deutschland
# Spain / España
#
# from unnecessarily causing records to be rejected.
# ============================================================

COUNTRY_ALIASES = {

    "brazil": [
        "brazil",
        "brasil"
    ],

    "germany": [
        "germany",
        "deutschland"
    ],

    "spain": [
        "spain",
        "españa",
        "espana"
    ],

    "france": [
        "france"
    ],

    "italy": [
        "italy",
        "italia"
    ],

    "japan": [
        "japan",
        "日本"
    ],

    "south korea": [
        "south korea",
        "korea",
        "대한민국"
    ],

    "china": [
        "china",
        "中国"
    ],

    "india": [
        "india",
        "भारत"
    ],

    "netherlands": [
        "netherlands",
        "holland",
        "nederland"
    ],

    "portugal": [
        "portugal"
    ],

    "mexico": [
        "mexico",
        "méxico"
    ]
}


def countries_match(
    requested,
    returned
):

    requested = clean_text(
        requested
    ).lower()

    returned = clean_text(
        returned
    ).lower()

    if not returned:
        return True

    if requested == returned:
        return True

    aliases = COUNTRY_ALIASES.get(
        requested,
        [requested]
    )

    if returned in aliases:
        return True

    if requested in returned:
        return True

    if returned in requested:
        return True

    return False


# ============================================================
# LOAD PERSISTENT CACHE
# ============================================================

def load_cache():

    if not os.path.exists(
        CACHE_FILE
    ):
        return {}

    try:

        with open(
            CACHE_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            return json.load(f)

    except Exception:

        return {}


# ============================================================
# SAVE PERSISTENT CACHE
# ============================================================

def save_cache(cache):

    try:

        with open(
            CACHE_FILE,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                cache,
                f,
                ensure_ascii=False,
                indent=2
            )

    except Exception as e:

        print(
            f"Cache save error: {e}"
        )


# ============================================================
# CACHE KEY
# ============================================================

def make_cache_key(
    brand,
    country,
    state,
    city
):

    value = "|".join([
        clean_text(brand).lower(),
        clean_text(country).lower(),
        clean_text(state).lower(),
        clean_text(city).lower()
    ])

    return hashlib.sha256(
        value.encode(
            "utf-8"
        )
    ).hexdigest()


# ============================================================
# UNIVERSAL SEARCH QUERY BUILDER
#
# IMPORTANT:
# No official domains.
# No country-specific dictionary.
# Works worldwide.
# ============================================================

def build_search_queries(
    brand,
    country,
    state,
    city
):

    brand = clean_text(
        brand
    )

    country = clean_text(
        country
    )

    state = clean_text(
        state
    )

    city = clean_text(
        city
    )

    queries = []

    # ========================================================
    # COUNTRY-WIDE SEARCHES
    # ========================================================

    queries.extend([

        f"{brand} tractor dealer {country}",

        f"{brand} tractor dealers {country}",

        f"{brand} dealer {country}",

        f"{brand} dealers {country}",

        f"{brand} tractor distributor {country}",

        f"{brand} distributor {country}",

        f"{brand} tractor dealership {country}",

        f"{brand} tractor dealerships {country}",

        f"{brand} authorized dealer {country}",

        f"{brand} authorized distributor {country}",

        f"{brand} tractor reseller {country}",

        f"{brand} agricultural machinery dealer {country}",

        f"{brand} farm machinery dealer {country}",

        f"{brand} tractor dealer phone {country}",

        f"{brand} tractor dealer address {country}",

        f"{brand} tractor dealer contact {country}",

        f"{brand} tractor dealer email {country}",

        f"{brand} tractor dealer directory {country}",

        f"{brand} dealer network {country}",

        f"{brand} tractor dealership contact {country}"

    ])


    # ========================================================
    # CITY SEARCHES
    # ========================================================

    if city:

        queries.extend([

            f"{brand} tractor dealer {city} {country}",

            f"{brand} dealer {city} {country}",

            f"{brand} dealers {city} {country}",

            f"{brand} distributor {city} {country}",

            f"{brand} tractor distributor {city} {country}",

            f"{brand} dealership {city} {country}",

            f"{brand} tractor dealership {city} {country}",

            f"{brand} authorized dealer {city} {country}",

            f"{brand} tractor dealer phone {city} {country}",

            f"{brand} tractor dealer address {city} {country}",

            f"{brand} tractor dealer contact {city} {country}",

            f"{brand} agricultural machinery dealer {city} {country}"

        ])


    # ========================================================
    # STATE / PROVINCE SEARCHES
    # ========================================================

    if state:

        queries.extend([

            f"{brand} tractor dealer {state} {country}",

            f"{brand} dealer {state} {country}",

            f"{brand} dealers {state} {country}",

            f"{brand} distributor {state} {country}",

            f"{brand} tractor distributor {state} {country}",

            f"{brand} dealership {state} {country}",

            f"{brand} tractor dealership {state} {country}",

            f"{brand} authorized dealer {state} {country}",

            f"{brand} agricultural machinery dealer {state} {country}"

        ])


    # ========================================================
    # REMOVE DUPLICATES
    # ========================================================

    final_queries = []

    seen = set()

    for query in queries:

        query = clean_text(
            query
        )

        key = query.lower()

        if (
            query
            and key not in seen
        ):

            final_queries.append(
                query
            )

            seen.add(key)

    return final_queries


# ============================================================
# TAVILY SEARCH
# ============================================================

def search_tavily(
    query,
    max_results=10
):

    try:

        response = tavily_client.search(

            query=query,

            search_depth="advanced",

            max_results=max_results,

            include_answer=False,

            include_raw_content=True

        )

        return response.get(
            "results",
            []
        )

    except Exception as e:

        print(
            f"Tavily error: {e}"
        )

        return []


# ============================================================
# COLLECT ALL TAVILY RESULTS
# ============================================================

def collect_tavily_results(
    brand,
    country,
    state,
    city,
    progress_callback=None
):

    queries = build_search_queries(
        brand=brand,
        country=country,
        state=state,
        city=city
    )

    all_results = {}

    total_queries = len(
        queries
    )

    for index, query in enumerate(
        queries
    ):

        results = search_tavily(
            query=query,
            max_results=10
        )

        for result in results:

            title = clean_text(
                result.get(
                    "title",
                    ""
                )
            )

            content = (
                result.get(
                    "raw_content",
                    ""
                )
                or result.get(
                    "content",
                    ""
                )
            )

            content = clean_text(
                content
            )

            url = clean_text(
                result.get(
                    "url",
                    ""
                )
            )

            if not content:
                continue

            # URL is used ONLY internally for
            # deduplication. It is never returned
            # to the user.

            result_key = (
                url
                if url
                else
                title.lower()
                + "|"
                + content[:300].lower()
            )

            if result_key not in all_results:

                all_results[result_key] = {

                    "title": title,

                    "content": content

                }

        if progress_callback:

            progress_callback(
                (index + 1)
                / total_queries
            )

    return list(
        all_results.values()
    )


# ============================================================
# PREPARE DATA FOR GEMINI
# ============================================================

def prepare_gemini_context(
    tavily_results,
    max_results=80
):

    chunks = []

    for index, result in enumerate(
        tavily_results[:max_results]
    ):

        title = clean_text(
            result.get(
                "title",
                ""
            )
        )

        content = clean_text(
            result.get(
                "content",
                ""
            )
        )

        # Keep individual pages manageable
        if len(content) > 10000:

            content = content[:10000]

        chunks.append(
            f"""
WEB RESULT {index + 1}

TITLE:
{title}

CONTENT:
{content}
"""
        )

    return "\n\n".join(
        chunks
    )


# ============================================================
# GEMINI EXTRACTION
#
# Gemini 3.6 Flash + structured JSON
# ============================================================

def extract_dealers_with_gemini(
    brand,
    country,
    state,
    city,
    tavily_results
):

    if not tavily_results:

        return []


    context = prepare_gemini_context(
        tavily_results
    )


    prompt = f"""
You are a professional market-intelligence
data extraction system.

You are NOT a web search engine.

The web information below was collected by Tavily.

Your job is ONLY to extract tractor dealers
supported by that supplied web information.

============================================================
REQUEST
============================================================

Brand:
{brand}

Country:
{country}

State / Province:
{state}

City:
{city}

============================================================
IMPORTANT
============================================================

Extract EVERY distinct dealer that is supported
by the supplied web results.

Do not select only the first or best dealer.

Do not return only one dealer.

If 2 dealers are supported, return 2.

If 10 dealers are supported, return 10.

If 30 dealers are supported, return 30.

Do not invent dealers.

Do not use your own knowledge.

Do not browse the internet yourself.

Use ONLY the supplied Tavily information.

============================================================
WHAT COUNTS AS A DEALER
============================================================

Include businesses that are clearly described as:

- tractor dealer
- tractor dealers
- tractor distributor
- distributor
- dealership
- authorized dealer
- authorized distributor
- agricultural machinery dealer
- farm machinery dealer
- tractor reseller
- concessionaire
- concessionária
- revendedor
- concessionnaire
- Händler
- Landmaschinenhändler

The exact local-language terminology may differ.

Use the context to determine whether the business
actually sells or distributes the requested tractor brand.

============================================================
LOCATION
============================================================

The requested country is:

{country}

Only include businesses that the supplied information
supports as being located in or serving the requested
country.

If a city was supplied:

{city}

prioritize businesses in that city.

However, do NOT discard a valid country-level dealer
merely because its city is different if the user did
not require a city-only search.

If state/province was supplied:

{state}

use it when supported by the supplied data.

============================================================
MISSING DATA
============================================================

Never guess.

If phone is unavailable:

""

If email is unavailable:

""

If address is unavailable:

""

If city is unavailable:

""

If state is unavailable:

""

============================================================
COUNTRY NAME
============================================================

Country names can appear in different languages.

Examples:

Brazil = Brasil

Germany = Deutschland

Spain = España

Italy = Italia

India = भारत / India

Japan = 日本 / Japan

Do not reject a valid dealer merely because
the country is written in another language.

============================================================
IMPORTANT DATA RULE
============================================================

The following fields must contain ONLY dealer data:

Company Name
Dealer Name
Country
State / Province
City
Address
Phone
Email

Do NOT put URLs in any field.

Do NOT put source names in any field.

Do NOT put citations in any field.

Do NOT put "Source:" anywhere.

Do NOT put website addresses anywhere.

Do NOT add notes.

Do NOT add comments.

============================================================
COMPANY NAME
============================================================

"Company Name" should normally be:

{brand}

unless the supplied information clearly identifies
the manufacturer/brand under a different written form.

============================================================
DEALER NAME
============================================================

Use the actual dealer/business name.

Examples:

DIMO Agribusinesses

Super Safra

Mahindra Papanduva

etc.

Do not replace the dealer name with the tractor brand.

============================================================
CONTACT INFORMATION
============================================================

Extract phone numbers exactly as supported
by the supplied text.

Extract email addresses exactly as supported
by the supplied text.

Do not manufacture phone numbers or emails.

============================================================
DUPLICATES
============================================================

If the same dealer appears in multiple web results,
return it only once.

If the same dealer has multiple phone numbers,
you may combine them using:

Phone 1 / Phone 2

If the same dealer has multiple emails,
you may combine them using:

email1 / email2

============================================================
TAVILY WEB DATA
============================================================

{context}
"""


    try:

        response = gemini_client.models.generate_content(

            model=GEMINI_MODEL,

            contents=prompt,

            config=types.GenerateContentConfig(

                response_mime_type="application/json",

                response_schema=DealerResults,

                max_output_tokens=20000

            )

        )

        raw = response.text.strip()

        parsed = DealerResults.model_validate_json(
            raw
        )

        dealers = []

        for dealer in parsed.dealers:

            dealers.append({

                "Company Name":
                    clean_text(
                        dealer.Company_Name
                    ),

                "Dealer Name":
                    clean_text(
                        dealer.Dealer_Name
                    ),

                "Country":
                    clean_text(
                        dealer.Country
                    ),

                "State / Province":
                    clean_text(
                        dealer.State_Province
                    ),

                "City":
                    clean_text(
                        dealer.City
                    ),

                "Address":
                    clean_text(
                        dealer.Address
                    ),

                "Phone":
                    clean_text(
                        dealer.Phone
                    ),

                "Email":
                    clean_text(
                        dealer.Email
                    )

            })

        return dealers


    except Exception as e:

        st.error(
            f"Gemini extraction error for "
            f"{brand}: {e}"
        )

        return []


# ============================================================
# NORMALIZE DEALER
# ============================================================

def normalize_dealer(
    dealer,
    brand,
    requested_country
):

    company = clean_text(
        dealer.get(
            "Company Name",
            ""
        )
    )

    if not company:

        company = brand

    country = clean_text(
        dealer.get(
            "Country",
            ""
        )
    )

    if not country:

        country = requested_country

    return {

        "Company Name":
            company,

        "Dealer Name":
            clean_text(
                dealer.get(
                    "Dealer Name",
                    ""
                )
            ),

        "Country":
            country,

        "State / Province":
            clean_text(
                dealer.get(
                    "State / Province",
                    ""
                )
            ),

        "City":
            clean_text(
                dealer.get(
                    "City",
                    ""
                )
            ),

        "Address":
            clean_text(
                dealer.get(
                    "Address",
                    ""
                )
            ),

        "Phone":
            clean_text(
                dealer.get(
                    "Phone",
                    ""
                )
            ),

        "Email":
            clean_text(
                dealer.get(
                    "Email",
                    ""
                )
            )

    }


# ============================================================
# BASIC DEALER VALIDATION
#
# IMPORTANT:
# We do NOT aggressively validate country strings.
# Gemini already receives the location context.
# ============================================================

def valid_dealer(
    dealer
):

    dealer_name = clean_text(
        dealer.get(
            "Dealer Name",
            ""
        )
    )

    if not dealer_name:

        return False

    # Need at least one useful identifying detail.
    if not any([

        dealer.get(
            "Address",
            ""
        ),

        dealer.get(
            "Phone",
            ""
        ),

        dealer.get(
            "Email",
            ""
        ),

        dealer.get(
            "City",
            ""
        )

    ]):

        return False

    return True


# ============================================================
# DEALER DEDUPLICATION
# ============================================================

def deduplicate_dealers(
    dealers
):

    unique = {}

    for dealer in dealers:

        dealer_name = clean_text(
            dealer.get(
                "Dealer Name",
                ""
            )
        )

        city = clean_text(
            dealer.get(
                "City",
                ""
            )
        )

        address = clean_text(
            dealer.get(
                "Address",
                ""
            )
        )

        phone = clean_text(
            dealer.get(
                "Phone",
                ""
            )
        )

        email = clean_text(
            dealer.get(
                "Email",
                ""
            )
        )

        if not dealer_name:
            continue

        # ----------------------------------------------------
        # Strongest key: dealer + phone
        # ----------------------------------------------------

        if phone:

            key = (
                dealer_name.lower()
                + "|phone|"
                + re.sub(
                    r"\D",
                    "",
                    phone
                )
            )

        # ----------------------------------------------------
        # Second: dealer + email
        # ----------------------------------------------------

        elif email:

            key = (
                dealer_name.lower()
                + "|email|"
                + email.lower()
            )

        # ----------------------------------------------------
        # Third: dealer + city + address
        # ----------------------------------------------------

        else:

            key = (
                dealer_name.lower()
                + "|"
                + city.lower()
                + "|"
                + address.lower()
            )

        # ----------------------------------------------------
        # Merge duplicate records
        # ----------------------------------------------------

        if key not in unique:

            unique[key] = dealer

        else:

            existing = unique[key]

            for field in OUTPUT_COLUMNS:

                old_value = clean_text(
                    existing.get(
                        field,
                        ""
                    )
                )

                new_value = clean_text(
                    dealer.get(
                        field,
                        ""
                    )
                )

                if not old_value and new_value:

                    existing[field] = new_value

    return list(
        unique.values()
    )


# ============================================================
# REMOVE URLS FROM DISPLAY DATA
# ============================================================

def remove_urls_from_data(
    dealer
):

    cleaned = {}

    for field in OUTPUT_COLUMNS:

        value = clean_text(
            dealer.get(
                field,
                ""
            )
        )

        # Remove accidental URLs
        value = re.sub(
            r"https?://\S+",
            "",
            value
        )

        value = re.sub(
            r"www\.\S+",
            "",
            value,
            flags=re.IGNORECASE
        )

        cleaned[field] = clean_text(
            value
        )

    return cleaned


# ============================================================
# SAVE FINAL RESULTS
# ============================================================

def save_search_result(
    key,
    dealers,
    metadata
):

    cache = load_cache()

    cache[key] = {

        "timestamp":
            time.time(),

        "metadata":
            metadata,

        "dealers":
            dealers

    }

    save_cache(
        cache
    )


# ============================================================
# GET CACHED RESULT
# ============================================================

def get_cached_result(
    key
):

    cache = load_cache()

    item = cache.get(
        key
    )

    if not item:

        return None

    return item.get(
        "dealers",
        []
    )


# ============================================================
# DISPLAY TABLE
# ============================================================

def display_dealers(
    dealers
):

    if not dealers:

        st.warning(
            "No supported dealer records were found "
            
        )

        return


    # --------------------------------------------------------
    # Clean again before display
    # --------------------------------------------------------

    cleaned_dealers = []

    for dealer in dealers:

        cleaned_dealers.append(
            remove_urls_from_data(
                dealer
            )
        )


    df = pd.DataFrame(
        cleaned_dealers
    )


    # --------------------------------------------------------
    # Guarantee exact columns
    # --------------------------------------------------------

    for column in OUTPUT_COLUMNS:

        if column not in df.columns:

            df[column] = ""


    df = df[
        OUTPUT_COLUMNS
    ]


    # --------------------------------------------------------
    # Metrics
    # --------------------------------------------------------

    col1, col2, col3 = st.columns(3)

    with col1:

        st.metric(
            "Dealers Found",
            len(df)
        )

    with col2:

        phones = (
            df["Phone"]
            .fillna("")
            .astype(str)
            .str.strip()
            .ne("")
            .sum()
        )

        st.metric(
            "Phone Numbers",
            int(phones)
        )

    with col3:

        emails = (
            df["Email"]
            .fillna("")
            .astype(str)
            .str.strip()
            .ne("")
            .sum()
        )

        st.metric(
            "Emails",
            int(emails)
        )


    st.divider()


    # --------------------------------------------------------
    # TABLE
    # --------------------------------------------------------

    st.dataframe(

        df,

        use_container_width=True,

        hide_index=True,

        column_config={

            "Company Name":
                st.column_config.TextColumn(
                    "Company Name"
                ),

            "Dealer Name":
                st.column_config.TextColumn(
                    "Dealer Name"
                ),

            "Country":
                st.column_config.TextColumn(
                    "Country"
                ),

            "State / Province":
                st.column_config.TextColumn(
                    "State / Province"
                ),

            "City":
                st.column_config.TextColumn(
                    "City"
                ),

            "Address":
                st.column_config.TextColumn(
                    "Address"
                ),

            "Phone":
                st.column_config.TextColumn(
                    "Phone"
                ),

            "Email":
                st.column_config.TextColumn(
                    "Email"
                )

        }

    )


    # --------------------------------------------------------
    # CSV DOWNLOAD
    # --------------------------------------------------------

    csv = df.to_csv(
        index=False
    ).encode(
        "utf-8-sig"
    )


    st.download_button(

        label="⬇️ Download Dealer Data",

        data=csv,

        file_name="tractor_dealers.csv",

        mime="text/csv",

        use_container_width=True

    )


# ============================================================
# SEARCH ONE BRAND
# ============================================================

def search_one_brand(
    brand,
    country,
    state,
    city,
    progress_container,
    status_container
):

    # --------------------------------------------------------
    # CACHE KEY
    # --------------------------------------------------------

    cache_key = make_cache_key(

        brand,

        country,

        state,

        city

    )


    # --------------------------------------------------------
    # CHECK PERSISTENT CACHE
    # --------------------------------------------------------

    cached = get_cached_result(
        cache_key
    )

    if cached is not None:

        status_container.info(
            f"Using saved results for {brand}."
        )

        return cached


    # --------------------------------------------------------
    # TAVILY
    # --------------------------------------------------------

    status_container.info(
        f"Searching Dealers for {brand}..."
    )


    tavily_results = collect_tavily_results(

        brand=brand,

        country=country,

        state=state,

        city=city,

        progress_callback=
            progress_container.progress

    )


    status_container.info(
        f"Tavily collected "
        f"{len(tavily_results)} unique web results "
        f"for {brand}."
    )


    # --------------------------------------------------------
    # No Tavily results
    # --------------------------------------------------------

    if not tavily_results:

        save_search_result(

            cache_key,

            [],

            {
                "brand": brand,
                "country": country,
                "state": state,
                "city": city
            }

        )

        return []


    # --------------------------------------------------------
    # GEMINI
    # --------------------------------------------------------

    status_container.info(
        f"Gemini {GEMINI_MODEL} is extracting "
        f"all supported {brand} dealers..."
    )


    dealers = extract_dealers_with_gemini(

        brand=brand,

        country=country,

        state=state,

        city=city,

        tavily_results=tavily_results

    )


    # --------------------------------------------------------
    # NORMALIZE
    # --------------------------------------------------------

    normalized = []

    for dealer in dealers:

        dealer = normalize_dealer(

            dealer=dealer,

            brand=brand,

            requested_country=country

        )

        if valid_dealer(
            dealer
        ):

            normalized.append(
                dealer
            )


    # --------------------------------------------------------
    # DEDUPLICATE
    # --------------------------------------------------------

    normalized = deduplicate_dealers(
        normalized
    )


    # --------------------------------------------------------
    # SAVE
    # --------------------------------------------------------

    save_search_result(

        cache_key,

        normalized,

        {

            "brand": brand,

            "country": country,

            "state": state,

            "city": city

        }

    )


    return normalized


# ============================================================
# MAIN UI
# ============================================================

def render_dealers_tab():

    st.title(
        "🚜 Global Tractor Dealer Intelligence"
    )

    st.caption(
        "Tavily Web Search → Gemini 3.6 Flash Extraction"
    )


    # ========================================================
    # LOCATION
    # ========================================================

    col1, col2, col3 = st.columns(3)


    with col1:

        country = st.text_input(

            "Country *",

            placeholder=
                "Brazil, Sri Lanka, Germany, Kenya..."

        )


    with col2:

        state = st.text_input(

            "State / Province / Region",

            placeholder=
                "São Paulo, Western Province..."

        )


    with col3:

        city = st.text_input(

            "City",

            placeholder=
                "Colombo, São Paulo, Munich..."

        )


    # ========================================================
    # BRAND
    # ========================================================

    brand = st.selectbox(

        "Tractor Brand",

        [
            "All Brands"
        ]
        +
        TRACTOR_BRANDS

    )


    # ========================================================
    # BRAND LIMIT
    # ========================================================

    if brand == "All Brands":

        max_brands = st.slider(

            "Maximum brands to search",

            min_value=1,

            max_value=len(
                TRACTOR_BRANDS
            ),

            value=5

        )

    else:

        max_brands = 1


    # ========================================================
    # SEARCH BUTTON
    # ========================================================

    search_location = ", ".join(

        x.strip()

        for x in [
            city,
            state,
            country
        ]

        if x.strip()

    )


    button_text = (

        f"🔍 Fetch Dealers — "
        f"{search_location}"

        if search_location

        else

        "🔍 Fetch Dealers"

    )


    if st.button(

        button_text,

        type="primary",

        use_container_width=True

    ):


        # ----------------------------------------------------
        # VALIDATION
        # ----------------------------------------------------

        if not country.strip():

            st.warning(
                "Please enter at least a country."
            )

            return


        # ----------------------------------------------------
        # SELECT BRANDS
        # ----------------------------------------------------

        if brand == "All Brands":

            brands = TRACTOR_BRANDS[
                :max_brands
            ]

        else:

            brands = [
                brand
            ]


        all_dealers = []


        overall_progress = st.progress(
            0
        )


        # ----------------------------------------------------
        # SEARCH BRANDS
        # ----------------------------------------------------

        for brand_index, current_brand in enumerate(
            brands
        ):


            st.subheader(
                f"🔎 {current_brand}"
            )


            brand_progress = st.progress(
                0
            )


            status = st.empty()


            try:

                dealers = search_one_brand(

                    brand=current_brand,

                    country=country,

                    state=state,

                    city=city,

                    progress_container=
                        brand_progress,

                    status_container=
                        status

                )


                all_dealers.extend(
                    dealers
                )


                status.success(

                    f"{current_brand}: "
                    f"{len(dealers)} dealer(s) found."

                )


            except Exception as e:

                status.error(

                    f"{current_brand}: "
                    f"{str(e)}"

                )


            overall_progress.progress(

                (brand_index + 1)
                / len(brands)

            )


        # ----------------------------------------------------
        # FINAL DEDUPLICATION
        # ----------------------------------------------------

        all_dealers = deduplicate_dealers(
            all_dealers
        )


        # ----------------------------------------------------
        # FINAL RESULT
        # ----------------------------------------------------

        st.divider()

        st.subheader(
            f"Dealer Results — {search_location}"
        )


        if all_dealers:

            display_dealers(
                all_dealers
            )

        else:

            st.warning(

                "No dealer records were extracted "
                "Try the "
                "country without a city/state, or "
                "try another brand."

            )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    render_dealers_tab()