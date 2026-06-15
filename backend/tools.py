# Step1: Setup Ollama with Medgemma tool
import ollama

def query_medgemma(prompt: str) -> str:
    """
    Calls MedGemma model with a therapist personality profile.
    Returns responses as an empathic mental health professional.
    """
    system_prompt = """You are Dr. Emily Hartman, a warm and experienced clinical psychologist. 
    Respond to patients with:

    1. Emotional attunement ("I can sense how difficult this must be...")
    2. Gentle normalization ("Many people feel this way when...")
    3. Practical guidance ("What sometimes helps is...")
    4. Strengths-focused support ("I notice how you're...")

    Key principles:
    - Never use brackets or labels
    - Blend elements seamlessly
    - Vary sentence structure
    - Use natural transitions
    - Mirror the user's language level
    - Always keep the conversation going by asking open ended questions to dive into the root cause of patients problem
    """
    
    try:
        response = ollama.chat(
            model='alibayram/medgemma:4b',
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            options={
                'num_predict': 350,  # Slightly higher for structured responses
                'temperature': 0.7,  # Balanced creativity/accuracy
                'top_p': 0.9        # For diverse but relevant responses
            }
        )
        return response['message']['content'].strip()
    except Exception as e:
        return f"I'm having technical difficulties, but I want you to know your feelings matter. Please try again shortly."


# Step2: Setup Twilio calling API tool
from twilio.rest import Client
from config import TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER, EMERGENCY_CONTACT

def call_emergency():
    client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    call = client.calls.create(
        to=EMERGENCY_CONTACT,
        from_=TWILIO_FROM_NUMBER,
        url="http://demo.twilio.com/docs/voice.xml"  # Can customize message
    )


# Step3: Setup Location tool
from ddgs import DDGS


def find_nearby_therapists_by_location(location: str) -> str:
    queries = [
        f"site:practo.com psychologist {location}",
        f"site:practo.com therapist {location}",
        f"site:lybrate.com psychologist {location}",
        f"psychologist in {location}",
    ]

    therapists = []
    allowed_domains = [
        "practo.com",
        "lybrate.com",
        "mindvoyage.in",
        "click2pro.com",
    ]

    with DDGS() as ddgs:
        for query in queries:
            results = ddgs.text(query, max_results=10)
            for result in results:
                title = result.get("title", "")
                url = result.get("href", "")
                if not any(domain in url for domain in allowed_domains):
                    continue
                therapists.append({"name": title, "url": url})

    seen = set()
    unique = []
    for therapist in therapists:
        if therapist["url"] not in seen:
            seen.add(therapist["url"])
            unique.append(therapist)

    if not unique:
        return f"No therapist directories found near {location}."

    output = [f"Therapist resources near {location}:\n"]
    for i, therapist in enumerate(unique[:10], 1):
        output.append(f"{i}. {therapist['name']}\nWebsite: {therapist['url']}")

    return "\n\n".join(output)
