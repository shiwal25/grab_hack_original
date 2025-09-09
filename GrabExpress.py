import os
import asyncio
import json
import threading
import random
from dotenv import load_dotenv
from langchain.agents import initialize_agent, AgentType, Tool
from langchain_google_genai import GoogleGenerativeAI
import aiohttp
import warnings
from langchain.callbacks.base import AsyncCallbackHandler

warnings.filterwarnings("ignore", category=DeprecationWarning)

load_dotenv()
Google_api = os.getenv("GOOGLE_API_KEY")
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
curr_lat = None
curr_lng = None

_prompt_target = "driver"

class WebsocketCallbackHandler(AsyncCallbackHandler):
    async def on_chain_start(self, serialized, inputs, **kwargs):
        try:
            print(json.dumps({"type": "agent_event", "event": "chain_start", "inputs": inputs}), flush=True)
        except Exception:
            pass

    async def on_chain_end(self, outputs, **kwargs):
        try:
            print(json.dumps({"type": "agent_event", "event": "chain_end", "outputs": outputs}), flush=True)
        except Exception:
            pass

    async def on_agent_action(self, action, **kwargs):
        try:
            tool = getattr(action, "tool", str(action))
            tool_input = getattr(action, "tool_input", "")
            log = getattr(action, "log", "")
            print(json.dumps({"type": "agent_event", "event": "agent_action", "tool": tool, "tool_input": tool_input, "log": str(log)}), flush=True)
        except Exception:
            pass

    async def on_agent_finish(self, finish, **kwargs):
        try:
            rv = getattr(finish, "return_values", finish)
            print(json.dumps({"type": "agent_event", "event": "agent_finish", "result": rv}), flush=True)
        except Exception:
            pass

    async def on_tool_start(self, serialized, input_str, **kwargs):
        try:
            name = serialized.get("name") if isinstance(serialized, dict) else str(serialized)
            print(json.dumps({"type": "agent_event", "event": "tool_start", "tool": name, "input": input_str}), flush=True)
        except Exception:
            pass

    async def on_tool_end(self, output, **kwargs):
        try:
            print(json.dumps({"type": "agent_event", "event": "tool_end", "output": output}), flush=True)
        except Exception:
            pass

    async def on_llm_start(self, serialized, prompts, **kwargs):
        try:
            print(json.dumps({"type": "agent_event", "event": "llm_start", "prompts": prompts}), flush=True)
        except Exception:
            pass

    async def on_llm_new_token(self, token, **kwargs):
        try:
            print(json.dumps({"type": "agent_event", "event": "llm_token", "token": token}), flush=True)
        except Exception:
            pass

    async def on_llm_end(self, response, **kwargs):
        try:
            print(json.dumps({"type": "agent_event", "event": "llm_end", "response": response}), flush=True)
        except Exception:
            pass

async def addresstolanglat(address: str) -> tuple[float, float]:
    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={address.replace(' ', '+')}&key={GOOGLE_MAPS_API_KEY}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            result = await response.json()
            if result['status'] == 'OK' and result['results']:
                loc = result['results'][0]['geometry']['location']
                return loc['lat'], loc['lng']
            else:
                raise ValueError(f"Unable to convert address to lat/lng. Status: {result.get('status', 'UNKNOWN')} - {result.get('error_message', '')}")

async def calculate_distance_google(orig_lat: float, orig_lng: float, dest_lat: float, dest_lng: float) -> float:
    url = f"https://maps.googleapis.com/maps/api/distancematrix/json?origins={orig_lat},{orig_lng}&destinations={dest_lat},{dest_lng}&key={GOOGLE_MAPS_API_KEY}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            result = await response.json()
            if result['status'] == 'OK':
                rows = result.get("rows", [])
                if rows and "elements" in rows[0] and rows[0]["elements"][0]["status"] == "OK":
                    distance_m = rows[0]["elements"][0]["distance"]["value"]
                    return distance_m / 1000.0
            raise ValueError("Failed to fetch distance from Google Maps API")

