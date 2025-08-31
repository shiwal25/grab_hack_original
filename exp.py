#importing necessary libraries :- (we used langchain , google gen ai , iohttp(for prompt enhancing) , dotenv(for env variables))
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
warnings.filterwarnings("ignore", category=DeprecationWarning)

load_dotenv() 
Google_api = os.getenv("GOOGLE_API_KEY")  #gemini api key lene k liye 
user_scenario_input = ""
recipient_reply = ""
curr_lat = None
curr_lng = None


async def geocode_osm(address: str) -> tuple[float, float]:
    url = f"https://nominatim.openstreetmap.org/search?q={address.replace(' ', '+')}&format=json" #openstreetmap api to convert given string address to lat lang 
    headers = {"User-Agent": "example@gmail.com"}
    async with aiohttp.ClientSession() as session: # for async http requests aiohttp use kr rhe hai
        async with session.get(url, headers=headers) as response:
            results = await response.json()
            if results:
                lat = float(results[0]['lat'])
                lng = float(results[0]['lon'])
                return lat, lng
            else:
                raise ValueError(f"We are unable to convert given: {address} to latitude and longitude form. No results found.")


async def find_nearby_lockers(lat: float, lng: float, radius: int = 2000) -> list[dict]:
    overpass_url = "https://overpass-api.de/api/interpreter"
    overpass_query = f'[out:json][timeout:25];node["amenity"="parcel_locker"](around:{radius},{lat},{lng});out body;'
    headers = {"User-Agent": "example@gmail.com"}
    async with aiohttp.ClientSession() as session:
        async with session.post(overpass_url, data={'data': overpass_query}, headers=headers) as response:
            result = await response.json()
            elements = result.get('elements', [])
            if elements:
                print(f"Found {len(elements)} lockers within {radius} meters have a look and select one ")
                lockers = []
                for r in elements[:5]:  
                    tags = r.get('tags', {})
                    name = tags.get('name', 'Unnamed Parcel Locker')
                    address = tags.get('addr:street', '') or tags.get('addr:full', '') or f"{r['lat']}, {r['lon']}"
                    lockers.append({'name': name, 'address': address})
                return lockers
            else:
                r = radius
                if(r>16000):
                    print("No lockers found within 16 km radius, so do you want to proceed with safe drop off or returning the parcel")
                    ans = input("Enter Yes to proceed with safe drop off or No to return the parcel: ").strip().lower()
                    if ans == 'yes':
                        return await perform_safe_drop_off()
                    else:
                        return await return_parcel()
                    
                else:
                    return await find_nearby_lockers(lat, lng, r*2)



def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371  # Earth radius in km
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    distance = R * c
    return distance


async def contact_recipient_via_chat(message: str) -> str:

    global user_scenario_input, recipient_reply
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
    # I am asking for his preference here 
    name = await contact_recipient_via_chat("Please provide the name of the person I can leave the package with:")
    if name == "Recipient is not replying":
        return "Recipient did not respond. Cannot proceed with safe drop-off."

    phone = await contact_recipient_via_chat("Please provide the phone number of that person:")
    if phone == "Recipient is not replying":
        return "Recipient did not respond. Cannot proceed with safe drop-off."

    location = await contact_recipient_via_chat("Please provide the address for the safe drop-off (must be within 2 km):")
    if location == "Recipient is not replying":
        return "Recipient did not respond. Cannot proceed with safe drop-off."

    try:
        drop_lat, drop_lng = await geocode_osm(location)
        dist = haversine(curr_lat, curr_lng, drop_lat, drop_lng)
        if dist > 2:
            print(f"\nThe location is {dist:.2f} km away, which exceeds 2 km.")
            return "Location too far. Cannot proceed with this safe drop-off."
        
        # Dynamic success message
        success_msg = f"Your parcel has been safely delivered to {location} with {name} (phone: {phone}). Thank you!"
        print(success_msg)
        return "Safe drop-off successful."
    except ValueError as e:
        print(f"\nError: {str(e)}")
        return "Failed to validate the drop-off location."


