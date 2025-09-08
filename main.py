import asyncio
import os
import json
from dotenv import load_dotenv
from langchain_google_genai import GoogleGenerativeAI
from GrabExpress import run_grabexpress_flow_entry
from GrabCar import run_grabcar_flow_entry

load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")

async def detect_scenario(user_text: str) -> str:
    llm = GoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=GOOGLE_API_KEY, temperature=0)
    prompt = f"""
    You are an intelligent scenario classifier for Grab services. 
    User will describe their situation in free text.
    Decide if it belongs to one of these categories:
    - GrabCar: A driver transporting a passenger, trip, route, ETA, obstruction monitoring.
    - GrabExpress: A delivery agent handling parcel delivery, recipient unavailable, safe drop-off, locker, return parcel.
    Respond strictly with one word: "GrabCar" or "GrabExpress".

    User description: {user_text}
    """
    return (await llm.ainvoke(prompt)).strip()

async def main():
    import sys

    print(json.dumps({"type": "request_user_input", "prompt": "Describe your situation", "target": "driver"}), flush=True)

    scenario_text = ""
    for line in sys.stdin:
        try:
            data = json.loads(line.strip())
        except Exception:
            continue

        if "input" in data:
            scenario_text = data["input"]
            break

    if not scenario_text:
        print(json.dumps({"type": "error", "message": "No scenario description provided."}), flush=True)
        return

    try:
        scenario = await detect_scenario(scenario_text)
    except Exception as e:
        print(json.dumps({"type": "error", "message": f"Scenario detection failed: {e}"}), flush=True)
        return

    if scenario.lower() == "grabexpress":
        await run_grabexpress_flow_entry()
    elif scenario.lower() == "grabcar":
        await run_grabcar_flow_entry()
    else:
        print(json.dumps({"type": "error", "message": "Could not classify scenario. Please try again."}), flush=True)

if __name__ == "__main__":
    asyncio.run(main())
