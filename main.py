import asyncio
import os
from dotenv import load_dotenv
from langchain_google_genai import GoogleGenerativeAI
from GrabCar import run_grabcar_flow_entry
from GrabExpress import run_grabexpress_flow_entry


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
    scenario_text = input("Describe your situation:\n> ")
    scenario = await detect_scenario(scenario_text)
    if scenario.lower() == "grabcar":
        await run_grabcar_flow_entry()
    elif scenario.lower() == "grabexpress":
        await run_grabexpress_flow_entry()
    else:
        print("Could not classify scenario. Please try again.")

if __name__ == "__main__":
    asyncio.run(main())