async def find_nearby_lockers(lat: float, lng: float, radius: int = 2000, allow_safe_drop_retry: bool = True) -> list[dict]:
    url = f"https://maps.googleapis.com/maps/api/place/nearbysearch/json?location={lat},{lng}&radius={radius}&keyword=parcel+locker&key={GOOGLE_MAPS_API_KEY}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            result = await response.json()
            if result['status'] == 'OK':
                print(json.dumps({"type": "info", "message": f"Found {len(result.get('results', []))} lockers within {radius} meters."}), flush=True)
                return [{'name': r['name'], 'address': r['vicinity']} for r in result.get('results', [])][:5]
            else:
                r = radius
                if r > 16000:
                    print(json.dumps({"type": "info", "message": "No lockers found within 16 km radius."}), flush=True)
                    if allow_safe_drop_retry:
                        return await find_nearby_lockers(lat, lng, 2000, allow_safe_drop_retry=False)
                    else:
                        return []
                else:
                    await asyncio.sleep(3)
                    return await find_nearby_lockers(lat, lng, r * 2, allow_safe_drop_retry)

async def request_user_input(prompt: str, timeout: int = 150) -> str:
    global _prompt_target
    print(json.dumps({"type": "request_user_input", "prompt": prompt, "timeout": timeout, "target": _prompt_target}), flush=True)
    import sys
    for line in sys.stdin:
        try:
            data = json.loads(line.strip())
            if "input" in data:
                return data["input"].strip()
        except Exception:
            continue
    return ""

async def contact_recipient_via_chat(message: str) -> str:
    global user_input, recipient_reply, _prompt_target
    print(json.dumps({"type": "info", "message": message, "target": "recipient"}), flush=True)

    recipient_reply = ""
    _prompt_target = "recipient"
    reply = (await input_with_timeout(
        message + " [150s timeout]:> ",
        150
    )).strip()
    _prompt_target = "driver"

    recipient_reply = reply
    if not recipient_reply:
        recipient_reply = "Recipient is not replying"

    return recipient_reply

async def perform_safe_drop_off_nearby(_input: str = "") -> str:
    name = await contact_recipient_via_chat("Please provide the name of the neighbor or guard I can leave the package with:")
    if name == "Recipient is not replying":
        return "Recipient did not respond. Cannot proceed with safe drop-off nearby."

    phone = ""
    while True:
        phone = await contact_recipient_via_chat("Please provide the 10-digit phone number of that person:")
        if phone == "Recipient is not replying":
            return "Recipient did not respond. Cannot proceed with safe drop-off nearby."
        if phone.isdigit() and len(phone) == 10:
            break
        else:
            print(json.dumps({"type": "info", "message": "Invalid phone number. Please enter a valid 10-digit number."}), flush=True)

    for i in range(3):
        otp = str(random.randint(1000, 9999))
        otp_message = f"An OTP has been sent to the provided phone number. Please enter the 4-digit OTP. 30 Sec time limit"
        print(json.dumps({"type": "info", "message": f"DEBUG: OTP for this attempt is {otp}"}), flush=True)
        otp_input = await request_user_input(f"{otp_message}> ", 30)

        if otp_input == otp:
            success_msg = f"Your parcel has been safely delivered to {name} (phone: {phone}). Thank you!"
            print(json.dumps({"type": "info", "message": success_msg}), flush=True)
            return "Safe drop-off nearby successful."
        elif otp_input.lower() == 'regenerate':
            print(json.dumps({"type": "info", "message": "Generating a new OTP..."}), flush=True)
        elif not otp_input:
            print(json.dumps({"type": "info", "message": "No response received within the time limit. Retrying..."}), flush=True)
        else:
            print(json.dumps({"type": "info", "message": "Invalid OTP. Retrying..."}), flush=True)

    print(json.dumps({"type": "info", "message": "OTP verification failed after multiple attempts. The safe drop-off nearby has been canceled."}), flush=True)
    return "OTP verification failed. Please try another method."

