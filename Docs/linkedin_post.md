# LinkedIn Post

---

## 🌍 I Built an AI Travel Planner Using Multi-Agent Architecture — Here's What I Learned

Just shipped **GlobeAI** — a full-stack AI system where **5 specialized agents** collaborate to turn a simple request like *"10 days in Thailand, ₹80K budget, love temples and street food"* into a complete, day-by-day travel itinerary.

### 🤖 How It Works

Instead of one monolithic AI call, I designed a **multi-agent pipeline**:

1. **Orchestrator Agent** — Extracts structured constraints from natural language
2. **Destination Agent** — Researches attractions, food spots, and local experiences
3. **Logistics Agent** — Plans lodging, transport routes, and daily sequencing
4. **Budget Agent** — Optimizes spending across categories (stay, food, transport, activities)
5. **Review Agent** — Validates the itinerary against the original request before delivery

The agents run **in parallel** using Python's asyncio, and a **repair loop** automatically fixes issues flagged by the Review Agent (up to 3 cycles).

### 🔧 Tech Stack

- **Backend**: FastAPI + Pydantic v2 + asyncio
- **Frontend**: React + TypeScript + Vite
- **LLM**: Groq Cloud (LLaMA 3.3 70B)
- **Deployment**: Docker + Render + Vercel

### 💡 Key Takeaways

→ **Constraints-first design** prevents agents from interpreting the same request differently
→ **Hub-and-spoke communication** (no agent-to-agent chatter) keeps the system debuggable
→ **Typed artifacts** (Pydantic schemas) at every boundary eliminate integration surprises
→ **Graceful degradation** — if an agent times out, the system returns a partial plan instead of crashing
→ **Static fallback catalogs** ensure quality output even when the LLM is rate-limited

### 🎯 What This Demonstrates

This project is a practical example of how **multi-agent AI systems** can decompose complex, real-world problems into specialized subtasks — a pattern that's increasingly relevant as AI moves from single-prompt interactions to orchestrated workflows.

The same architecture pattern applies to any domain where you need **research + planning + validation**: content pipelines, financial analysis, customer onboarding flows, and more.

🔗 **GitHub**: https://github.com/mathurkartik/AI-Travel-Agent

#AI #MultiAgentSystems #ProductManagement #FastAPI #React #LLM #TravelTech #BuildInPublic #Groq

---
