# importing needfull things 
from __future__ import annotations
import os
import asyncio
import json
import warnings
import threading
import random
import aiohttp
import requests
from dotenv import load_dotenv
from langchain.agents import initialize_agent, AgentType, Tool
from langchain_google_genai import GoogleGenerativeAI
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from math import radians, sin, cos, sqrt, atan2
from datetime import datetime
import sys
from langchain.callbacks.base import AsyncCallbackHandler
warnings.filterwarnings("ignore", category=DeprecationWarning)


# for fetching api keys from .env 

load_dotenv()


# here we are providing variables to api keys for better working from .env file
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "") 
FLIGHT_API_KEY = os.getenv("FLIGHT_API_KEY", "")  
TRAIN_API_KEY = os.getenv("TRAIN_API_KEY", "")    
BUS_API_KEY = os.getenv("BUS_API_KEY", "")     
RAPIDAPI_HOST = "irctc-indian-railway-pnr-status.p.rapidapi.com"   


# Interval after which check_Status or event_status is called .
TRAFFIC_INTERVAL = 60
TRANSIT_INTERVAL = 60 # we fixed them for now 

# ye hai ki how we are dealing with obstruction case 

MAJOR_DELAY_PCT = 0.25  # if delay increase by current 25 %  
MAJOR_DELAY_ABS_SEC = 8 * 60  # if delay increase by 8 minutes
train_departure_date: Optional[str] = None


#added for first check 
first_train_check = True
first_flight_check = True
# first_bus_check = True

trip_active = True
current_route_index: int = 0
all_routes: List[Dict[str, Any]] = [] 
last_checked_eta_sec: Optional[int] = None


orig_latlng: Optional[Tuple[float, float]] = None
dest_latlng: Optional[Tuple[float, float]] = None
mode_of_transport: str = "other"  
pnr: Optional[str] = None

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
            tool = getattr(action, "tool", None) or str(action)
            tool_input = getattr(action, "tool_input", None)
            log = getattr(action, "log", None)
            print(json.dumps({
                "type": "agent_event",
                "event": "agent_action",
                "tool": tool,
                "tool_input": tool_input,
                "log": str(log)
            }), flush=True)
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

#For taking input with time limit from user  
async def input_with_timeout(prompt: str, timeout: int) -> str:
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

    thread = threading.Thread(target=read_stdin, daemon=True)
    thread.start()

    try:
        user_input = await asyncio.wait_for(future_input, timeout=timeout)
        return user_input.strip()
    except asyncio.TimeoutError:
        return ""

def changetime(seconds: int) -> str: #== for changing time in sec,  m and hours
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}h {m}m"
    elif m:
        return f"{m}m"
    else:
        return f"{seconds}s"

def fmt_distance(meters: int) -> str: # for changing distance given in m in kms and meters  
    if meters >= 1000:
        return f"{meters/1000:.1f} km"
    return f"{meters} m"

# this is used to change  given address in form of lat lang because google map api works on lat lang basis
async def changetolatlang(session: aiohttp.ClientSession, address: str) -> Tuple[float, float]:
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {"address": address, "key": GOOGLE_MAPS_API_KEY}

    async with session.get(url, params=params) as resp:
        data = await resp.json()

        results = data.get("results")
        if data.get("status") != "OK" or not results:
            raise ValueError(f"Geocoding failed for '{address}': {data.get('status')}")

        location = results[0]["geometry"]["location"]
        return location["lat"], location["lng"]

async def directions_google(session: aiohttp.ClientSession, origin: Tuple[float, float], destination: Tuple[float, float],alternatives: bool = False,) -> Dict[str, Any]:
    #ye return kregi ek dictionary having all routes 
    url = "https://maps.googleapis.com/maps/api/directions/json"   #google map api key url 
    params = {
        "origin": f"{origin[0]},{origin[1]}",  #origin k first second lat lang 
        "destination": f"{destination[0]},{destination[1]}", # desitination k bhi first second lat lang
        "mode": "driving",  # taking from scenario as given  example is of  driving 
        "departure_time": "now", 
        "traffic_model": "best_guess", 
        "alternatives": str(alternatives).lower(),
        "key": GOOGLE_MAPS_API_KEY, # defined in .env files 
    }

    async with session.get(url, params=params) as resp: # ye get request bhej rha hai url and params ko
        data = await resp.json()
        if data.get("status") != "OK":
            raise ValueError(f"Directions API (google map api key is not working correctly) error: {data.get('status')}: {data.get('error_message')}")
        return data # in case the status is OK 

