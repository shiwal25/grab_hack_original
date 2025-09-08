<h1 align="center" id="title">PROJECT SYNAPSE (TEAM HACKON)</h1>
<img width="957" alt="kayo-chan" src="https://github.com/user-attachments/assets/f423798c-1161-4c3b-b4c0-199e6d62c024">

<p align="center"><i>(Team Hackon)</i></p>
<h2>Description</h2>
<br>
<p id="description">
Developed an asynchronous event-driven Python application that leverages LangChain Google Generative AI (Gemini) and Google Maps Platform to automate decision-making in two operational domains: GrabExpress: Handles delivery partner–recipient communication suggests safe drop-off locations finds secure lockers and processes recipient responses with LLM-based intent parsing. GrabCar: Monitors traffic between origin–destination calculates alternative optimal routes notifies passengers/drivers and checks live flight statuses for urgent trips. Key Features: Natural language classification of user scenarios into logistics or ride-hailing workflows. Prompt engineering for enhanced agent goals and precise LLM responses. Real-time geocoding routing and traffic analysis via Google Maps APIs. Flight status tracking using AviationStack API. Automated timeout handling for unresponsive users. Integrated with asynchronous coroutines for scalable concurrent API calls.</p>
<h2>🧐 Features</h2>

Here're some of the project's best features:

*   AI-Powered Scenario Classification – Automatically classifies situations into GrabExpress (delivery) or GrabCar (ride-hailing) using Google Generative AI (Gemini).
*   LLM-Enhanced Decision Making – Uses prompt-engineered Gemini responses to create actionable goals for agents.
*   Real-Time Map Integration – Integrates Google Maps API for geocoding routing alternative path calculations and traffic-aware trip planning.
*   Recipient Interaction Automation – Initiates chat with recipients suggests safe drop-off locations and locates nearby parcel lockers.
*   Flight Status Tracking – Fetches real-time flight status from AviationStack API for urgent travel scenarios.
*   Timeout Handling – Automatically proceeds with fallback actions if the recipient/passenger is unresponsive.
*   Asynchronous & Scalable – Built with asyncio and aiohttp for concurrent non-blocking API calls.
*   Customizable Agent Tools – Modular tool setup with LangChain making it easy to extend with new APIs or logic.


<br />
<h2>🛠️ Installation Steps:</h2>

<p>1. Clone the repository</p>

```
git clone https://github.com/aerinpatel/Grab_hack_proj.git
```

<p>2. Create a virtual environment</p>

```
python -m venv venv
```

<p>3. Activate the virtual environment</p>

```
venv\Scripts\activate
```

<p>4. Install dependencies</p>

```
pip install -r requirements.txt
```

<p>5. Set up environment variables</p>

```
GOOGLE_API_KEY=your_gemini_api_key
GOOGLE_MAPS_API_KEY=your_google_maps_api_key
FLIGHT_API_KEY=your_aviationstack_api_key
```

<p>6. Run the project</p>

```
python main.py
```


#### TechStacks Used by Us :

<!--START_SECTION:waka-->
```
Langchain                     ██████████████████▓░░░░░░   75.25 %

JSON                          █████▒░░░░░░░░░░░░░░░░░░░   21.23 %

TSConfig                      ▓░░░░░░░░░░░░░░░░░░░░░░░░   02.48 %

Vue.js                        ▒░░░░░░░░░░░░░░░░░░░░░░░░   00.67 %

Git Config                    ░░░░░░░░░░░░░░░░░░░░░░░░░   00.28 %
```
<!--END_SECTION:waka-->

<br />
<p> need to be updated when we have pushed all code </p>

<!--
     This is the list of my skills and tools I am studying!
