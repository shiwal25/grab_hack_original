import os
import asyncio
import json
from dotenv import load_dotenv
from langchain.agents import initialize_agent, AgentType, Tool
from langchain_google_genai import GoogleGenerativeAI
import aiohttp
import threading
import random
from math import radians, sin, cos, sqrt, atan2
import warnings

warnings.filterwarnings("ignore", category=DeprecationWarning)

load_dotenv()
Google_api = os.getenv("GOOGLE_API_KEY")
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
user_input = ""
recipient_reply = ""
curr_lat = None
curr_lng = None

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
                print(f"Found {len(result.get('results', []))} lockers within {radius} meters. Please review and select one.")
                return [{'name': r['name'], 'address': r['vicinity']} for r in result.get('results', [])][:5]
            else:
                r = radius
                if r > 16000:
                    print("No lockers found within 16 km radius.")
                    if allow_safe_drop_retry:
                        again = input("Do you want to attempt a safe drop-off instead? Enter Yes or No: ").strip().lower()
                        if again == "yes":
                            for attempt in range(3):
                                result = await perform_safe_drop_off()
                                if "successful" in result:
                                    return []
                        return await find_nearby_lockers(lat, lng, 2000, allow_safe_drop_retry=False)
                    else:
                        return []
                else:
                    await asyncio.sleep(3)
                    return await find_nearby_lockers(lat, lng, r * 2, allow_safe_drop_retry)

async def contact_recipient_via_chat(message: str) -> str:
    global user_input, recipient_reply
    print(f"{message}")

    recipient_reply = ""
    reply = input_with_timeout(
        "\nEnter your reply for the delivery agent  [150s timeout]:\n> ",
        150
    ).strip()
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
            print("Invalid phone number. Please enter a valid 10-digit number.")

    for i in range(3):
        otp = str(random.randint(1000, 9999))
        otp_message = f"An OTP has been sent to the provided phone number. Please enter the 4-digit OTP. 30 Sec time limit"
        print(f"DEBUG: OTP for this attempt is {otp}")
        otp_input = input_with_timeout(f"{otp_message}\n> ", 30).strip()

        if otp_input == otp:
            success_msg = f"Your parcel has been safely delivered to {name} (phone: {phone}). Thank you!"
            print(success_msg)
            return "Safe drop-off nearby successful."
        elif otp_input.lower() == 'regenerate':
            print("Generating a new OTP...")
        elif not otp_input:
            print("No response received within the time limit. Retrying...")
        else:
            print("Invalid OTP. Retrying...")

    print("OTP verification failed after multiple attempts. The safe drop-off nearby has been canceled.")
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
                print("Invalid phone number. Please enter a valid 10-digit number.")

        location = await contact_recipient_via_chat("Please provide the address for the safe drop-off (must be within 2 km):")
        if location == "Recipient is not replying":
            return "Recipient did not respond. Cannot proceed with safe drop-off."

        try:
            drop_lat, drop_lng = await addresstolanglat(location)
            dist = await calculate_distance_google(curr_lat, curr_lng, drop_lat, drop_lng)
            if dist > 2:
                print(f"\nThe location is {dist:.2f} km away, which exceeds 2 km. Try again.")
                attempts += 1
                continue

            print(f"The safe drop-off address provided is under 2 km. Distance: {dist:.2f} km from current location.")

            for i in range(3):
                otp = str(random.randint(1000, 9999))
                otp_message = f"An OTP has been sent to the provided phone number. Please enter the 4-digit OTP. 30 Sec time limit"
                print(f"DEBUG: OTP for this attempt is {otp}")
                otp_input = input_with_timeout(f"{otp_message}\n> ", 30).strip()

                if otp_input == otp:
                    success_msg = f"Your parcel has been safely delivered to {location} with {name} (phone: {phone}). Thank you!"
                    print(success_msg)
                    return "Safe drop-off successful."
                elif otp_input.lower() == 'regenerate':
                    print("Generating a new OTP...")
                elif not otp_input:
                    print("No response received within the time limit. Retrying...")
                else:
                    print("Invalid OTP. Retrying...")

            print("OTP verification failed after multiple attempts. The safe drop-off has been canceled.")
            return "OTP verification failed. Please try another method."
        except ValueError as e:
            print(f"\nError: {str(e)}")
            return "Failed to validate the drop-off location."

    return "Safe drop-off attempts exceeded. Moving to next option."

async def perform_locker_delivery(_input: str = "") -> str:
    lockers = await find_nearby_lockers(curr_lat, curr_lng)
    if not lockers:
        print("No nearby parcel lockers found.")
        return "No lockers available."

    list_msg = "Found nearby secure parcel lockers:\n" + "\n".join(f"{i+1}. {locker['name']} at {locker['address']}" for i, locker in enumerate(lockers))
    select = await contact_recipient_via_chat(list_msg + "\nPlease select one by entering the number:")

    if select == "Recipient is not replying":
        print("\nRecipient did not respond.")
        return "No response from recipient."

    try:
        num = int(select) - 1
        if 0 <= num < len(lockers):
            selected = lockers[num]
            pin = random.randint(10, 99)
            otp = random.randint(1000, 9999)
            success_msg = f"I am done with the delivery to {selected['name']} at {selected['address']}. Your 2-digit Locker No. is {pin}, and your 4-digit PIN is {otp}."
            print(success_msg)
            return "Locker delivery successful."
        else:
            print("Invalid selection.")
            return "Invalid locker selection."
    except ValueError:
        print("Invalid input.")
        return "Invalid input for selection."

async def return_parcel(_input: str = "") -> str:
    msg = "Sadly, we are returning the parcel."
    print(msg)
    return "Parcel return initiated."

def setup_agent():
    if not Google_api:
        raise ValueError("GOOGLE_API_KEY not found in env file")

    if not GOOGLE_MAPS_API_KEY:
        raise ValueError("GOOGLE_MAPS_API_KEY not found in env file")

    llm = GoogleGenerativeAI(model="gemini-1.5-flash", temperature=0)
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
        verbose=True
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
                    print("API call failed, using default prompt.")
                    return (
                        f"I have arrived at your location with your valuable package, but you are unavailable. "
                        f"The situation is: '{user_input}'. "
                        f"Can I leave it with a neighbor or a security guard? Please reply with Yes or No."
                    )
        except Exception as e:
            print(f"An error occurred during API call: {e}")
            return (
                f"I have arrived at your location with your valuable package, but you are unavailable. "
                f"The situation is: '{user_input}'. "
                f"Can I leave it with a neighbor or a security guard? Please reply with Yes or No."
            )

def input_with_timeout(prompt, timeout):
    result = {"reply": ""}
    def get_input():
        result["reply"] = input(prompt)
    thread = threading.Thread(target=get_input)
    thread.daemon = True
    thread.start()
    thread.join(timeout)
    if thread.is_alive():
        return ""
    return result["reply"]

async def run_grabexpress_flow():
    global curr_lat, curr_lng
    current_location = input("Delivery Agent, enter your current address for location services (e.g., 'Lucknow, India'): \n> ")
    try:
        curr_lat, curr_lng = await addresstolanglat(current_location)
    except ValueError as e:
        print(f"Geocoding failed: {e} ")
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
