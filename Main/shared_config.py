import random
import re
import json
from groq import Groq
# ==========================================
# SHARED CONFIG, KEYS, LOGOS, COLORS
# ==========================================
# Using new google.genai package instead of deprecated google.generativeai
# ••••••••••ltlCua
try:
    import google.genai as genai
    genai_client = genai.Client(api_key="AIzaSyD1yzog4c32HisjN2y-4u-hfr-T1bWD8Uc")
except ImportError:
    # Fallback to old package if new one not available
    import google.generativeai as genai
    genai.configure(api_key="AIzaSyD1yzog4c32HisjN2y-4u-hfr-T1bWD8Uc")
    genai_client = genai.GenerativeModel("gemini-2.5-flash")
YOUTUBE_API_KEY = "AIzaSyA4nB_-mbAmE5ZzkyAaFnJD_2nXUxJm-Eg"
APIFY_API_KEY = "apify_api_c5Yfk7gUP1XUTVxzhJ3yba31MUfZiR4lnzkK"   # your Apify key
CURATOR_FEED_ID = "91ec00ba-66aa-4650-907a-17f6103c23eb"  
FIRECRAWL_API_KEY="fc-b832cbf8b5944af79dea3ff882009fa7"
LLAMA_CLOUD_API_KEY="llx-EoAgxMZ2e0BNOEiJVaD2J5V0qkEDgWa0qcRhm6trdqPAVw1X"
GROQ_API_KEYS = [
    "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"
]
TAVILY_API_KEYS = [
    "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",
    "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",
    "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",
    "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",
    
]

LOGOS = {
    "All (Competitors)": "mahindra.png",
    "Cummins India": "cummin.png",
    "Kirloskar Oil Engines": "kirloskar.png",
    "Mahindra Powerol": "mahindra.png",
    "TAFE Power": "download.jfif"
}

COLORS = {
    "Cummins India": "#ffffff",
    "Kirloskar Oil Engines": "#E31837",
    "Mahindra Powerol": "#F97316",
    "TAFE Power": "#3B82F6"
}

ACCENT_MAP = {
    "Cummins India":        ("#1FD8F0", "rgba(31,216,240,.18)"),
    "Kirloskar Oil Engines":("#FF2D55", "rgba(255,45,85,.18)"),
    "Mahindra Powerol":     ("#FF5C0A", "rgba(255,92,10,.18)"),
    "TAFE Power":           ("#3B82F6", "rgba(59,130,246,.18)"),
}

PLOT_COLORS = {
    "Cummins India": "#1FD8F0",
    "Kirloskar Oil Engines": "#FF2D55",
    "Mahindra Powerol": "#FF5C0A",
    "TAFE Power": "#3B82F6"
}

# ==========================================
# STOCK / SHARE MARKET FILTER KEYWORDS
# ==========================================
STOCK_FILTER_KEYWORDS = [
    "share price", "stock price", "nse", "bse", "sensex", "nifty",
    "equity", "dividend", "market cap", "52-week", "trading halt",
    "investor", "shareholders", "ipo", "quarterly results", "q1 results",
    "q2 results", "q3 results", "q4 results", "earnings per share",
    "eps", "p/e ratio", "bullish", "bearish", "technical analysis",
    "resistance level", "support level", "target price", "buy call",
    "sell call", "intraday", "futures", "options trading", "demat"
]

def is_stock_news(title, content=""):
    combined = (title + " " + content).lower()
    return any(kw in combined for kw in STOCK_FILTER_KEYWORDS)


