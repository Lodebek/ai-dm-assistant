import urllib.request
import json

try:
    req = urllib.request.Request('https://openrouter.ai/api/v1/models')
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode())['data']
        
        res = []
        for m in data:
            id = m['id'].lower()
            if 'gemini' in id or 'llama' in id or 'claude' in id:
                try:
                    p = float(m['pricing']['prompt']) * 1000000
                    c = float(m['pricing']['completion']) * 1000000
                    res.append((m['id'], p, c))
                except:
                    pass
                    
        res.sort(key=lambda x: x[1])
        print('--- CURRENT 2026 MODELS & PRICING (per 1M tokens) ---')
        for r in res:
            if 'gemini' in r[0].lower():
                print(f'{r[0]}: ${r[1]:.4f} in / ${r[2]:.4f} out')
        print('\n--- TOP CLAUDE/LLAMA MODELS ---')
        for r in res:
            if 'claude-3.5' in r[0].lower() or 'llama-3.1' in r[0].lower():
                print(f'{r[0]}: ${r[1]:.4f} in / ${r[2]:.4f} out')
except Exception as e:
    print(f"Error: {e}")
