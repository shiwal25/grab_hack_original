import os
import asyncio
import json
import sys
import aiohttp
import threading
import random
from math import radians, sin, cos, sqrt, atan2
import warnings

# Import langchain and GoogleGenerativeAI at the top
from langchain_google_genai import GoogleGenerativeAI
from langchain.agents import initialize_agent, AgentType, Tool

# Use a queue to handle async input from stdin
# This is a robust way to handle the non-blocking nature of async code with blocking I/O
_input_queue = asyncio.Queue()

# Thread-safe function to put input into the queue
def input_reader():
    for line in sys.stdin:
        _input_queue.put_nowait(line)

# Start a separate thread to read from stdin
input_thread = threading.Thread(target=input_reader)
input_thread.daemon = True
input_thread.start()

# Asynchronous input function to read from the queue
async def async_input(prompt=None, timeout=None):
    if prompt:
        # Use a structured message to be sent to the frontend
        sys.stdout.write(json.dumps({'type': 'prompt', 'message': prompt}) + '\n')
        sys.stdout.flush()
    try:
        # Wait for input with an optional timeout
        line = await asyncio.wait_for(_input_queue.get(), timeout)
        _input_queue.task_done()
        return line.strip()
    except asyncio.TimeoutError:
        return ""

# The rest of your functions are modified to use async_input instead of input()
# and sys.stdout.write(json.dumps()) instead of print()

# Deprecation warnings can be ignored
warnings.filterwarnings("ignore", category=DeprecationWarning)

Google_api = "AIzaSyAJgV5-HrpXydB1X5w6oA07TD7n1nyXZAQ"
GOOGLE_MAPS_API_KEY = "AIzaSyD5S9tQvpls92uiAk8RG3RZc43lIpG2_aA"

# Add a check for API key validity
if not Google_api or "AIza" not in Google_api:
    print("ERROR: GOOGLE_API_KEY is missing or invalid. Please check your .env file and remove any quotes around the key.")
    sys.exit(1)
if not GOOGLE_MAPS_API_KEY or "AIza" not in GOOGLE_MAPS_API_KEY:
    print("ERROR: GOOGLE_MAPS_API_KEY is missing or invalid. Please check your .env file and remove any quotes around the key.")
    sys.exit(1)

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
                sys.stdout.write(json.dumps({'type': 'info', 'message': f"Found {len(result.get('results', []))} lockers within {radius} meters. Please review and select one."}) + '\n')
                sys.stdout.flush()
                return [{'name': r['name'], 'address': r['vicinity']} for r in result.get('results', [])][:5]
            else:
                r = radius
                if r > 16000:
                    sys.stdout.write(json.dumps({'type': 'prompt', 'message': "No lockers found within 16 km radius. Do you want to proceed with a safe drop-off or return the parcel?"}) + '\n')
                    sys.stdout.flush()
                    ans = (await async_input()).strip().lower()
                    if ans == 'yes':
                        return []
                    else:
                        return []
                else:
                    await asyncio.sleep(3)
                    return await find_nearby_lockers(lat, lng, r * 2)

async def contact_recipient_via_chat(message: str) -> str:
    # Use the async_input function with the provided message as a prompt
    sys.stdout.write(json.dumps({'type': 'message', 'role': 'agent', 'content': message}) + '\n')
    sys.stdout.flush()
    
    reply = await async_input("Enter your reply for the delivery agent [150s timeout]:\n> ", 150)
    
    return reply if reply else "Recipient is not replying"

async def perform_safe_drop_off(_input: str = "") -> str:
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
            sys.stdout.write(json.dumps({'type': 'info', 'message': "Invalid phone number. Please enter a valid 10-digit number."}) + '\n')
            sys.stdout.flush()
    
    for i in range(3):
        otp = str(random.randint(1000, 9999))
        otp_message = f"An OTP has been sent to the provided phone number. Please enter the 4-digit OTP. You have 30 seconds to reply."
        
        sys.stdout.write(json.dumps({'type': 'debug', 'message': f"DEBUG: OTP for this attempt is {otp}"}) + '\n')
        sys.stdout.flush()
        
        otp_input = await async_input(f"{otp_message}\n> ", 30)
        
        if otp_input == otp:
            success_msg = f"Your parcel has been safely delivered to a neighbor with {name} (phone: {phone}). Thank you!"
            sys.stdout.write(json.dumps({'type': 'success', 'message': success_msg}) + '\n')
            sys.stdout.flush()
            return "Safe drop-off successful."
        elif otp_input.lower() == 'regenerate':
            sys.stdout.write(json.dumps({'type': 'info', 'message': "Generating a new OTP..."}) + '\n')
            sys.stdout.flush()
        elif not otp_input:
            sys.stdout.write(json.dumps({'type': 'info', 'message': "No response received within the time limit. Retrying..."}) + '\n')
            sys.stdout.flush()
        else:
            sys.stdout.write(json.dumps({'type': 'info', 'message': "Invalid OTP. Retrying..."}) + '\n')
            sys.stdout.flush()
    
    sys.stdout.write(json.dumps({'type': 'error', 'message': "OTP verification failed after multiple attempts. The safe drop-off has been canceled."}) + '\n')
    sys.stdout.flush()
    return "OTP verification failed. Please try another method."

