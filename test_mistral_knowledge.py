import requests

prompt = "You are an expert Pathfinder 1e Game Master. Provide the stat block summary (CR, HP, AC, Attacks, Special Abilities) for a 'Baykok'."
response = requests.post("http://localhost:11434/api/generate", json={"model": "mistral:instruct", "prompt": prompt, "stream": False})
print(response.json()["response"])