INDIAN_LOCATIONS = {
    "Andhra Pradesh": ["Visakhapatnam", "Vijayawada/Vijaywada", "Guntur", "Nellore", "Kurnool", "Rajahmundry/Rajamahendravaram", "Tirupati", "Kadappa/Kadapa", "Anantapur"],
    "Arunachal Pradesh": ["Itanagar", "Tawang", "Naharlagun", "Pasighat"],
    "Assam": ["Guwahati", "Silchar", "Dibrugarh", "Jorhat", "Nagaon", "Tinsukia", "Tezpur/Tejpur", "Khatkati", "Cachar"],
    "Bihar": ["Patna", "Gaya", "Bhagalpur", "Muzaffarpur", "Purnia/Purnea", "Darbhanga", "Begusarai", "Gopalganj", "Rohtas", "Motihari"],
    "Chandigarh": ["Chandigarh"],
    "Chhattisgarh": ["Raipur", "Bhilai", "Bilaspur", "Korba", "Durg", "Rajnandgaon", "Ambikapur", "Raigarh", "Jagdalpur"],
    "Delhi": ["New Delhi", "Delhi", "Delhi NCR"],
    "Goa": ["Panaji", "Margao", "Vasco da Gama", "Mapusa", "Verna", "Porvorim", "Bardez"],
    "Gujarat": ["Ahmedabad", "Surat", "Vadodara", "Rajkot", "Bhavnagar", "Jamnagar", "Gandhinagar", "Junagadh", "Gandhidham/Gandhidam", "Vapi", "Palanpur", "Ankleshwar"],
    "Haryana": ["Gurgaon/Gurugram", "Faridabad", "Panipat", "Ambala", "Karnal", "Rohtak", "Hisar/Hissar", "Sonipat", "Panchkula", "Charkhi Dadri", "Jagadhri"],
    "Himachal Pradesh": ["Shimla", "Mandi", "Solan", "Dharamshala", "Kullu", "Bhuntar"],
    "Jammu and Kashmir": ["Srinagar", "Jammu", "Anantnag", "Baramulla"],
    "Jharkhand": ["Ranchi", "Jamshedpur", "Dhanbad", "Bokaro", "Deoghar", "Hazaribagh", "Chandwa", "Giridih", "Daltoganj", "Ramgarh"],
    "Karnataka": ["Bengaluru/Bangalore", "Mysuru/Mysore", "Hubballi/Hubli", "Mangaluru/Mangalore", "Belagavi/Belgaum", "Davanagere/Davangere", "Ballari/Bellary", "Tumakuru", "Hospete/Hospet", "Vijayapura/Bijapur", "Nelamangala", "Shimoga", "Madikeri", "Chitradurga", "Chikmaglur", "Gulbarga/Kalaburagi", "Udupi"],
    "Kerala": ["Thiruvananthapuram", "Kochi/Cochin/Ernakulam", "Kozhikode/Calicut", "Thrissur", "Kollam", "Alappuzha", "Palakkad", "Kottayam", "Kannur"],
    "Madhya Pradesh": ["Indore", "Bhopal", "Jabalpur", "Gwalior", "Ujjain", "Sagar", "Ratlam", "Rewa", "Singrauli", "Satna", "Sendhwa", "Shivpuri"],
    "Maharashtra": ["Mumbai", "Pune", "Nagpur", "Nashik", "Aurangabad", "Thane", "Kolhapur", "Solapur", "Amravati", "Navi Mumbai", "Nanded", "Manmad", "Baramati", "Panvel", "Sangli", "Ahmednagar", "Ulhasnagar", "Palghar", "Mehkar", "Alibag"],
    "Manipur": ["Imphal", "Churachandpur"],
    "Meghalaya": ["Shillong", "Tura"],
    "Mizoram": ["Aizawl", "Lunglei"],
    "Nagaland": ["Kohima", "Dimapur", "Mokokchung"],
    "Odisha": ["Bhubaneswar/Bhubaneshwar", "Cuttack", "Rourkela", "Berhampur/Brahmapur", "Sambalpur", "Puri", "Balasore", "Jharsuguda", "Barbil", "Rayagada/Raigadha", "Bargarh", "Angul", "Jeypore"],
    "Punjab": ["Ludhiana", "Amritsar", "Jalandhar", "Patiala", "Bathinda", "Pathankot", "Malout", "Hoshiarpur"],
    "Rajasthan": ["Jaipur", "Jodhpur", "Udaipur", "Kota", "Bikaner", "Ajmer", "Alwar", "Bhilwara", "Behror", "Pali", "Sikar", "Shahpura", "Nimbahera", "Shri Ganganagar/Sri Ganganagar"],
    "Sikkim": ["Gangtok", "Namchi"],
    "Tamil Nadu": ["Chennai", "Coimbatore", "Madurai", "Salem", "Tiruchirappalli/Trichy", "Tirunelveli", "Vellore", "Erode", "Hosur", "Krishnagiri", "Tuticorin/Thoothukudi", "Sivakasi", "Sivaganga/Sivaganagai", "Theni", "Nagercoil"],
    "Telangana": ["Hyderabad", "Warangal", "Nizamabad", "Karimnagar", "Khammam", "Ramagundam", "Secunderabad", "Mahabubnagar", "Hanamkonda", "Nalgonda"],
    "Tripura": ["Agartala", "Dharmanagar"],
    "Uttar Pradesh": ["Lucknow", "Kanpur", "Ghaziabad", "Agra", "Varanasi", "Meerut", "Prayagraj/Allahabad", "Bareilly", "Aligarh", "Moradabad", "Noida", "Greater Noida", "Muzaffarnagar", "Kabrai", "Gorakhpur", "Rae Bareli", "Ayodhya/Faizabad", "Jhansi", "Jaunpur", "Anpara", "Mau", "Bahraich", "Saharanpur"],
    "Uttarakhand": ["Dehradun", "Haridwar", "Roorkee", "Haldwani", "Rishikesh", "Rudrapur"],
    "West Bengal": ["Kolkata", "Howrah", "Siliguri", "Durgapur", "Asansol", "Kharagpur", "Burdwan/Bardhaman", "Malda", "Rampurhat", "Krishnanagar/Nadia", "Kolaghat", "Murshidabad", "Medinipur", "Hooghly", "Darjeeling"],
    "Andaman and Nicobar Islands": ["Port Blair"],
    "Puducherry": ["Puducherry/Pondicherry", "Karaikal"]
}

