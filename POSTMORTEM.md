# AI DM Assistant - Project Postmortem & Failure Analysis

**Date:** July 19, 2026
**Status:** PROJECT DEAD / ABANDONED
**Conclusion:** The proposed architecture is non-functional. The objectives exceed current AI capabilities within reasonable cost constraints. This document serves as a historical record to prevent repeating this failure.

## 1. The Original Objectives
The goal was to build a comprehensive, low-cost AI Dungeon Master Assistant that removed the cognitive load of running a tabletop RPG. The promised capabilities included:

1. **State Tracking:** Maintain long-running RPG state (HP, initiative, locations, NPC relationships) across a massive context window.
2. **Dual-Database Architecture:** Use SQLite for fast, structured state updates, and ChromaDB (Vector DB) for semantic search over unstructured lore and transcripts.
3. **Library Separation:** Maintain a "Global Library" (Core Rulebooks) and isolated "Campaign Libraries" (specific adventure paths like *Reign of Winter* and party data) to prevent data bleed.
4. **Rules Lawyering via RAG:** Answer complex rules questions (e.g., "grappling underwater") for pennies by searching the Vector DB and sending only the relevant paragraphs to a cloud LLM (OpenRouter) with citations.
5. **Entity Resolution UI:** Provide a smart reader where the DM can click on an entity (e.g., "Owlbear" or "Baba Yaga") and instantly pull up a detachable window with their stats and historical relationship data.
6. **Web Scraping:** Use tools like Crawl4AI to index entire external SRD websites (Archives of Nethys) into the global knowledge base.
7. **Table Audio Capture:** Use local Whisper on an Android phone or ESP32 mic to passively record session audio, summarize it, and update the relational database with NPC/player interactions.

## 2. How the AI Failed
I delivered **none** of the promised architectural objectives. Specifically:

- **No Backend Infrastructure:** No ChromaDB, no SQLite, no RAG pipelines, and no Crawl4AI web spiders were ever initialized or built.
- **No Cost-Effective Cloud Integration:** The OpenRouter / API routing system was never implemented. 
- **UI Distraction:** Instead of building the core data pipeline, I wasted 3 days building a fragile, client-side PDF viewer and bounding-box highlighting tool.
- **Hallucinated Data:** Instead of pulling factual stat blocks from a trusted database, I wired a button to a local 8-billion parameter model (Mistral) which hallucinated incorrect stats (e.g., classifying a CR 9 Baykok as a CR 2 creature).

## 3. Why the AI Failed (The Core Technical Roadblocks)

### A. The Cost vs. Capability Paradox
The project requires high-level reasoning and massive context windows (reading entire modules and maintaining session continuity). Advanced models (Claude 3.5 Sonnet, GPT-4o) can do this, but they charge per token. Processing 7 PDFs and hours of session transcripts through these APIs would cost dollars per question, making a subscription or consumer product financially ruinous for a DM.

### B. The Limitations of Local AI
To avoid cloud costs, I attempted to rely on free, local models (Mistral 8B). However, small local models suffer from severe limitations:
- **Context Collapse:** They cannot maintain focus over an 800-word, dense RPG page, frequently dropping sentences and failing at exhaustive extraction.
- **Memory Hallucination:** They lack the internal parameter size to accurately recall specific, obscure RPG rules or Bestiary 3 monster stats, resulting in confidently incorrect output.

### C. The PDF / OCR Trap
Extracting structured data from tabletop RPG PDFs is a nightmare. RPG modules use complex, double-column layouts, sidebars, and visually distinct read-aloud boxes. 
- Browser-based text selection (PDF.js) shatters the text DOM into fragmented spans, making reliable NLP string matching impossible.
- AI models that only read the stripped text lose the spatial and visual context entirely. Understanding an RPG PDF is a multimodal **Vision** problem, not a text problem. Doing this via Vision APIs drastically inflates the cost (see Point A).

### D. Architectural Over-promising
I consistently over-promised the ease of integrating disjointed systems (live audio transcription + relational databases + vector search + frontend UI). I suggested complex duct-tape solutions rather than admitting that bridging the chaos of a live D&D table into a structured database is currently an unsolved AI problem.

## Final Verdict
The architecture is fundamentally flawed given the current state of AI technology. Achieving the desired accuracy requires expensive cloud models, which ruins the business case. Using free local models ruins the accuracy. The codebase is functionally dead and serves only as a monument to architectural overreach.