async def perform_safe_drop_off(_input: str = "") -> str:
    attempts = 0
    while attempts < 3:
        name = await contact_recipient_via_chat("Please provide the name of the person I can leave the package with:")
        if name == "Recipient is not replying":
            return "Recipient did not respond. Cannot proceed with safe drop-off."

        phone = ""
        while True:
            phone = await contact_recipient_via_chat("Please provide the 10-digit phone number of that person:")
            if phone == "Recipient is not replying":
                return "Recipient did not respond. Cannot proceed with safe drop-off."
            if phone.isdigit() and len(phone) == 10:
                break
            else:
                print(json.dumps({"type": "info", "message": "Invalid phone number. Please enter a valid 10-digit number."}), flush=True)

        location = await contact_recipient_via_chat("Please provide the address for the safe drop-off (must be within 2 km):")
        if location == "Recipient is not replying":
            return "Recipient did not respond. Cannot proceed with safe drop-off."

        try:
            drop_lat, drop_lng = await addresstolanglat(location)
            dist = await calculate_distance_google(curr_lat, curr_lng, drop_lat, drop_lng)
            if dist > 2:
                print(json.dumps({"type": "info", "message": f"The location is {dist:.2f} km away, which exceeds 2 km. Try again."}), flush=True)
                attempts += 1
                continue

            print(json.dumps({"type": "info", "message": f"The safe drop-off address provided is under 2 km. Distance: {dist:.2f} km from current location."}), flush=True)

            for i in range(3):
                otp = str(random.randint(1000, 9999))
                otp_message = f"An OTP has been sent to the provided phone number. Please enter the 4-digit OTP. 30 Sec time limit"
                print(json.dumps({"type": "info", "message": f"DEBUG: OTP for this attempt is {otp}"}), flush=True)
                otp_input = await request_user_input(f"{otp_message}> ", 30)

                if otp_input == otp:
                    success_msg = f"Your parcel has been safely delivered to {location} with {name} (phone: {phone}). Thank you!"
                    print(json.dumps({"type": "info", "message": success_msg}), flush=True)
                    return "Safe drop-off successful."
                elif otp_input.lower() == 'regenerate':
                    print(json.dumps({"type": "info", "message": "Generating a new OTP..."}), flush=True)
                elif not otp_input:
                    print(json.dumps({"type": "info", "message": "No response received within the time limit. Retrying..."}), flush=True)
                else:
                    print(json.dumps({"type": "info", "message": "Invalid OTP. Retrying..."}), flush=True)

            print(json.dumps({"type": "info", "message": "OTP verification failed after multiple attempts. The safe drop-off has been canceled."}), flush=True)
            return "OTP verification failed. Please try another method."
        except ValueError as e:
            print(json.dumps({"type": "error", "message": str(e)}), flush=True)
            return "Failed to validate the drop-off location."

    return "Safe drop-off attempts exceeded. Moving to next option."

async def perform_locker_delivery(_input: str = "") -> str:
    lockers = await find_nearby_lockers(curr_lat, curr_lng)
    if not lockers:
        print(json.dumps({"type": "info", "message": "No nearby parcel lockers found."}), flush=True)
        return "No lockers available."

    list_msg = "Found nearby secure parcel lockers:" + "".join(f"{i+1}. {locker['name']} at {locker['address']}" for i, locker in enumerate(lockers))
    select = await contact_recipient_via_chat(list_msg + "Please select one by entering the number:")

    if select == "Recipient is not replying":
        print(json.dumps({"type": "info", "message": "Recipient did not respond."}), flush=True)
        return "No response from recipient."

    try:
        num = int(select) - 1
        if 0 <= num < len(lockers):
            selected = lockers[num]
            pin = random.randint(10, 99)
            otp = random.randint(1000, 9999)
            success_msg = f"I am done with the delivery to {selected['name']} at {selected['address']}. Your 2-digit Locker No. is {pin}, and your 4-digit PIN is {otp}."
            print(json.dumps({"type": "info", "message": success_msg}), flush=True)
            return "Locker delivery successful."
        else:
            print(json.dumps({"type": "info", "message": "Invalid selection."}), flush=True)
            return "Invalid locker selection."
    except ValueError:
        print(json.dumps({"type": "info", "message": "Invalid input."}), flush=True)
        return "Invalid input for selection."

async def return_parcel(_input: str = "") -> str:
    msg = "Sadly, we are returning the parcel."
    print(json.dumps({"type": "info", "message": msg}), flush=True)
    return "Parcel return initiated."

def setup_agent():
    if not Google_api:
        raise ValueError("GOOGLE_API_KEY not found in env file")

    if not GOOGLE_MAPS_API_KEY:
        raise ValueError("GOOGLE_MAPS_API_KEY not found in env file")

    llm = GoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)
    tools = [
        Tool(
            name="contact_recipient_via_chat",
            func=contact_recipient_via_chat,
            coroutine=contact_recipient_via_chat,
            description="Useful for sending any message to the recipient and getting their reply."
        ),
        Tool(
            name="perform_safe_drop_off_nearby",
            func=perform_safe_drop_off_nearby,
            coroutine=perform_safe_drop_off_nearby,
            description="Safe drop-off with a neighbor or guard at the same location. Includes phone number and OTP verification."
        ),
        Tool(
            name="perform_safe_drop_off",
            func=perform_safe_drop_off,
            coroutine=perform_safe_drop_off,
            description="Safe drop-off at a recipient-provided location (within 2 km). Includes phone number and OTP verification."
        ),
        Tool(
            name="perform_locker_delivery",
            func=perform_locker_delivery,
            coroutine=perform_locker_delivery,
            description="Delivery to a nearby locker with PIN and Locker No. generation."
        ),
        Tool(
            name="return_parcel",
            func=return_parcel,
            coroutine=return_parcel,
            description="Return the parcel as a last resort."
        )
    ]

    agent = initialize_agent(
        tools,
        llm,
        agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
        verbose=True,
        callbacks=[WebsocketCallbackHandler()]
    )

    return agent

