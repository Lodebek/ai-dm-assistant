# AI Dungeon Master Assistant - Project Notes & Feasibility Study

**Status:** Paused / Under Consideration
**Date:** July 2026

## 1. The Core Concept
Build an AI assistant for Tabletop RPG Game Masters that can keep track of long-running RPG state (hit points, locations, past events, table transcripts) over a huge amount of context. The AI would answer complex questions (e.g., "what should the goblin do on its initiative?") based on the current world state.

### Planned Architecture
*   **Phase 1 (IDE Prototype):** Rely on Text-Based Memory Files maintained locally.
    *   `world_lore.md`: Static world facts, history, rules.
    *   `session_transcript.md`: Running log of table events.
    *   `current_state.md`: Structured file tracking fast-changing state (HP, location, initiative).
*   **Phase 2 (Standalone App):** 
    *   **Relational DB (SQLite):** For rapid, structured state tracking (HP, inventory, coordinates).
    *   **Vector DB (ChromaDB/Pinecone):** For semantic search across massive amounts of unstructured text (session transcripts, world lore) using Retrieval-Augmented Generation (RAG).

## 2. Technical Feasibility & VTT Integration
To be truly useful, the AI needs to understand the spatial and tactical reality of the game (the map, token positions).
*   **Roll20:** Not viable. It is a closed, sandboxed ecosystem with no external API for real-time state extraction.
*   **Foundry VTT:** Viable. It has an open ecosystem where a custom "Bridge Module" could be written to expose real-time token coordinates and combat state to our external application.
*   **Conclusion:** Technical execution is possible, but requires targeting Foundry VTT and building an API bridge.

## 3. The "Garbage In, Garbage Out" Audio Problem
How does the AI capture in-character narrative moments (e.g., "The Bard insulted the Goblin Chief") out of chaotic voice chat (Zoom/Discord) filled with out-of-character cross-talk and pizza orders?
*   **Real-time dictation/parsing:** Considered too difficult and fragile ("boiling the ocean").
*   **Proposed Solutions:**
    1.  **Post-Session Processing:** Take a post-game transcript from tools like Fathom, feed it to a cheap LLM (like Haiku/Flash) prompted specifically to extract *only* narrative events, and update the memory files offline.
    2.  **DM "Push-to-Lore" Button:** The DM manually types key events into a UI box during the game to update the AI's memory reliably.

## 4. Business Case & Monetization Concerns (The Roadblock)
Several major concerns were raised regarding the viability of this as a business or a portfolio piece:
*   **Small Market Size:** You only need 1 DM per group of 4-7 players, severely limiting the Total Addressable Market.
*   **Subscription Fatigue:** Users already pay for VTT licenses (Foundry) and digital modules. Asking for a recurring subscription for an assistant is a tough sell.
*   **Variable Token Costs:** Every LLM query costs money. If a user pays a flat subscription, heavy users could cost the service money.
*   **Market Solutions:** While other tools (like Loremaster VTT) solve this via "Bring Your Own Key" (BYOK) models or tightly metered token limits, the underlying market size remains a concern.

## 5. Final Thoughts
The project was paused because the required effort (building VTT bridges, structuring memory pipelines, solving the audio-to-lore gap) feels too high given the small target audience and low likelihood of significant financial return. Furthermore, it may not serve as the most impressive "tech demo" for sharpening generalized engineering skills, as much of the effort would be spent fighting VTT integrations rather than core AI architecture.
