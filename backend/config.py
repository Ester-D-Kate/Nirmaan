import os
from dotenv import load_dotenv


load_dotenv()

class Config:

    GROQ_API_KEYS = [
        os.getenv("GROQ_API_KEY"),
        os.getenv("GROQ_API_KEY_ALT_1"),
        os.getenv("GROQ_API_KEY_ALT_2"),
        os.getenv("GROQ_API_KEY_ALT_3"),
        os.getenv("GROQ_API_KEY_ALT_4"),
    ]

    GROQ_API_KEYS = [key for key in GROQ_API_KEYS if key]

    MODEL_NAME = "llama-3.3-70b-versatile"
    

    BACKEND_URL = os.getenv("BACKEND_URL")
    FRONTEND_URL = os.getenv("FRONTEND_URL")


    RUBRIC = {
        "content_structure": {
            "weight": 40,
            "salutation": 5,
            "keyword_presence": 30,
            "flow": 5
        },
        "speech_rate": {
            "weight": 10,
            "ideal_min": 111,
            "ideal_max": 140
        },
        "language_grammar": {
            "weight": 20,
            "grammar": 10,
            "vocabulary": 10
        },
        "clarity": {
            "weight": 15,
            "filler_words": 15
        },
        "engagement": {
            "weight": 15,
            "sentiment": 15
        }
    }


    SPEECH_RATE_THRESHOLDS = {
        "too_fast": 161,
        "fast_min": 141,
        "ideal_min": 111,
        "slow_min": 81
    }

    GRAMMAR_THRESHOLDS = {
        "excellent": 0.9,
        "good": 0.7,
        "average": 0.5,
        "poor": 0.3
    }

    VOCAB_THRESHOLDS = {
        "excellent": 0.9,
        "good": 0.7,
        "average": 0.5,
        "poor": 0.3
    }

    FILLER_THRESHOLDS = {
        "excellent": 3,
        "good": 6,
        "average": 9,
        "poor": 12
    }

    ENGAGEMENT_THRESHOLDS = {
        "excellent": 0.9,
        "good": 0.7,
        "average": 0.5,
        "poor": 0.3
    }


    MUST_HAVE_KEYWORDS = {
        "name": ["name", "myself", "i am"],
        "age": ["age", "years old"],
        "school": ["school", "class", "studying"],
        "family": ["family", "mother", "father", "parents"],
        "hobbies": ["hobby", "hobbies", "interest", "enjoy", "play", "like to"]
    }

    GOOD_TO_HAVE_KEYWORDS = {
        "origin": ["origin", "from", "live"],
        "ambition": ["ambition", "goal", "dream", "become"],
        "fact": ["fact", "unique", "special"],
        "strength": ["strength", "achievement"]
    }

    FILLER_WORDS = [
        "um", "uh", "like", "you know", "so", "actually", "basically",
        "right", "i mean", "well", "kinda", "sort of", "okay", "hmm", "ah"
    ]

    SYSTEM_PROMPT = """You are an expert communication coach evaluating a student's self-introduction transcript.
    Your task is to analyze the text based on specific criteria and return a structured JSON response.
    
    Analyze the following aspects:
    1. **Salutation Level**:
       - "No Salutation" (0 pts)
       - "Normal" (e.g., Hi, Hello) (2 pts)
       - "Good" (e.g., Good Morning, Hello everyone) (4 pts)
       - "Excellent" (e.g., Excited to introduce, Feeling great) (5 pts)
    
    2. **Keyword Presence**:
       Check for the presence of these topics. Return a list of found topics.
       - Must Have: Name, Age, School/Class, Family, Hobbies/Interest.
       - Good to Have: Origin/Location, Ambition/Goal, Fun fact/Unique point, Strengths/Achievements.
    
    3. **Flow**:
       Check if the order is: Salutation -> Basic Details (Name, Age, School) -> Additional Details -> Closing.
       - "Order followed" (5 pts)
       - "Order Not followed" (0 pts)
    
    4. **Engagement/Sentiment**:
       Analyze the tone. Is it Positive (enthusiastic), Neutral, or Negative?
       
    Output strictly in JSON format.
    """
