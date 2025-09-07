# main.py
import os
import sys
import json
import time
import random
import asyncio
import threading
from queue import Queue, Empty
from typing import Tuple, List, Dict, Any

import aiohttp  # for Google APIs
from dotenv import load_dotenv

# LangChain (no langchain_community required)
from langchain.agents import initialize_agent, AgentType, Tool
from langchain_google_genai import GoogleGenerativeAI

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "")

# ------------ JSON emitter (no prints) ------------
def emit(event_type: str, **payload: Any) -> None:
    msg = {"type": event_type, **payload}
    sys.stdout.write(json.dumps(msg) + "\n")
    sys.stdout.flush()

def emit_info(message: str) -> None:
    emit("info", message=message)

def emit_error(message: str) -> None:
    emit("error", message=message)

def emit_prompt(message: str) -> None:
    emit("prompt", message=message)

def emit_message(role: str, content: str) -> None:
    emit("message", role=role, content=content)

def emit_tool_event(phase: str, name: str, input_: Any = None, output: Any = None) -> None:
    payload = {"phase": phase, "name": name}
    if input_ is not None:
        payload["input"] = input_
    if output is not None:
        payload["output"] = output
    emit("tool", **payload)

# ------------ stdin queue for replies -------------
input_queue: "Queue[str]" = Queue()

def _stdin_reader():
    for line in sys.stdin:
        if not line:
            continue
        input_queue.put(line)

reader_thread = threading.Thread(target=_stdin_reader, daemon=True)
reader_thread.start()

def blocking_user_input(timeout: float | None = None) -> str:
    """
    Wait for the frontend to send { input: "..." } via stdin.
    Returns a clean string, or "" on timeout.
    """
    try:
        raw = input_queue.get(timeout=timeout)
    except Empty:
        return ""
    raw = raw.strip()
    try:
        obj = json.loads(raw)
        return str(obj.get("input", "")).strip()
    except Exception:
        return raw

# ------------ Google helpers (async) -------------
async def geocode_address(address: str) -> Tuple[float, float]:
    url = (
        "https://maps.googleapis.com/maps/api/geocode/json"
        f"?address={address.replace(' ', '+')}&key={GOOGLE_MAPS_API_KEY}"
    )
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            data = await resp.json()
            if data.get("status") == "OK" and data.get("results"):
                loc = data["results"][0]["geometry"]["location"]
                return float(loc["lat"]), float(loc["lng"])
            raise ValueError(f"Geocoding failed: {data.get('status')} {data.get('error_message','')}")

async def google_distance_km(orig_lat: float, orig_lng: float, dest_lat: float, dest_lng: float) -> float:
    url = (
        "https://maps.googleapis.com/maps/api/distancematrix/json"
        f"?origins={orig_lat},{orig_lng}&destinations={dest_lat},{dest_lng}&key={GOOGLE_MAPS_API_KEY}"
    )
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            data = await resp.json()
            if data.get("status") == "OK":
                rows = data.get("rows", [])
                if rows and rows[0].get("elements") and rows[0]["elements"][0].get("status") == "OK":
                    meters = rows[0]["elements"][0]["distance"]["value"]
                    return meters / 1000.0
    raise ValueError("Distance API failed")

async def places_nearby_lockers(lat: float, lng: float, radius: int = 2000) -> List[Dict[str, str]]:
    url = (
        "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
        f"?location={lat},{lng}&radius={radius}&keyword=parcel+locker&key={GOOGLE_MAPS_API_KEY}"
    )
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            data = await resp.json()
            if data.get("status") == "OK":
                results = data.get("results", [])[:5]
                return [{"name": r.get("name", ""), "address": r.get("vicinity", "")} for r in results]
            return []

# ------------ Conversation tools (SYNC wrappers) -------------
# Globals set during boot
CURR_LAT: float | None = None
CURR_LNG: float | None = None

def tool_contact_recipient_via_chat(message: str) -> str:
    """
    Sync tool: emits a message and waits for user's reply from Socket.IO (stdin).
    """
    emit_message("agent", message)
    emit_prompt("Enter your reply for the delivery agent [150s timeout]:")
    reply = blocking_user_input(timeout=150)
    if not reply:
        return "Recipient is not replying"
    return reply