def get_groq_client():
    return Groq(api_key=random.choice(GROQ_API_KEYS))

def get_tavily_key():
    return random.choice(TAVILY_API_KEYS)

def get_firecrawl_key():
    return FIRECRAWL_API_KEY

def get_llamaparse_key():
    return LLAMA_CLOUD_API_KEY

def safe_json_parse(text):
    try:
        text = re.sub(r'```json\s*', '', text)
        text = re.sub(r'```\s*', '', text)
        match = re.search(r'(\{.*\}|\[.*\])', text, re.DOTALL)
        if match:
            return json.loads(match.group(1))
        return json.loads(text)
    except:
        return {}

def flatten_ai_val(val):
    if isinstance(val, dict):
        return " ".join([str(v) for v in val.values()])
    elif isinstance(val, list):
        return ", ".join([str(v) for v in val])
    return str(val)

def style_plotly_dark(fig):
    import plotly.graph_objects as go
    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(family="JetBrains Mono", color="#7b8db5", size=10),
        margin=dict(l=16, r=16, t=36, b=16),
        xaxis=dict(showgrid=False, zeroline=False,
                   tickfont=dict(family="JetBrains Mono", size=10, color="#3b4a6b")),
        yaxis=dict(gridcolor="#1c2540", zeroline=False,
                   tickfont=dict(family="JetBrains Mono", size=10, color="#3b4a6b")),
        legend=dict(font=dict(color="#dce4f5", family="JetBrains Mono", size=10),
                    bgcolor="rgba(0,0,0,0)", bordercolor="rgba(0,0,0,0)"),
        hoverlabel=dict(bgcolor="#0f1520", font_color="#dce4f5",
                        font_family="JetBrains Mono", font_size=11,
                        bordercolor="#243055"),
    )
    return fig