# parsing the json file return by directions_google function(bcz that function is returning us a json with a lot of legs ).
def parse_route(route_json: Dict[str, Any]) -> Dict[str, Any]:
    legs = route_json.get("legs", [])

    total_distance_m = sum(
        leg.get("distance", {}).get("value", 0) for leg in legs
    )
    total_duration_seconds = sum(
        leg.get("duration", {}).get("value", 0) for leg in legs
    )
    total_duration_with_traffic_seconds = sum(
        leg.get("duration_in_traffic", {}).get("value", leg.get("duration", {}).get("value", 0))
        for leg in legs
    )

    return {
    "route_name": route_json.get("summary", "Unnamed Route"),
    "distance_m": int(total_distance_m),
    "duration_s": int(total_duration_seconds),
    "duration_with_traffic_seconds": int(total_duration_with_traffic_seconds),
    "warnings": route_json.get("warnings", []), 
    }

async def get_routes( session: aiohttp.ClientSession, origin: Tuple[float, float], destination: Tuple[float, float],include_alternatives: bool = True,) -> List[Dict[str, Any]]:
    raw = await directions_google(session, origin, destination, alternatives=include_alternatives)
    routes = [parse_route(r) for r in raw.get("routes", [])]
    routes.sort(key=lambda r: r["duration_with_traffic_seconds"])
    return routes

async def detect_obstruction(session: aiohttp.ClientSession) -> Dict[str, Any]:

    global all_routes, current_route_index, last_checked_eta_sec

    routes = await get_routes(session, orig_latlng, dest_latlng, include_alternatives=True)
    if not routes:
        raise ValueError("There are no routes available on DIRECTION API for This origin and destination .")

    all_routes = routes  
    chosen = routes[current_route_index] if current_route_index < len(routes) else routes[0]

    base = max(1, chosen["duration_s"])  
    eta = chosen["duration_with_traffic_seconds"]  
    delta = max(0, eta - base)

    if base <= 0:
        return 0.0
    pct = (eta -base)/base

    last_checked_eta_sec = eta

    severity = "NONE"
    has_obstruction = False
    if delta >0:  
        severity = "MINOR"
        has_obstruction = True
        if pct >= MAJOR_DELAY_PCT and delta >= MAJOR_DELAY_ABS_SEC:  
            severity = "MAJOR"

    obstruction_notes = []
    if chosen.get("warnings"):
        obstruction_notes.extend(chosen["warnings"])
        has_obstruction = True
        severity = "MAJOR"

    return {
    "has_obstruction": has_obstruction,
    "severity": severity,
    "eta_sec": eta,
    "base_sec": base,
    "delta_sec": delta,
    "delta_pct": pct,
    "routes": routes,
    "obstruction_notes": chosen.get("warnings", []),  
    }

async def calculate_alternative_route(_input: str = "") -> str:
    async with aiohttp.ClientSession() as session:
        det = await detect_obstruction(session)
        routes = det["routes"]
        if not routes:
            return "No routes available."

        top = routes[:5]
        chosen = routes[current_route_index] if current_route_index < len(routes) else routes[0]
        curr_eta = chosen["duration_with_traffic_seconds"]

        lines = ["Alternate routes (fastest first):"]
        for i, r in enumerate(top, start=1):
            eta = r["duration_with_traffic_seconds"]
            dist = r["distance_m"]
            delta_sec = curr_eta - eta
            if delta_sec == 0:
                delta_str = "same ETA"
            elif delta_sec > 0:
                delta_str = f"faster by {changetime(abs(delta_sec))}"
            else:
                delta_str = f"slower by {changetime(abs(delta_sec))}"

            lines.append(
                f"{i}. {r['route_name']} — {fmt_distance(dist)}, ETA {changetime(eta)} ({delta_str})"
            )

        lines.append("\nReply with a number to switch, or type 'stay' to keep current route.")
        return "\n".join(lines)