async def enhance_userinput(user_input: str) -> str:
    prompt = (
        f"You are a prompt engineer for a delivery agent. A delivery partner has a valuable package, "
        f"but the recipient is unavailable. The delivery partner describes the situation as: "
        f"'{user_input}'. "
        f"Your task is to generate a polite initial message to send to the recipient, informing them of the situation "
        f"and asking for permission to leave the parcel with a neighbor or security guard. End the message with: 'Can I leave it with a neighbor or a security guard? Please reply with Yes or No.' "
        f"The message should be clear and direct."
    )

    chatHistory = [{"role": "user", "parts": [{"text": prompt}]}]
    payload = {"contents": chatHistory}

    apiKey = Google_api
    apiUrl = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-05-20:generateContent?key={apiKey}"

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(apiUrl, headers={'Content-Type': 'application/json'}, data=json.dumps(payload)) as response:
                result = await response.json()
                if result.get('candidates') and len(result['candidates']) > 0 and 'parts' in result['candidates'][0]['content']:
                    return result['candidates'][0]['content']['parts'][0]['text']
                else:
                    print(json.dumps({"type": "info", "message": "API call failed, using default prompt."}), flush=True)
                    return (
                        f"I have arrived at your location with your valuable package, but you are unavailable. "
                        f"The situation is: '{user_input}'. "
                        f"Can I leave it with a neighbor or a security guard? Please reply with Yes or No."
                    )
        except Exception as e:
            print(json.dumps({"type": "error", "message": f"An error occurred during API call: {e}"}), flush=True)
            return (
                f"I have arrived at your location with your valuable package, but you are unavailable. "
                f"The situation is: '{user_input}'. "
                f"Can I leave it with a neighbor or a security guard? Please reply with Yes or No."
            )

async def input_with_timeout(prompt, timeout=150):
    global _prompt_target
    print(json.dumps({"type": "request_user_input", "prompt": prompt, "timeout": timeout, "target": _prompt_target}), flush=True)
    loop = asyncio.get_event_loop()
    future_input = loop.create_future()

    def read_stdin():
        for line in sys.stdin:
            try:
                data = json.loads(line.strip())
                if "input" in data:
                    if not future_input.done():
                        loop.call_soon_threadsafe(future_input.set_result, data["input"])
                    break
            except Exception:
                continue

    import sys
    thread = threading.Thread(target=read_stdin, daemon=True)
    thread.start()

    try:
        user_input = await asyncio.wait_for(future_input, timeout=timeout)
        return user_input.strip()
    except asyncio.TimeoutError:
        return ""

async def run_grabexpress_flow():
    global curr_lat, curr_lng, _prompt_target
    _prompt_target = "driver"
    current_location = await input_with_timeout("Delivery Agent, enter your current address for location services :", 300)
    try:
        curr_lat, curr_lng = await addresstolanglat(current_location)
    except ValueError as e:
        print(json.dumps({"type": "error", "message": f"Geocoding failed: {e} "}), flush=True)
        curr_lat, curr_lng = 40.7128, -74.0060

    delivery_agent = setup_agent()

    initial_message = await enhance_userinput("Recipient is unavailable.")

    agent_goal = f"""Handle the delivery for an unavailable recipient by strictly following this flow:
    1. Initiate contact with the recipient using the initial message: '{initial_message}'
    2. Evaluate their response:
        - If affirmative ('Yes'), proceed with perform_safe_drop_off_nearby.
        - If negative ('No'), contact the recipient asking: 'Would you like me to drop off the parcel at another safe location (within 2 km)? Please reply with Yes or No.'
    3. If affirmative, proceed with perform_safe_drop_off.
    4. If negative, contact the recipient asking: 'Would you like me to drop off the parcel at a nearby secure locker instead? Please reply with Yes or No.'
    5. Based on the locker response:
        - If affirmative, proceed with perform_locker_delivery.
        - If negative, use return_parcel.
    If the recipient does not reply at any step, assume a negative response and move to the next step."""

    await delivery_agent.arun(agent_goal)

async def run_grabexpress_flow_entry():
    await run_grabexpress_flow()
