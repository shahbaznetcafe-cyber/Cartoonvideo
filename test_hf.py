"""
HuggingFace LLM test/benchmark.
Pehle .env mein token daalein:  HF_TOKEN=hf_xxx   (aur chahein to HF_MODEL=...)

Chalao:  python test_hf.py
Do cheezein test karta hai:
  1) seedha InferenceClient (aap wala tareeqa)
  2) app ke unified providers.llm_generate (LLM_PROVIDER=huggingface)
"""
import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")

import config

TOKEN = (os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_API_KEY")
         or os.getenv("HUGGINGFACEHUB_API_TOKEN"))
MODEL = config.HF_MODEL

if not TOKEN:
    print("[!] HF_TOKEN nahi mila. .env mein daalein:  HF_TOKEN=hf_xxxxx")
    print("    Token: https://huggingface.co/settings/tokens (Read).")
    print(f"    Note: '{MODEL}' gated model hai — pehle uske page par license accept karein,")
    print("    ya .env mein non-gated model set karein, e.g.:")
    print("      HF_MODEL=mistralai/Mistral-7B-Instruct-v0.3")
    print("      HF_MODEL=Qwen/Qwen2.5-7B-Instruct")
    sys.exit(1)


def test_direct():
    from huggingface_hub import InferenceClient
    client = InferenceClient(MODEL, token=TOKEN)
    start = time.time()
    resp = client.chat_completion(
        [{"role": "user", "content": "2 line Urdu joke banao"}],
        max_tokens=200, temperature=0.8)
    dt = time.time() - start
    print(f"\n=== 1) InferenceClient ({MODEL}) ===")
    print(f"Time: {dt:.1f}s")
    print(resp.choices[0].message.content)


def test_providers():
    import providers
    config.LLM_PROVIDER = "huggingface"
    config.LLM_FALLBACK = ["huggingface"]   # sirf HF (fallback masking na ho)
    start = time.time()
    out = providers.llm_generate(
        "You are a witty Urdu comedian.", "2 line Urdu joke banao",
        max_tokens=200, temperature=0.8)
    dt = time.time() - start
    print(f"\n=== 2) providers.llm_generate (huggingface) ===")
    print(f"Time: {dt:.1f}s")
    print(out)


if __name__ == "__main__":
    try:
        test_direct()
    except Exception as e:
        print(f"\n[direct fail] {type(e).__name__}: {str(e)[:200]}")
    try:
        test_providers()
    except Exception as e:
        print(f"\n[providers fail] {type(e).__name__}: {str(e)[:200]}")