async def set_current_route(selection: str) -> str:
    global current_route_index
    selection = (selection or "").strip().lower()

    if selection=="stay":
        return "Staying on current route."
    
    try:
        idx = int(selection) - 1  

    except ValueError:
        return "Invalid selection. Please enter a number like 1, 2, 3... or 'stay'."

    if idx <0 or idx >=len(all_routes):
        return "This option is not available."

    current_route_index = idx
    chosen = all_routes[current_route_index]
    return(
        f"Switched to route #{idx+1} ({chosen['route_name']}), "
        f"ETA : {changetime(chosen['duration_with_traffic_seconds'])}, "
        f"distance : {fmt_distance(chosen['distance_m'])}."
    )

async def notify_passenger_and_driver(message: str) -> str:

    print(json.dumps({"type": "info", "message": message}), flush=True)

    reply = await input_with_timeout("Your reply (number/stay) [120s timeout]:\n> ", 120)
    return reply or ""

def safe_get(d, *keys, default=0):
    for key in keys:
        if not isinstance(d, dict):
            return default
        d = d.get(key)
        if d is None:
            return default
    return d

async def check_flight_status(flight_number: str) -> Optional[Dict[str, Any]]:
    if not FLIGHT_API_KEY:
        print(json.dumps({"type": "error", "message": "Flight API key missing! Check if your key is valid or if the API limit is exceeded."}), flush=True)
        return None

    url = "https://api.aviationstack.com/v1/flights"
    params = {"access_key": FLIGHT_API_KEY, "flight_iata": flight_number, "limit": 1}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=20) as resp:
                data = await resp.json()

                if "data" not in data or not data["data"]:
                    return {"error": "No flight data found."}

                flight = data["data"][0]

                departure = flight.get("departure") or {}
                arrival = flight.get("arrival") or {}

                return {
                    "flight_number": flight.get("flight", {}).get("iata", ""),
                    "airline": flight.get("airline", {}).get("name", ""),
                    "status": (flight.get("flight_status") or "UNKNOWN").upper(),
                    "from": departure.get("airport", ""),
                    "to": arrival.get("airport", "") ,
                    "delay_departure_min": departure.get("delay") or 0,
                    "delay_arrival_min": arrival.get("delay") or 0,
                    "raw": flight
                }

    except Exception as e:
        print(json.dumps({"type": "error", "message": f"Error occurred in flight status check: {e}"}), flush=True)
        return None

