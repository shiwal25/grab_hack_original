import os
import asyncio
import random
from dotenv import load_dotenv
from langchain.agents import initialize_agent, AgentType, Tool
from langchain_google_genai import GoogleGenerativeAI
import aiohttp
import threading

load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
GRABFOOD_API_KEY = os.getenv("GRABFOOD_API_KEY", "")

user_id = None
order_id = None

def input_with_timeout(prompt: str, timeout: int) -> str:
    result = {"reply": ""}
    def _get():
        try:
            result["reply"] = input(prompt)
        except EOFError:
            result["reply"] = ""
    t = threading.Thread(target=_get, daemon=True)
    t.start()
    t.join(timeout)
    return result["reply"].strip()

async def get_merchant_status(order_id: str) -> dict:
    # Simulated response; replace with real API call when available
    await asyncio.sleep(0.1)
    return {"prep_time_min": random.choice([20, 40, 60])}

async def notify_customer(_input: str = "") -> str:
    print("Notification sent to customer: Your order prep time is delayed. Here’s a voucher for the wait.")
    return "Customer notified"

async def re_route_driver(_input: str = "") -> str:
    print("Driver rerouted to closest pending pickup to optimize time.")
    return "Driver re-routed"

async def get_nearby_merchants(_input: str = "") -> str:
    print("Suggested alternative nearby merchant with shorter wait: Merchant XYZ (prep time 15 min).")
    return "Alternative merchant suggested"

def setup_agent():
    llm = GoogleGenerativeAI(model="gemini-1.5-flash", temperature=0)
    tools = [
        Tool(name="get_merchant_status", func=get_merchant_status, coroutine=get_merchant_status, description="Check kitchen prep time."),
        Tool(name="notify_customer", func=notify_customer, coroutine=notify_customer, description="Notify customer of delay and voucher."),
        Tool(name="re_route_driver", func=re_route_driver, coroutine=re_route_driver, description="Reassign driver to other pickup."),
        Tool(name="get_nearby_merchants", func=get_nearby_merchants, coroutine=get_nearby_merchants, description="Suggest fast alternative merchant."),
    ]
    agent = initialize_agent(tools, llm, agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION, verbose=True)
    return agent

async def run_grabfood_flow():
    global order_id, user_id
    user_id = input("Enter customer ID:\n> ")
    order_id = input("Enter order ID:\n> ")
    merchant_status = await get_merchant_status(order_id)
    initial_prompt = f"Order {order_id} kitchen prep time is {merchant_status['prep_time_min']} minutes. Plan actions."
    agent = setup_agent()
    await agent.arun(initial_prompt)

if __name__ == "__main__":
    asyncio.run(run_grabfood_flow())
