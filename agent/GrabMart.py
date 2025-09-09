from __future__ import annotations
import os
import asyncio
import logging
import random
from dotenv import load_dotenv
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime
from langchain.agents import initialize_agent, Tool
from langchain_google_genai import GoogleGenerativeAI
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("packaging_mediation_gemini")

MEDIATION_STORE: dict = {}
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")

@dataclass
class MediationSession:
    session_id: str
    order_id: str
    driver_id: str
    customer_id: str
    merchant_id: Optional[str] = None
    resolved: bool = False
    resolution: Optional[Dict[str, Any]] = None
    driver_photos: List[str] = field(default_factory=list)
    customer_photos: List[str] = field(default_factory=list)
    driver_answers: Dict[str, str] = field(default_factory=dict)
    customer_answers: Dict[str, str] = field(default_factory=dict)

async def generate_session_id(order_id: str) -> str:
    return f"med-{order_id}-{int(datetime.now().timestamp())}-{random.randint(100,999)}"

async def create_mediation_session(order_id: str, driver_id: str, customer_id: str, merchant_id: Optional[str]) -> MediationSession:
    sid = await generate_session_id(order_id)
    session = MediationSession(session_id=sid, order_id=order_id, driver_id=driver_id, customer_id=customer_id, merchant_id=merchant_id)
    MEDIATION_STORE[sid] = session
    return session

async def initiate_mediation_flow(order_id: str, driver_id: str, customer_id: str, merchant_id: Optional[str] = None) -> MediationSession:
    session = await create_mediation_session(order_id, driver_id, customer_id, merchant_id)
    logger.info(f"Session {session.session_id} created for Order {order_id}")
    return session

async def collect_evidence(session: MediationSession):
    print(f"\n--- Collecting evidence for Session {session.session_id} ---")
    driver_photo = input(f"Driver ({session.driver_id}) - enter photo filename or NA if none: ").strip()
    session.driver_photos = [driver_photo] if driver_photo != "NA" else []
    bag_sealed = input("Driver - Was the bag sealed by the merchant? (yes/no/NA): ").strip()
    session.driver_answers = {"bag_sealed": bag_sealed}

    customer_photo = input(f"Customer ({session.customer_id}) - enter photo filename or NA if none: ").strip()
    session.customer_photos = [customer_photo] if customer_photo != "NA" else []
    seal_intact = input("Customer - Was the seal intact upon handover? (yes/no/NA): ").strip()
    session.customer_answers = {"seal_intact": seal_intact}

    print("Evidence collected successfully.\n")

async def analyze_evidence(session: MediationSession) -> str:

    driver_answers = session.driver_answers
    customer_answers = session.customer_answers
    verdict = "ambiguous"

    if driver_answers.get("bag_sealed") == "yes" and customer_answers.get("seal_intact") == "yes":


        verdict = "merchant_fault"
    elif driver_answers.get("bag_sealed") == "no":
        verdict = "merchant_fault"

    elif customer_answers.get("seal_intact") == "no" and driver_answers.get("bag_sealed") == "yes":


        verdict = "driver_fault"
    session.resolution = {"verdict": verdict, "confidence": 0.9}
    return verdict

async def issue_refund(session: MediationSession, amount_cents: int = 500):

    print(f"Refund issued to Customer {session.customer_id}: {amount_cents} cents")

async def Penalty_driver(session: MediationSession):

    print(f"Driver {session.driver_id} CHARGED .")

async def log_merchant_packaging_feedback(session: MediationSession, feedback: str):

    print(f"Feedback for Merchant {session.merchant_id}: {feedback}")

async def notify_resolution(session: MediationSession):

    verdict = session.resolution.get("verdict", "unknown")

    print(f"Notification to Customer {session.customer_id}: Order {session.order_id} resolved: {verdict}")

    print(f"Notification to Driver {session.driver_id}: CHARGED ={verdict=='merchant_fault'}")

async def execute_resolution(session: MediationSession):

    verdict = session.resolution.get("verdict", "ambiguous")
    if verdict == "merchant_fault":
        await issue_refund(session)

        await Penalty_driver(session)

        await log_merchant_packaging_feedback(session, feedback="Poor packaging resulted in damage")

    elif verdict == "driver_fault":

        print(f"Driver {session.driver_id} may face penalties.")
    else:

        print("Ambiguous case requires manual review.")

    await notify_resolution(session)
    session.resolved = True

def setup_mediation_agent():

    llm = GoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=GOOGLE_API_KEY, temperature=0)

    tools = [
        Tool.from_function(name="analyze_evidence",
         func=analyze_evidence, 
         description="Analyze evidence and determine fault", 
         coroutine=analyze_evidence),
         
        Tool.from_function(name="execute_resolution", 
                           func=execute_resolution, 
                           description="Finalize resolution and notify parties", 
                           coroutine=execute_resolution)
    ]

    agent = initialize_agent(tools, llm, agent="zero-shot-react-description", verbose=True)
    return agent

async def main():
    print("---- GrabMart Initialized  -----\n")
    order_id = input("Order ID: ").strip()
    driver_id = input("Driver ID: ").strip()
    customer_id = input("Customer ID: ").strip()
    merchant_id = input("Merchant ID: ").strip()

    session = await initiate_mediation_flow(order_id, driver_id, customer_id, merchant_id)
    await collect_evidence(session)

    agent = setup_mediation_agent()
    verdict = await analyze_evidence(session)
    print(f"Evidence analysis complete. Verdict: {verdict}\n")
    await execute_resolution(session)

if __name__ == "__main__":
    asyncio.run(main())
