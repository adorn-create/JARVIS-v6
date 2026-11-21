import base64, io, os, requests
from dotenv import load_dotenv
from PIL import ImageGrab
ROOT=os.path.dirname(os.path.dirname(__file__)); load_dotenv(os.path.join(ROOT,".env"))
def analyze_screen(question="Describe my screen and help with the task.",model=None):
    key=os.getenv("OPENROUTER_API_KEY","").strip(); model=model or os.getenv("OPENROUTER_VISION_MODEL","openai/gpt-4o-mini")
    if not key: raise RuntimeError("OpenRouter API key missing in .env")
    image=ImageGrab.grab(); buf=io.BytesIO(); image.save(buf,format="JPEG",quality=80); data=base64.b64encode(buf.getvalue()).decode("ascii")
    payload={"model":model,"messages":[{"role":"user","content":[{"type":"text","text":question},{"type":"image_url","image_url":{"url":"data:image/jpeg;base64,"+data}}]}],"max_tokens":700}
    r=requests.post("https://openrouter.ai/api/v1/chat/completions",headers={"Authorization":f"Bearer {key}","Content-Type":"application/json","HTTP-Referer":"http://localhost","X-Title":"JARVIS"},json=payload,timeout=120)
    if not r.ok: raise RuntimeError(f"Vision API error {r.status_code}: {r.text[:500]}")
    return r.json()["choices"][0]["message"].get("content","")