def tool_perform_safe_drop_off(_: str = "") -> str:
    """
    Sync tool: safe drop-off at user-specified nearby location (<= 2 km), with OTP.
    """
    emit_tool_event("start", "perform_safe_drop_off")

    name = tool_contact_recipient_via_chat(
        "Please provide the name of the person I can leave the package with:"
    )
    if name == "Recipient is not replying":
        emit_tool_event("end", "perform_safe_drop_off", output="Recipient did not respond.")
        return "Recipient did not respond. Cannot proceed with safe drop-off."

    # Phone loop
    while True:
        phone = tool_contact_recipient_via_chat(
            "Please provide the 10-digit phone number of that person:"
        )
        if phone == "Recipient is not replying":
            emit_tool_event("end", "perform_safe_drop_off", output="Recipient did not respond.")
            return "Recipient did not respond. Cannot proceed with safe drop-off."
        if phone.isdigit() and len(phone) == 10:
            break
        emit_info("Invalid phone number, please enter a valid 10-digit number.")

    # Ask for address and validate <=2 km
    location = tool_contact_recipient_via_chat(
        "Please provide the address for the safe drop-off (must be within 2 km):"
    )
    if location == "Recipient is not replying":
        emit_tool_event("end", "perform_safe_drop_off", output="No reply for address.")
        return "Recipient did not respond. Cannot proceed with safe drop-off."

    try:
        drop_lat, drop_lng = asyncio.run(geocode_address(location))
        dist_km = asyncio.run(google_distance_km(CURR_LAT, CURR_LNG, drop_lat, drop_lng))
        if dist_km > 2.0:
            emit_info(f"Provided location is {dist_km:.2f} km away (>2 km). Cancelling safe drop-off.")
            emit_tool_event("end", "perform_safe_drop_off", output="Too far")
            return "Safe drop-off location exceeds 2 km. Please choose another method."
    except Exception as e:
        emit_error(f"Failed to validate safe drop address: {e}")
        emit_tool_event("end", "perform_safe_drop_off", output="Address validation failed")
        return "Failed to validate the drop-off location."

    # OTP flow
    for _ in range(3):
        otp = str(random.randint(1000, 9999))
        emit_info("Sending 4-digit OTP to the provided number.")
        emit("debug", message=f"DEBUG OTP (for testing): {otp}")
        emit_prompt("Please enter the 4-digit OTP (or type 'regenerate'). [30s timeout]")
        user_otp = blocking_user_input(timeout=30)
        if not user_otp:
            emit_info("No response received within the time limit. Retrying...")
            continue
        if user_otp.lower().strip() == "regenerate":
            emit_info("Generating a new OTP...")
            continue
        if user_otp == otp:
            success_msg = f"Your parcel has been safely delivered to {location} with {name} (phone: {phone}). Thank you!"
            emit("success", message=success_msg)
            emit_tool_event("end", "perform_safe_drop_off", output="Safe drop-off successful.")
            return "Safe drop-off successful."
        emit_info("Invalid OTP. Retrying...")

    emit_error("OTP verification failed after multiple attempts.")
    emit_tool_event("end", "perform_safe_drop_off", output="OTP failed")
    return "OTP verification failed. Please try another method."

def tool_perform_locker_delivery(_: str = "") -> str:
    emit_tool_event("start", "perform_locker_delivery")
    try:
        lockers = asyncio.run(places_nearby_lockers(CURR_LAT, CURR_LNG, 2000))
    except Exception as e:
        emit_error(f"Locker lookup failed: {e}")
        emit_tool_event("end", "perform_locker_delivery", output="Lookup failed")
        return "No lockers available."

    if not lockers:
        emit_info("No nearby parcel lockers found.")
        emit_tool_event("end", "perform_locker_delivery", output="0 lockers")
        return "No lockers available."

    listing = "Found nearby secure parcel lockers:\n" + "\n".join(
        f"{i+1}. {l['name']} at {l['address']}" for i, l in enumerate(lockers)
    )
    choice = tool_contact_recipient_via_chat(
        listing + "\nPlease select one by entering the number:"
    )
    if choice == "Recipient is not replying":
        emit_info("Recipient did not respond for locker choice.")
        emit_tool_event("end", "perform_locker_delivery", output="No reply")
        return "No response from recipient."

    try:
        idx = int(choice) - 1
        if 0 <= idx < len(lockers):
            selected = lockers[idx]
            locker_no = random.randint(10, 99)
            pin = random.randint(1000, 9999)
            success_msg = (
                f"Delivered to {selected['name']} at {selected['address']}. "
                f"Locker No: {locker_no}, PIN: {pin}."
            )
            emit("success", message=success_msg)
            emit_tool_event("end", "perform_locker_delivery", output="Locker delivery successful.")
            return "Locker delivery successful."
        emit_error("Invalid locker selection index.")
        emit_tool_event("end", "perform_locker_delivery", output="Invalid selection")
        return "Invalid locker selection."
    except ValueError:
        emit_error("Locker selection input was not a number.")
        emit_tool_event("end", "perform_locker_delivery", output="Invalid input")
        return "Invalid input for selection."

