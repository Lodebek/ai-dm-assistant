import json
import requests
import sys
import time

PAGE_11_TEXT = """
A2. The Mother Tree (CR 19)
A picturesque waterfall tumbles from the cliff above into a roiling pool that bubbles like a giant witch's cauldron. The waterfall gives off a frigid mist, but hot steam rises from the bubbling waters of the pool, combining with the mist to make a comfortable, if somewhat damp, locale. Colorful lichens grow on the rocks around the pool, and lush ferns grow from every fissure and seam in the rock. Numerous trees, ranging from shrublike saplings to fully grown specimens crowd the soil around the pool's edge. Just visible through the mist, a magnificent rowan tree with an immense trunk stands on a low ledge overlooking the pool. The lowest of its thin branches hang all the way down to dip into the surface of the pool, and its leaves constantly drip with condensation from the ever-present mist. Massive knots that almost resemble contorted faces look out from the tree's gnarled surface, and its fissured bark bears the scars of ancient lines carved into the tree that lost whatever symbolic meaning they may have had ages ago.

This rowan tree, called the Mother Tree, is 80 feet tall and over 30,000 years old, though it largely stopped growing thousands of years ago. Its extreme longevity is the result of its link to the primordial norn Vigliv, who was granted immortality by an ancient goddess as long as she remains in the grotto. The massive tree sits upon a ledge that stands 4 feet above the level of the roiling waters below.

Creature: A primordial norn named Vigliv inhabits the Mother Tree. Although bound to the mighty rowan, Vigliv is not actually a part of the tree. She is free to travel about Grandmother's Cauldron as she pleases, though she usually spends most of her time inside the tree's trunk using tree stride or jumping to one of the saplings that live throughout the grotto. Vigliv is fully detailed in the NPC Gallery on page 60.

When the PCs first arrive at the pool, Vigliv watches them from within her tree with some curiosity. When she sees the matryoshka doll in their possession, she immediately realizes that Baba Yaga is imprisoned inside and reveals herself...
"""

SYSTEM_PROMPT = """You are an expert Game Master assistant. Extract the specific text that matches the following categories. 
For each extracted piece of text, generate a normalized tag (e.g., 'npc_vigliv').

Categories:
1. GREEN: Read-Aloud dialogue, and the staging actions leading up to dialogue.
2. RED: Monster names, NPC names, and explicit page references to their stat blocks.
3. ORANGE: Environmental hazards, structural "Development" notes, and critical lore.
4. YELLOW: Mechanics, DCs, hidden triggers, and skill checks.

Return ONLY a valid JSON object matching this exact schema:
{
  "highlights": [
    {
      "color": "GREEN" | "RED" | "ORANGE" | "YELLOW",
      "exact_text_quote": "The exact sentence",
      "summary": "Brief summary",
      "tag": "normalized_entity_tag"
    }
  ]
}
"""

def test_ollama():
    url = "http://localhost:11434/api/generate"
    payload = {
        "model": "mistral:instruct",
        "prompt": f"{SYSTEM_PROMPT}\n\nPAGE TEXT:\n{PAGE_11_TEXT}",
        "stream": False,
        "format": "json",
        "options": {
            "temperature": 0.1
        }
    }
    
    print("Sending text to Mistral on Ollama (with 120 second timeout)...")
    start = time.time()
    try:
        response = requests.post(url, json=payload, timeout=120)
        end = time.time()
        if response.status_code == 200:
            result = response.json()
            print(f"Response received in {end-start:.2f} seconds!")
            print(json.dumps(json.loads(result['response']), indent=2))
        else:
            print("Error:", response.status_code, response.text)
    except requests.exceptions.Timeout:
        print("TIMEOUT ERROR: The model took longer than 120 seconds to respond.")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    test_ollama()
