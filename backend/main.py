import asyncio
import re

import uvicorn
from fastapi import FastAPI
from groq import Groq
from pydantic import BaseModel

from config import GROQ_API_KEY
from tools import call_emergency, find_nearby_therapists_by_location

CHAT_MODEL = "openai/gpt-oss-20b"

app = FastAPI()
client = Groq(api_key=GROQ_API_KEY, timeout=12, max_retries=0)


@app.get("/")
async def root():
    return {"status": "ok"}


class ChatMessage(BaseModel):
    role: str
    content: str


class Query(BaseModel):
    message: str
    history: list[ChatMessage] = []


SYSTEM_PROMPT = """
You are SafeSpace, a warm, emotionally intelligent companion for supportive conversation.
Your job is to feel like a kind friend who is easy to talk to, while still being responsible around mental health.

Style:
- Sound natural, gentle, and conversational, like ChatGPT with more warmth.
- Usually write 2 to 5 short paragraphs when the user shares feelings, asks for help, or wants to talk.
- For casual messages, match their vibe and be relaxed, but still give a real answer.
- Do not keep repeating the same line.
- Ask one thoughtful follow-up question when it would help the conversation continue.
- Use simple language. Avoid clinical labels unless the user asks.

Safety:
- You are not a replacement for a licensed therapist.
- If the user may be in immediate danger, encourage emergency help and staying with someone safe.
"""


def is_crisis(message: str) -> bool:
    lower_message = message.lower()
    crisis_terms = [
        "suicide",
        "kill myself",
        "end my life",
        "self-harm",
        "hurt myself",
        "can't go on",
        "want to die",
    ]
    return any(term in lower_message for term in crisis_terms)


def is_therapist_search(message: str) -> bool:
    lower_message = message.lower()
    return "therapist" in lower_message or "psychologist" in lower_message or "counselor" in lower_message


def extract_location(message: str) -> str:
    match = re.search(r"\b(?:in|near|around)\s+([a-zA-Z0-9 ,.-]+)", message, re.IGNORECASE)
    if match:
        return match.group(1).strip(" .")
    return message.strip()


def build_messages(message: str, history: list[ChatMessage]) -> list[dict[str, str]]:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    for item in history[-10:]:
        if item.role in {"user", "assistant"} and item.content.strip():
            messages.append({"role": item.role, "content": item.content.strip()})

    messages.append({"role": "user", "content": message})
    return messages


def generate_groq_reply(message: str, history: list[ChatMessage]) -> str:
    completion = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=build_messages(message, history),
        temperature=0.85,
        max_tokens=420,
    )
    return completion.choices[0].message.content.strip()


def crisis_response() -> str:
    return (
        "I am really glad you told me. If you might act on those thoughts right now, call emergency services "
        "or go to the nearest ER now. If you are in the U.S. or Canada, call or text 988.\n\n"
        "If you can, move near another person right now and send me just one word: safe, unsure, or in danger."
    )


def fallback_response(message: str) -> str:
    if not message.strip():
        return "Tell me what is on your mind. I am here with you."

    return (
        "I am here with you. My AI connection is being a little slow right now, but you do not have to sit "
        "with this alone.\n\nTell me what happened or what you are feeling, and I will stay with you through it."
    )


@app.post("/ask")
async def ask(query: Query):
    message = query.message.strip()

    if is_crisis(message):
        try:
            await asyncio.to_thread(call_emergency)
        except Exception:
            pass
        return {"response": crisis_response(), "tool_called": "emergency_call_tool"}

    if is_therapist_search(message):
        try:
            location = extract_location(message)
            therapist_result = await asyncio.to_thread(find_nearby_therapists_by_location, location)
            return {"response": therapist_result, "tool_called": "find_nearby_therapists_by_location"}
        except Exception:
            pass

    try:
        response_text = await asyncio.wait_for(
            asyncio.to_thread(generate_groq_reply, message, query.history),
            timeout=10,
        )
        return {"response": response_text, "tool_called": CHAT_MODEL}
    except Exception:
        return {"response": fallback_response(message), "tool_called": "fallback"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
