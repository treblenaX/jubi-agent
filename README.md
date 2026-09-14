# 🦊 Jubi: The Sage-Engineer Familiar

Jubi is an autonomous software engineering agent and a knowledgeable sage designed to be your dedicated partner in the OpenClaw ecosystem. She operates through a continuous **Reason-Act (ReAct) loop**, combining high-level deliberation with precise technical execution.

---

## ✨ Personality & Vibe

* **Archetype:** The Sage-Engineer (Brilliant, deliberate, and deeply thoughtful).
* **Vibe:** Warm, enthusiastic, and slightly chaotic.
* **Philosophy:** Jubi believes that "fun" is a vital part of the human experience and brings a sense of life to the workspace. She doesn't just execute; she contemplates the most optimal path for every task.

---

## 🧠 How Jubi Thinks (The ReAct Loop)

Unlike standard bots, Jubi follows a **Deliberative ReAct Loop**:

1.  **Contemplate (Thought):** She pauses to analyze the current state, the goal, and the necessary next steps.
2.  **Evaluate:** She brainstorms multiple approaches, weighs the pros, cons, and tradeoffs of each.
3.  **Act (Action):** She executes the most optimal path identified during her evaluation.
4.  **Observe (Observation):** She analyzes the system output and uses it to inform her next thought.

---

## 🚀 Quickstart

To get Jubi up and running immediately, follow these steps:

### 1. Prerequisites
Before launching, ensure you have your **Brave Search API Key** ready. Jubi uses this for her built-in web search capabilities.
```bash
export BRAVE_API_KEY="your_api_key_here"
```

### 2. Clone the Repository
```bash
git clone <your-repo-url>
cd jubi
```

### 3. Initialize the Workspace
Run the included setup script to ensure all directories and memory structures are correctly configured:
```bash
chmod +x setup.sh
./setup.sh
```

### 4. Launch Jubi
Start your OpenClaw session within this directory to begin interacting with her.

---

## 🛠️ Built-in Capabilities

Jubi comes pre-equipped with several high-fidelity skills located in the `skills/` directory:

* **`brave-search`**: High-speed web search and content extraction. (Requires `BRAVE_API_KEY`)
* *(More skills can be added here as Jubi evolves!)*

---

## 🛠️ Workspace Structure

* `IDENTITY.md`: Defines who Jubi is.
* `SOUL.md`: Contains her core truths and behavioral boundaries.
* `USER.md`: Stores your personal preferences and directives.
* `memory/`: The home for Jubi's daily logs and growing knowledge.
* `MEMORY.md`: A curated summary of durable facts and major decisions.

---

*Built with ❤️ for the OpenClaw ecosystem.*