-->
### Main skills
[![My Skills](https://skillicons.dev/icons?i=py,regex,github,git,mongodb,mysql,eclipse,java,spring,js,nodejs,react,express,jest,jenkins,cpp,cs,dotnet,html,css,bootstrap,pug,php,androidstudio,blender,ps,notion)](https://skillicons.dev)

### Studying
[![Learning](https://skillicons.dev/icons?i=aws,azure,ruby)](https://skillicons.dev)



<h2> Architecture </h2>




[https://app.eraser.io/workspace/72CRzJvRh0oKGkwe4omY?origin=share](https://app.eraser.io/workspace/72CRzJvRh0oKGkwe4omY?origin=share)
  
<h2> Work Demonstration </h2>

[https://youtu.be/XnvdVjgUIKA](https://youtu.be/XnvdVjgUIKA)


  <h2> REFERENCES AND LINKS </h2>
  <table><tr><td valign="top" width="33%">

### CONTRIBUTORS AND THEIR PROFILES 
<!-- recent_releases starts -->
[datasette-alerts-discord 0.1.0a1](https://github.com/datasette/datasette-alerts-discord/releases/tag/0.1.0a1) - 2025-08-19

[datasette-alerts 0.0.1a3](https://github.com/datasette/datasette-alerts/releases/tag/0.0.1a3) - 2025-08-19

[llm-gemini 0.25](https://github.com/simonw/llm-gemini/releases/tag/0.25) - 2025-08-18

[datasette-demo-dbs 0.1.1](https://github.com/datasette/datasette-demo-dbs/releases/tag/0.1.1) - 2025-08-14

[llm 0.27.1](https://github.com/simonw/llm/releases/tag/0.27.1) - 2025-08-12

[llm-anthropic 0.18](https://github.com/simonw/llm-anthropic/releases/tag/0.18) - 2025-08-05

[datasette-queries 0.1.2](https://github.com/datasette/datasette-queries/releases/tag/0.1.2) - 2025-07-22

[datasette-public 0.3a3](https://github.com/datasette/datasette-public/releases/tag/0.3a3) - 2025-07-22
<!-- recent_releases ends -->
More [recent releases](https://github.com/simonw/simonw/blob/main/releases.md)
</td><td valign="top" width="34%">

### RESEARCH PAPERS 
<!-- blog starts -->
[GPT-5 Thinking in ChatGPT (aka Research Goblin) is shockingly good at search](https://simonwillison.net/2025/Sep/6/research-goblin/) - 2025-09-06

[V&A East Storehouse and Operation Mincemeat in London](https://simonwillison.net/2025/Aug/27/london-culture/) - 2025-08-27

[The Summer of Johann: prompt injections as far as the eye can see](https://simonwillison.net/2025/Aug/15/the-summer-of-johann/) - 2025-08-15

[Open weight LLMs exhibit inconsistent performance across providers](https://simonwillison.net/2025/Aug/15/inconsistent-performance/) - 2025-08-15

[LLM 0.27, the annotated release notes: GPT-5 and improved tool calling](https://simonwillison.net/2025/Aug/11/llm-027/) - 2025-08-11

[Qwen3-4B-Thinking: "This is art - pelicans don't ride bikes!"](https://simonwillison.net/2025/Aug/10/qwen3-4b/) - 2025-08-10
<!-- blog ends -->
More on [simonwillison.net](https://simonwillison.net/)
</td><td valign="top" width="33%">

### API KEYS
<!-- tils starts -->
[Running a gpt-oss eval suite against LM Studio on a Mac](https://til.simonwillison.net/llms/gpt-oss-evals) - 2025-08-17

[Configuring GitHub Codespaces using devcontainers](https://til.simonwillison.net/github/codespaces-devcontainers) - 2025-08-13

[Rate limiting by IP using Cloudflare's rate limiting rules](https://til.simonwillison.net/cloudflare/rate-limiting) - 2025-07-03

[Using Playwright MCP with Claude Code](https://til.simonwillison.net/claude-code/playwright-mcp-claude-code) - 2025-07-01

[Converting ORF raw files to JPEG on macOS](https://til.simonwillison.net/macos/orf-to-jpeg) - 2025-06-26

[Publishing a Docker container for Microsoft Edit to the GitHub Container Registry](https://til.simonwillison.net/github/container-registry) - 2025-06-21
<!-- tils ends -->
More on [til.simonwillison.net](https://til.simonwillison.net/)
</td></tr></table>

