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

#deprications warnings ko ignore krne k liye 
warnings.filter_settings("ignore", category=DeprecationWarning)

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

async def find_nearby_lockers(lat: float, lng: float, radius: int = 2000) -> list[dict]:
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
                    print("No lockers found within 16 km radius. Do you want to proceed with a safe drop-off or return the parcel?")
                    ans = input("Enter Yes to proceed with safe drop off or No to return the parcel: ").strip().lower()
                    if ans == 'yes':
                        return []
                    else:
                        return []
                else:
                    await asyncio.sleep(3)
                    return await find_nearby_lockers(lat, lng, r * 2)

def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371 
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    distance = R * c
    return distance

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

async def perform_safe_drop_off(_input: str = "") -> str:
    name = await contact_recipient_via_chat("Please provide the name of the person I can leave the package with:")
    if name == "Recipient is not replying":
        return "Recipient did not respond. Cannot proceed with safe drop-off."

    # Loop to get a valid 10-digit phone number
    phone = ""
    while True:
        phone = await contact_recipient_via_chat("Please provide the 10-digit phone number of that person:")
        if phone == "Recipient is not replying":
            return "Recipient did not respond. Cannot proceed with safe drop-off."
        
        # Validate that the phone number is 10 digits and contains only numeric characters
        if phone.isdigit() and len(phone) == 10:
            break
        else:
            print("Invalid phone number. Please enter a valid 10-digit number.")
    
    # Logic for OTP verification with regeneration option
    for i in range(3):
        otp = str(random.randint(1000, 9999))
        otp_message = f"An OTP has been sent to the provided phone number. Please enter the 4-digit OTP. You have 30 seconds to reply."
        
        print(f"DEBUG: OTP for this attempt is {otp}")
        otp_input = input_with_timeout(f"{otp_message}\n> ", 30).strip()
        
        if otp_input == otp:
            success_msg = f"Your parcel has been safely delivered to a neighbor with {name} (phone: {phone}). Thank you!"
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
            pin = random.randint(1000, 9999)
            success_msg = f"I am done with the delivery to {selected['name']} at {selected['address']}. Your 4-digit PIN is {pin}."
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
            description="Useful for sending any message to the recipient and getting their reply. Use this for initial contact, asking permissions, or any questions. Input is the message to send."
        ),
        Tool(
            name="perform_safe_drop_off",
            func=perform_safe_drop_off,
            coroutine=perform_safe_drop_off,
            description="Useful for arranging a safe drop-off with a neighbor or guard. This tool handles phone number and OTP verification. It will return 'Safe drop-off successful.' on success or 'OTP verification failed. Please try another method.' on failure. The agent should use this tool ONLY after the recipient has explicitly agreed to a safe drop-off."
        ),
        Tool(
            name="perform_locker_delivery",
            func=perform_locker_delivery,
            coroutine=perform_locker_delivery,
            description="Useful for handling delivery to a nearby locker. This tool finds lockers under 2 km, presents a list, lets the recipient select, generates a random PIN, and completes delivery. Use this tool only after the recipient has given permission for it."
        ),
        Tool(
            name="return_parcel",
            func=return_parcel,
            coroutine=return_parcel,
            description="Useful as a last resort if the recipient declines all options. This informs the recipient that the parcel is being returned. No input required."
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

async def main():
    global curr_lat, curr_lng
    current_location = input("Delivery Agent, enter your current address for location services (e.g., 'Lucknow, India'): \n> ")
    try:
        curr_lat, curr_lng = await addresstolanglat(current_location)
    except ValueError as e:
        print(f"Geocoding failed: {e} ")
        curr_lat, curr_lng = 40.7128, -74.0060
    
    delivery_agent = setup_agent()
    
    user_input_given = input("Delivery Agent, describe the situation (e.g., 'I am at the door but no one is answering'): \n> ")
    
    global user_input, recipient_reply
    user_input = user_input_given
    recipient_reply = "" 
    
    initial_message = await enhance_userinput(user_input)
    
    agent_goal = f"""Handle the delivery for an unavailable recipient by strictly following this flow:
1. Initiate contact with the recipient using the initial message: '{initial_message}'
2. Evaluate their response to the neighbor/guard option:
    - If affirmative (e.g., 'Yes'), proceed with perform_safe_drop_off.
    - If negative (e.g., 'No'), or if the `perform_safe_drop_off` tool fails, contact the recipient asking: 'Would you like me to drop off the parcel at a nearby secure locker instead? Please reply with Yes or No.'
3. Based on the locker response:
    - If affirmative, proceed with perform_locker_delivery.
    - If negative, use return_parcel.
Use tools only as needed in this sequence. If the recipient does not reply at any step, the agent should assume a negative response and move to the next logical step."""

    await delivery_agent.arun(agent_goal)

if __name__ == "__main__":
    asyncio.run(main())