def tool_return_parcel(_: str = "") -> str:
    emit_info("Sadly, we are returning the parcel.")
    emit_tool_event("end", "return_parcel", output="Return initiated")
    return "Parcel return initiated."

# ------------ LLM helpers -------------
async def initial_message_from_situation(situation: str) -> str:
    """
    Generate a polite initial message to the recipient.
    Falls back to a default if API fails.
    """
    if not GOOGLE_API_KEY:
        return (
            f"I've arrived with your package, but you're unavailable. "
            f"Situation: '{situation}'. Can I leave it with a neighbor or a security guard? Please reply Yes or No."
        )

    try:
        # Use LangChain wrapper to keep deps simple
        llm = GoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=GOOGLE_API_KEY, temperature=0)
        prompt = (
            "You are a delivery agent writing the first polite message to the recipient. "
            f"The situation is: '{situation}'. "
            "Ask for permission to leave the parcel with a neighbor or the security guard. "
            "End with: 'Can I leave it with a neighbor or a security guard? Please reply with Yes or No.'"
        )
        text = await llm.ainvoke(prompt)
        return (text or "").strip() or (
            f"I've arrived with your package, but you're unavailable. "
            f"Situation: '{situation}'. Can I leave it with a neighbor or a security guard? Please reply Yes or No."
        )
    except Exception as e:
        emit_error(f"Initial message generation failed: {e}")
        return (
            f"I've arrived with your package, but you're unavailable. "
            f"Situation: '{situation}'. Can I leave it with a neighbor or a security guard? Please reply Yes or No."
        )

# ------------ Agent runner -------------
def run_agent() -> None:
    user_id = os.getenv("USER_ID", "")
    location = os.getenv("LOCATION", "")
    situation = os.getenv("SITUATION", "")

    if not situation or not location:
        emit_error("SITUATION and LOCATION must be provided via environment.")
        return

    # Compute current lat/lng
    global CURR_LAT, CURR_LNG
    try:
        CURR_LAT, CURR_LNG = asyncio.run(geocode_address(location))
    except Exception as e:
        emit_error(f"Geocoding failed; using default NYC. Error: {e}")
        CURR_LAT, CURR_LNG = 40.7128, -74.0060

    # Build LLM and tools (SYNC funcs so Tool works)
    if not GOOGLE_API_KEY:
        emit_error("GOOGLE_API_KEY is missing. LLM will not run.")
        return

    llm = GoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=GOOGLE_API_KEY, temperature=0)

    tools = [
        Tool(
            name="contact_recipient_via_chat",
            func=tool_contact_recipient_via_chat,
            description="Send a message to the recipient and get their reply. Input is the message string."
        ),
        Tool(
            name="perform_safe_drop_off",
            func=tool_perform_safe_drop_off,
            description="Arrange safe drop-off at recipient-provided location (<=2 km), with phone & OTP verification."
        ),
        Tool(
            name="perform_locker_delivery",
            func=tool_perform_locker_delivery,
            description="Deliver to a nearby secure locker (within ~2 km), then provide Locker No. and PIN."
        ),
        Tool(
            name="return_parcel",
            func=tool_return_parcel,
            description="Return the parcel as last resort."
        ),
    ]

    agent = initialize_agent(
        tools,
        llm,
        agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
        verbose=False  # keep stdout clean (JSON-only from us)
    )

    # Generate first message and assemble the plan
    init_msg = asyncio.run(initial_message_from_situation(situation))

    goal = f"""
Handle the delivery for an unavailable recipient by following this flow:

1) Use contact_recipient_via_chat with this initial message: '{init_msg}'
2) If recipient responds 'Yes', proceed with perform_safe_drop_off.
3) If 'No' or no reply, ask: "Would you like me to drop off the parcel at a nearby secure locker instead? Yes or No."
   - If 'Yes', use perform_locker_delivery.
   - Otherwise, use return_parcel.

At each step, only use the tools above to communicate and act. Do not assume user responses—wait for them via contact_recipient_via_chat.
"""

    emit("session_start", user_id=user_id, location=location, situation=situation)
    try:
        # Run synchronously so our tools (which are sync) are compatible
        final_text = agent.run(goal)
        emit("final", message=str(final_text))
    except Exception as e:
        emit_error(f"Agent run failed: {e}")
    finally:
        emit("session_done")

if __name__ == "__main__":
    run_agent()