async def perform_locker_delivery(_input: str = "") -> str:
    # we will integrate here google map api by taking delivery boy's current 
    # location as input and providing a safe drop-off location as output
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
        raise ValueError("GOOGLE_API_KEY not found in env file") #if we are not able to find our gemini api key 

    llm = GoogleGenerativeAI(model="gemini-1.5-flash", temperature=0)  # using free teir gemini api key 
    # temperature set to 0 right now to get deterministic output ( for removing randomness for now ), can be changed later if needed
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
            description="Useful for handling a safe drop-off, but ONLY after the recipient has given explicit permission (e.g., replied 'yes'). This tool collects details like name, phone, and location (under 2 km), validates, and completes delivery if possible. No input required."
        ),
        Tool(
            name="perform_locker_delivery",
            func=perform_locker_delivery,
            coroutine=perform_locker_delivery,
            description="Useful for handling delivery to a nearby locker, but ONLY after the recipient has given permission for it. This tool finds lockers under 2 km, presents a list, lets the recipient select, generates a random PIN, and completes delivery. No input required."
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
        verbose=True # Added for thought of chains 
    )

    return agent

async def enhance_userinput(user_input: str) -> str:
    
    
    prompt = (
        f"You are a prompt engineer for a delivery agent. A delivery partner has a valuable package, "
        f"but the recipient is unavailable. The delivery partner describes the situation as: "
        f"'{user_input}'. "
        f"Your task is to generate a polite initial message to send to the recipient, informing them of the situation "
        f"and asking for permission to use a safe drop-off location. End the message with: 'Can I leave it at a safe drop-off location? Please reply with Yes or No.' "
        f"The message should be clear and direct."
    )

    chatHistory = []
    chatHistory.append({ "role": "user", "parts": [{ "text": prompt}] })
    payload = { "contents": chatHistory }
    
    apiKey = Google_api #yaha 2.5 use ho rha hai 
    apiUrl = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-05-20:generateContent?key={apiKey}"

    async with aiohttp.ClientSession() as session:
        async with session.post(apiUrl, headers={'Content-Type': 'application/json'}, data=json.dumps(payload)) as response:
            result = await response.json()
            # print(f"[DEBUG] Gemini API response: {result}")  # Debugging line to check the API response
            if result.get('candidates') and len(result['candidates']) > 0 and 'parts' in result['candidates'][0]['content']:
                return result['candidates'][0]['content']['parts'][0]['text']
            else:
                print("API call failed, using default prompt.") # in case free tier gemini api limit is reached or any other issue
                return ( #returns with this default msg
                    f"I have arrived at your location with your valuable package, but you are unavailable. "
                    f"The situation is: '{user_input}'. "
                    f"Can I leave it at a safe drop-off location? Please reply with Yes or No."
                )


def input_with_timeout(prompt, timeout): #if user is not replying for 150 seconds 
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





# main starting point 
async def main():
    global curr_lat, curr_lng
    current_location = input("Delivery Agent, enter your current address for location services (e.g., 'Lucknow, India'): \n> ")
    try:
        curr_lat, curr_lng = await geocode_osm(current_location)
    except ValueError as e:
        print(f"Geocoding failed: {e} ")
        curr_lat, curr_lng = 40.7128, -74.0060
    
    delivery_agent = setup_agent()
    
    
    user_input = input("Delivery Agent, describe the situation (e.g., 'I am at the door but no one is answering'): \n> ")
    
    global user_scenario_input, recipient_reply
    user_scenario_input = user_input
    recipient_reply = "" 
    
    initial_message = await enhance_userinput(user_input)  # just used for enhancing the delivery guy provided input 
    
    agent_goal = f"""Handle the delivery for an unavailable recipient by strictly following this flow:
1. Initiate contact with the recipient using the initial message: '{initial_message}'
2. Evaluate their response:
   - If affirmative (e.g., 'Yes'), proceed with perform_safe_drop_off.
   - If negative (e.g., 'No'), contact the recipient asking: 'Would you like me to drop off the parcel at a nearby secure locker instead? Please reply with Yes or No.'
3. Based on the locker response:
   - If affirmative, proceed with perform_locker_delivery.
   - If negative, use return_parcel.
Use tools only as needed in this sequence. If recipient does not reply, treat as negative and move to next step."""

    
    await delivery_agent.arun(agent_goal) #finally run based upon generated agent goal 

if __name__ == "__main__":
    asyncio.run(main())
    # asyncio.run(main()) 