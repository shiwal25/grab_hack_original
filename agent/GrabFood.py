import os
import asyncio
import json
import random
from dotenv import load_dotenv
import aiohttp
from langchain.agents import initialize_agent, AgentType, Tool
from langchain_google_genai import GoogleGenerativeAI

import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")




COUPONS = [
    "2% off on your order", "Free delivery for inconvenience", "50 rupee voucher", 
    "Free Coke", "10% off next order", "Buy 1 Get 1 Free", "Free dessert", 
    "Extra 100 reward points", "5% off on beverage", "Free salad"
]



WAIT_THRESHOLD = 40
MAX_NEARBY_INITIAL = 5
MAX_NEARBY_SECOND = 10
cnt  =0
drivers =[
    {"driver_id": 1, "location": {'lat': 28.6139, 'lng': 77.2090}, "status": "idle"},
    {"driver_id": 2, "location": {'lat': 28.6150, 'lng': 77.2070}, "status": "idle"},
    {"driver_id": 3, "location": {'lat': 28.6140, 'lng': 77.2100}, "status": "idle"},
    {"driver_id": 4, "location": {'lat': 28.6120, 'lng': 77.2080}, "status": "idle"},
    {"driver_id": 5, "location": {'lat': 28.6130, 'lng': 77.2060}, "status": "idle"},    
]


orders = []


async def geocode_address(address: str):
    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={address.replace(' ', '+')}&key={GOOGLE_MAPS_API_KEY}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            res = await resp.json()
            if res['status'] == 'OK' and res['results']:
                loc = res['results'][0]['geometry']['location']
                return loc['lat'], loc['lng']
            raise ValueError("Could not geocode address")



async def get_nearby_restaurants(lat, lng, max_results=5):
    url = f"https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    params = {
        "location": f"{lat},{lng}",
        "radius": 3000,
        "type": "restaurant",
        "key": GOOGLE_MAPS_API_KEY
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as resp:
            res = await resp.json()
            return res.get('results', [])[:max_results]



async def get_distance(origin, destination):
    url = f"https://maps.googleapis.com/maps/api/distancematrix/json"
    params = {
        "origins": f"{origin['lat']},{origin['lng']}",
        "destinations": f"{destination['lat']},{destination['lng']}",
        "key":GOOGLE_MAPS_API_KEY
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as resp:
            res = await resp.json()
            elem = res['rows'][0]['elements'][0]
            return elem['distance']['value'], elem['duration']['value']





def notify_customer(message: str):
    print(f"[Notify Customer]: {message}")
    return message



def select_coupon():
    return random.choice(COUPONS)



async def re_route_driver():
    for driver in drivers:
        if driver['status'] == 'idle' and orders:
            min_dist = float('inf')
            closest_order = None
            for order in orders:

                dist, _ = await get_distance(driver['location'], order['restaurant_location'])
                if dist < min_dist:
                    min_dist = dist
                    closest_order = order
            if closest_order:
                driver['status'] = 'assigned'
                driver['assigned_order'] = closest_order['order_id']
                print(f"Driver {driver['driver_id']} assigned to order {closest_order['order_id']}")



def setup_agent():

    llm = GoogleGenerativeAI(model="gemini-1.5-flash", temperature=0)

    tools =[
        Tool(
            name="notify_customer", 
            func=notify_customer, 
            description="Send message to customer"
        ),
        Tool(
            name="get_nearby_restaurants", 
            func=get_nearby_restaurants, 
            description="Fetch nearby restaurants"
        ),
        Tool(
            name="select_coupon", 
            func=select_coupon, 
            description="Select coupon for delay"
        ),
        Tool(
            name="re_route_driver", 
            func=re_route_driver,     
            description="Re-route drivers to new restaurant"
        )
    ]

    agent = initialize_agent(
        tools,
        llm,
        agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
        verbose=True
    )

    return agent




async def grabfood_flow():
    user_address = input("Enter your location (address or pin code): ")
    lat, lng = await geocode_address(user_address)

    
    nearby = await get_nearby_restaurants(lat, lng, MAX_NEARBY_INITIAL)
    print("Nearby Restaurants:")
    for idx, r in enumerate(nearby, 1):
        print(f"{idx}. {r['name']}")


    sel = int(input(f"Select restaurant (1-{len(nearby)}), 0 for more: "))

    if sel == 0:

        nearby = await get_nearby_restaurants(lat, lng, MAX_NEARBY_SECOND)
        print("Next options:")

        for idx, r in enumerate(nearby, 1):
            print(f"{idx}. {r['name']}")
        sel = int(input(f"Select restaurant (1-{len(nearby)}): "))

        if sel < 1 or sel > len(nearby):
            cnt+=1
            print("These are not in the available options ")
            if(cnt !=3):
                asyncio.run(grabfood_flow())
            else:
                return

    restaurant = nearby[sel - 1]

    merchant_id = restaurant['place_id']


    prep_time = int(input(f"Merchant please enter your kitchen prep time (minutes) for your restaurant - {restaurant['name']}: "))

    agent = setup_agent()

    if prep_time > WAIT_THRESHOLD:

        coupon = select_coupon()
        await agent.arun(f"Your order from {restaurant['name']} will take {prep_time} mins. Offering coupon: {coupon}")


        order_id = len(orders) + 1
        orders.append({"order_id": order_id, "restaurant_location": {'lat': restaurant['geometry']['location']['lat'], 'lng': restaurant['geometry']['location']['lng']}, "status": "pending"})
        await re_route_driver()


        
        alternatives = await get_nearby_restaurants(lat, lng, MAX_NEARBY_INITIAL)

        alternatives = [r for r in alternatives if r['place_id'] != merchant_id]

        if alternatives:
            print("Alternative nearby restaurants:")
            for idx, r in enumerate(alternatives, 1):
                print(f"{idx}. {r['name']}")


    else:
        print(f"Your order from {restaurant['name']} will be prepared in {prep_time} mins. Enjoy!")

if __name__ == '__main__':
    asyncio.run(grabfood_flow())