async def check_train_status(train_number: str, departure_date: str) -> Dict[str, Any]:
    """
    Fetch train status and calculate delay for the last crossed station.
    """
    if not TRAIN_API_KEY:
        print(json.dumps({"type": "error", "message": "Train Rapid API key missing! Check if key is valid or API limit exceeded."}), flush=True)
        return None

    url = f"https://indian-railway-irctc.p.rapidapi.com/api/trains/v1/train/status?departure_date={departure_date}&isH5=true&client=web&train_number={train_number}"
    headers = {
        'x-rapidapi-host': 'indian-railway-irctc.p.rapidapi.com',
        'x-rapidapi-key': TRAIN_API_KEY
    }

    try:
        response = requests.get(url, headers=headers, timeout=20)
        data = response.json()

        body = data.get("body", {})
        stations = body.get("stations", [])
        last_crossed = body.get("current_station", "")
        # print(last_crossed)

        scheduled = actual = None

        for station in stations:
            if station.get("stationCode") == last_crossed:
                scheduled = station.get("arrivalTime")
                actual = station.get("actual_arrival_time")
                break

        from datetime import datetime, timedelta

        def calculate_delay(scheduled: str, actual: str) -> str:
            if not scheduled or not actual or scheduled == "--" or actual == "--":
                return "UNKNOWN"
            try:
                today = datetime.today().strftime("%Y%m%d")
                scheduled_dt = datetime.strptime(f"{today} {scheduled}", "%Y%m%d %H:%M")
                actual_dt = datetime.strptime(f"{today} {actual}", "%Y%m%d %H:%M")

                if actual_dt < scheduled_dt:
                    actual_dt += timedelta(days=1)

                delta_min = int((actual_dt - scheduled_dt).total_seconds() // 60)

                if delta_min == 0:
                    return "On time"
                elif delta_min > 0:
                    return f"Delayed by {delta_min} min"
                else:
                    return f"Ahead by {abs(delta_min)} min"

            except Exception as e:
                print(json.dumps({"type": "error", "message": f"[calculate_delay] Exception: {e}"}), flush=True)
                return "UNKNOWN"

        delay_status = calculate_delay(scheduled, actual)

        src = stations[0].get("stationName") if stations else "UNKNOWN"
        dest = stations[-1].get("stationName") if stations else "UNKNOWN"

        return {
            "train_num": train_number,
            "source": src,
            "destination": dest,
            "last_crossed_station": last_crossed,
            "scheduled_arrival": scheduled,
            "actual_arrival": actual,
            "delay_status": delay_status,
            "raw": data
        }

    except Exception as e:
        print(json.dumps({"type": "error", "message": f"Error occurred in train status check: {e}"}), flush=True)
        return None



async def check_traffic_tool(_input: str = "") -> str:

    async with aiohttp.ClientSession() as session:
        det = await detect_obstruction(session)

    label = det["severity"]
    eta_s = det["eta_sec"]
    base_s = det["base_sec"]
    delta_s = det["delta_sec"]
    
    if det["obstruction_notes"]:
        msg = (
            f"Obstruction detected: {', '.join(det['obstruction_notes'])}. "
            f"ETA: {changetime(eta_s)}, Distance: {fmt_distance(all_routes[current_route_index]['distance_m'])}."
        )
    else:
        msg = (
            f"Traffic check: severity={label}, "
            f"Base travel time={changetime(base_s)}, "
            f"Current ETA={changetime(eta_s)}, "
            f"Delay={changetime(delta_s)}."
        )
    return msg


async def notify_passenger_and_driver_tool(message: str) -> str:
    return await notify_passenger_and_driver(message)


async def check_flight_status_tool(pnr: str) -> str:
    st = await check_flight_status(pnr)
    if not st:
        return "Flight status unavailable"
    delay = st.get("delay_departure_min")
    if st.get("status") == "DELAYED" and delay:
        return f"Flight delayed by ~{delay} min."
    return f"Flight status: {st.get('status')}"


async def check_train_status_tool(pnr: str) -> str:
    st = await check_train_status(pnr, train_departure_date or "20250906")
    if not st:
        return "Train status unavailable"
    return f"Train status: {st.get('delay_status')}"


def setup_agent() -> Any:
    
    llm = GoogleGenerativeAI(model="gemini-1.5-flash", temperature=0)
    tools = [
        Tool(
            name="check_traffic",
            func=check_traffic_tool,
            coroutine=check_traffic_tool,
            description=(
                "Check current traffic on the planned route and return severity, base ETA, "
                "current ETA, and delay. Use this repeatedly to monitor evolving conditions."
            ),
        ),
        Tool(
            name="calculate_alternative_route",
            func=calculate_alternative_route,
            coroutine=calculate_alternative_route,
            description=(
                "Compute fastest route options with ETA and distance deltas vs current. "
                "Returns a numbered list for selection."
            ),
        ),
        Tool(
            name="set_current_route",
            func=set_current_route,
            coroutine=set_current_route,
            description=(
                "Switch to a selected alternative route by replying with its number (1..N) or 'stay'."
            ),
        ),
        Tool(
            name="notify_passenger_and_driver",
            func=notify_passenger_and_driver_tool,
            coroutine=notify_passenger_and_driver_tool,
            description=(
                "Send a notification to both passenger and driver, optionally collecting a reply (e.g., '1', 'stay')."
            ),
        ),
        Tool(
            name="check_flight_status",
            func=check_flight_status_tool,
            coroutine=check_flight_status_tool,
            description=(
                "Check flight status by PNR. Returns high-level status (DELAYED, ON_TIME, CANCELLED)."
            ),
        ),
        Tool(
            name="check_train_status",
            func=check_train_status_tool,
            coroutine=check_train_status_tool,
            description=(
                "Check train status by PNR. Returns high-level status and delay if available."
            ),
        ),
    ]

    agent = initialize_agent(
        tools,
        llm,
        agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
        verbose=True,
        return_intermediate_steps=True,
        callbacks=[WebsocketCallbackHandler()]
    )
    return agent

async def traffic_monitor_loop():
    global trip_active
    while trip_active:
        try:
            async with aiohttp.ClientSession() as session:
                det = await detect_obstruction(session)

            if det["has_obstruction"] and det["severity"] == "MAJOR":
                chosen = all_routes[current_route_index]
                msg = (
                    "Alert: We detected a major obstruction on your current route.\n"
                    f"Route distance: {fmt_distance(chosen['distance_m'])}\n"
                    f"Normal time (no traffic): {changetime(det['base_sec'])}\n"
                    f"Current ETA (with obstruction): {changetime(det['eta_sec'])}\n"
                    f"Delay: {changetime(det['delta_sec'])}\n"
                    f"Severity: {det['severity']}\n"
                )
                menu = await calculate_alternative_route("")
                reply = await notify_passenger_and_driver(msg + "\n" + menu)
                if reply:
                    print(json.dumps({"type": "info", "message": await set_current_route(reply)}), flush=True)
            else:
                chosen = all_routes[current_route_index]
                ping = (
                    f"Route clear.\n"
                    f"Distance: {fmt_distance(chosen['distance_m'])}\n"
                    f"ETA (with traffic): {changetime(chosen['duration_with_traffic_seconds'])}\n"
                )
                print(json.dumps({"type": "info", "message": ping}), flush=True)

        except Exception as e:
            print(json.dumps({"type": "error", "message": f"[traffic_monitor_loop] Warning: {e}"}), flush=True)

        await asyncio.sleep(TRAFFIC_INTERVAL)


async def transit_monitor_loop():
    """
    Monitors flight/train status periodically during the trip.
    """
    global trip_active, first_train_check, first_flight_check, train_departure_date

    if mode_of_transport not in {"flight", "train"} or not pnr:
        return

    while trip_active:
        try:
            if mode_of_transport == "flight":
                st = await check_flight_status(pnr)
                if st:
                    if first_flight_check:
                        print(json.dumps({"type": "info", "message": f" Flight {st.get('flight_number')} ({st.get('airline')}) is scheduled."}), flush=True)
                        delay_dep = st.get("delay_departure_min", 0)
                        delay_arr = st.get("delay_arrival_min", 0)
                        if delay_dep or delay_arr:
                            print(json.dumps({"type": "info", "message": f"Flight delayed by ~{delay_dep} min on departure, ~{delay_arr} min on arrival"}), flush=True)
                        else:
                            print(json.dumps({"type": "info", "message": "Flight is on time"}), flush=True)
                        first_flight_check = False
                    else:
                        status = st.get("status", "On time")
                        delay = st.get("delay_departure_min", 0)
                        if status.upper() == "DELAYED" and delay:
                            print(json.dumps({"type": "info", "message": f"Flight update: delayed by ~{delay} min"}), flush=True)
                        else:
                            print(json.dumps({"type": "info", "message": f"Flight update: {status}"}), flush=True)
                else:
                    print(json.dumps({"type": "info", "message": "Flight update unavailable at the moment."}), flush=True)

            elif mode_of_transport == "train":
                train_number = pnr
                departure_date = train_departure_date or "20250906"
                st = await check_train_status(train_number, departure_date)
                if st:
                    if first_train_check:
                        print(json.dumps({"type": "info", "message": f" Train number: {st['train_num']}"}), flush=True)
                        print(json.dumps({"type": "info", "message": f"From {st['source']} to {st['destination']}"}), flush=True)
                        print(json.dumps({"type": "info", "message": f"Currently at: {st['last_crossed_station']}"}), flush=True)
                        print(json.dumps({"type": "info", "message": f"Current delay: ~{st['delay_status']}"}), flush=True)
                        first_train_check = False
                    else:
                        print(json.dumps({"type": "info", "message": f"Currently at: {st['last_crossed_station']}"}), flush=True)
                        print(json.dumps({"type": "info", "message": f"Scheduled arrival: {st['scheduled_arrival']}, Actual arrival: {st['actual_arrival']}"}), flush=True)
                        print(json.dumps({"type": "info", "message": f"Current delay: ~{st['delay_status']}"}), flush=True)
                else:
                    print(json.dumps({"type": "info", "message": "Train update unavailable at the moment."}), flush=True)

        except Exception as e:
            print(json.dumps({"type": "error", "message": f"Some error in transit_monitor_loop: {e}"}), flush=True)

        await asyncio.sleep(TRANSIT_INTERVAL)

async def run_grabcar_flow():
    global orig_latlng, dest_latlng, mode_of_transport, pnr, train_departure_date, _prompt_target

    _prompt_target = "driver"
    origin_addr = await input_with_timeout("Driver, Enter your current address :\n>", 300)
    dest_addr = await input_with_timeout("Enter Customer's destination address :\n>", 300)

    mode_of_transport = (await input_with_timeout("Continuation mode at destination? (flight/train/other):\n> ", 60)).strip().lower() or "other"
    if mode_of_transport == "train":
        pnr = (await input_with_timeout("Enter Train number :\n> ", 60)).strip() or None
        train_departure_date = (await input_with_timeout("Enter train departure date (YYYYMMDD):\n> ", 60)).strip() or None
    elif mode_of_transport == "flight":
        pnr = (await input_with_timeout("Enter ID of your flight for details :\n> ", 60)).strip() or None
       
    else:    
        print(json.dumps({"type": "info", "message": "No transit monitoring will be done as this transit tool is not available right now"}), flush=True)

    async with aiohttp.ClientSession() as session:
        orig_lat, orig_lng = await changetolatlang(session, origin_addr)
        dest_lat, dest_lng = await changetolatlang(session, dest_addr)

    orig_latlng = (orig_lat, orig_lng)
    dest_latlng = (dest_lat, dest_lng)

    async with aiohttp.ClientSession() as session:
        routes = await get_routes(session, orig_latlng, dest_latlng, include_alternatives=True)
    if not routes:
        print(json.dumps({"type": "error", "message": "Sorry we are unable to find any routes. Exiting...."}), flush=True)
        return

    global all_routes, current_route_index
    all_routes = routes
    current_route_index = 0

    chosen = routes[current_route_index]
    print(json.dumps({"type": "info", "message": (
        f"Initial route selected: {chosen['route_name']}, "
        f"Distance {fmt_distance(chosen['distance_m'])}, "
        f"ETA {changetime(chosen['duration_with_traffic_seconds'])}."
    )}), flush=True)
    check_status = asyncio.create_task(traffic_monitor_loop())
    event_task = asyncio.create_task(transit_monitor_loop())

    try:
        print(json.dumps({"type": "info", "message": "\nMonitoring started. Press Ctrl+C to stop.\n"}), flush=True)
        await asyncio.gather(check_status, event_task)
    except asyncio.CancelledError:
        pass
    finally:
        global trip_active
        trip_active = False
        for t in (check_status, event_task):
            if not t.done():
                t.cancel()
        await asyncio.sleep(0.1)


async def run_langchain_plan():
    agent = setup_agent()

    plan = f"""
    You are a ride operations agent helping a passenger on an urgent trip. The system will provide tools.
    Follow this exact plan once (no infinite loops):

    1) Call check_traffic to notify and find alternate route when an obstruction is found.
    2) If delay severity is MAJOR (or ETA increased), call calculate_alternative_route and then notify_passenger_and_driver with the menu asking for a route choice (yes or no).
    3) Read the reply; then call set_current_route with either the index or 'stay' depending on user and drivers input.
    4) If continuation mode is '{mode_of_transport}' and a code/number exists, call the matching tool (check_flight_status / check_train_status ) once and append the status to your final message.
    5) Summarize the decision and provide the updated ETA.
    """
    await agent.arun(plan)


async def run_grabcar_flow_entry():
    await run_grabcar_flow()