async def perform_locker_delivery(_input: str = "") -> str:
    # Use environment variables passed from Node.js
    curr_lat = float(os.getenv("CURRENT_LAT"))
    curr_lng = float(os.getenv("CURRENT_LNG"))
    
    lockers = await find_nearby_lockers(curr_lat, curr_lng)
    if not lockers:
        sys.stdout.write(json.dumps({'type': 'info', 'message': "No nearby parcel lockers found."}) + '\n')
        sys.stdout.flush()
        return "No lockers available."

    list_msg = "Found nearby secure parcel lockers:\n" + "\n".join(f"{i+1}. {locker['name']} at {locker['address']}" for i, locker in enumerate(lockers))
    select = await contact_recipient_via_chat(list_msg + "\nPlease select one by entering the number:")

    if select == "Recipient is not replying":
        sys.stdout.write(json.dumps({'type': 'info', 'message': "Recipient did not respond."}) + '\n')
        sys.stdout.flush()
        return "No response from recipient."

    try:
        num = int(select) - 1
        if 0 <= num < len(lockers):
            selected = lockers[num]
            pin = random.randint(1000, 9999)
            success_msg = f"I am done with the delivery to {selected['name']} at {selected['address']}. Your 4-digit PIN is {pin}."
            sys.stdout.write(json.dumps({'type': 'success', 'message': success_msg}) + '\n')
            sys.stdout.flush()
            return "Locker delivery successful."
        else:
            sys.stdout.write(json.dumps({'type': 'error', 'message': "Invalid selection."}) + '\n')
            sys.stdout.flush()
            return "Invalid locker selection."
    except ValueError:
        sys.stdout.write(json.dumps({'type': 'error', 'message': "Invalid input."}) + '\n')
        sys.stdout.flush()
        return "Invalid input for selection."

async def return_parcel(_input: str = "") -> str:
    msg = "Sadly, we are returning the parcel."
    sys.stdout.write(json.dumps({'type': 'info', 'message': msg}) + '\n')
    sys.stdout.flush()
    return "Parcel return initiated."
    
# Main function to run the agent
# In delivery_agent.py, replace your run_agent function with this one

async def run_agent():
    # Use environment variables passed from Node.js
    user_input_given = os.getenv('SITUATION')
    current_location = os.getenv('LOCATION')
    
    if not user_input_given or not current_location:
        sys.stderr.write("SITUATION and LOCATION environment variables are required.\n")
        return

    try:
        curr_lat, curr_lng = await addresstolanglat(current_location)
    except ValueError as e:
        sys.stderr.write(f"Geocoding failed: {e}. Using a default location.\n")
        curr_lat, curr_lng = 40.7128, -74.0060

    os.environ['CURRENT_LAT'] = str(curr_lat)
    os.environ['CURRENT_LNG'] = str(curr_lng)

    # Pass the API key explicitly to GoogleGenerativeAI
    llm = GoogleGenerativeAI(model="gemini-1.5-flash", temperature=0, google_api_key=Google_api)
    tools = [
        Tool(
            name="contact_recipient_via_chat",
            func=contact_recipient_via_chat,
            coroutine=contact_recipient_via_chat,
            description="Useful for sending any message to the recipient and getting their reply. Input is the message to send."
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
    
    # This new, simplified prompt directs the agent to the very first step.
    agent_goal = f"The delivery partner's situation is: '{user_input_given}'. Initiate a chat with the recipient to handle this delivery. Your first message should be polite and ask for permission to leave the parcel with a neighbor or guard."
    
    await agent.arun(agent_goal)

# The rest of the code remains unchanged.
if __name__ == "__main__":
    asyncio.run(run_agent())