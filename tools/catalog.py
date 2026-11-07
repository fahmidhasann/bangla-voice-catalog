#!/usr/bin/env python3
"""বাংলা ভয়েস ক্যাটালগ আপডেট টুল (ElevenLabs CLI লাগবে, `elevenlabs auth login` করা থাকতে হবে)।

ব্যবহার (রিপোর রুট ফোল্ডার থেকে):
  python3 tools/catalog.py find                     # লাইব্রেরিতে নতুন বাংলা ভয়েস আছে কিনা দেখায় (ক্রেডিট লাগে না)
  python3 tools/catalog.py add <voice_id> [M|F] [native|accent|multi]   # নতুন ভয়েস যোগ + ডেমো + যাচাই
  python3 tools/catalog.py regen --model eleven_v5  # নতুন মডেল এলে সব ভয়েস নতুন করে জেনারেট করে
  python3 tools/catalog.py verify                   # সব ক্লিপ speech-to-text দিয়ে আবার যাচাই করে
তারপর: git add -A && git commit -m "update" && git push
"""
import json, math, os, re, subprocess, sys
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "voices.json")
META = os.path.join(ROOT, "meta.json")
AUDIO = os.path.join(ROOT, "audio")


def cli(*args, raw=False):
    r = subprocess.run(["elevenlabs", *args, "--format", "raw" if raw else "json"], capture_output=True)
    if r.returncode:
        raise RuntimeError(r.stderr.decode()[:300])
    return r.stdout if raw else json.loads(r.stdout)


def load():
    return json.load(open(DATA, encoding="utf-8")), json.load(open(META, encoding="utf-8"))


def save(voices, meta):
    json.dump(voices, open(DATA, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump(meta, open(META, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def tts(v, meta):
    for _ in range(3):
        try:
            audio = cli("text-to-speech", "convert", "--voice-id", v["id"], "--model-id", meta["model"],
                        "--language-code", "bn", "--text", meta["script"], raw=True)
            open(os.path.join(AUDIO, v["id"] + ".mp3"), "wb").write(audio)
            print("ok   ", v["name"]); return
        except RuntimeError as e:
            err = e
    print("FAIL ", v["name"], err)


def norm(s):
    s = re.sub(r"[^ঀ-৿]", "", s)
    return s.replace("ী", "ি").replace("ূ", "ু").replace("ো", "")


def lev(a, b):
    p = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        c = [i]
        for j, y in enumerate(b, 1):
            c.append(min(p[j] + 1, c[j - 1] + 1, p[j - 1] + (x != y)))
        p = c
    return p[-1]


def verify(v, meta):
    d = cli("speech-to-text", "convert", "--file", os.path.join(AUDIO, v["id"] + ".mp3"),
            "--model-id", "scribe_v2", "--language-code", "bn")
    words = [w for w in d["words"] if w.get("type") == "word"]
    ref = norm(meta["script"])
    v["match"] = max(0, round(100 * (1 - lev(ref, norm(d["text"])) / len(ref))))
    v["conf"] = round(100 * math.exp(sum(w.get("logprob", 0) for w in words) / max(1, len(words))), 1)
    v["heard"] = d["text"]
    print(f"{v['match']:>3}% মিল  {v['conf']}% নিশ্চয়তা  {v['name']}")


def dur(v):
    r = subprocess.run(["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "csv=p=0",
                        os.path.join(AUDIO, v["id"] + ".mp3")], capture_output=True, text=True)
    try:
        v["dur"] = round(float(r.stdout), 1)
    except ValueError:
        pass


def run_all(fn, items, meta, workers=3):
    with ThreadPoolExecutor(workers) as ex:
        list(ex.map(lambda v: fn(v, meta), items))


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "help"
    voices, meta = load()
    if cmd == "find":
        have = {v["id"] for v in voices}
        seen = set()
        queries = [["--language", "bn"]] + [["--search", s] for s in ("bangla", "bengali", "bangladesh", "kolkata")]
        for q in queries:
            for page in range(3):
                res = cli("voices", "get_shared", *q, "--page-size", "100", "--page", str(page))
                for v in res.get("voices", []):
                    if v["voice_id"] in have or v["voice_id"] in seen:
                        continue
                    seen.add(v["voice_id"])
                    print(f"{v['voice_id']}  {v.get('gender', '?'):6} {v.get('language', '?'):3} {v['name'][:50]}")
                if not res.get("has_more"):
                    break
        print(f"\n{len(seen)}টা নতুন ভয়েস। যোগ করতে: python3 tools/catalog.py add <voice_id> M|F native|accent|multi")
    elif cmd == "add":
        vid = sys.argv[2]
        g = sys.argv[3] if len(sys.argv) > 3 else "M"
        tier = sys.argv[4] if len(sys.argv) > 4 else "accent"
        info = cli("voices", "get", "--voice-id", vid)
        name, _, desc = info["name"].partition(" - ")
        v = dict(id=vid, name=name.strip(), desc=desc.strip(), g=g, tier=tier, uses=0, pick=False)
        tts(v, meta); dur(v); verify(v, meta)
        voices = [x for x in voices if x["id"] != vid] + [v]
        save(voices, meta)
    elif cmd == "regen":
        if "--model" in sys.argv:
            meta["model"] = sys.argv[sys.argv.index("--model") + 1]
        run_all(tts, voices, meta)
        for v in voices:
            dur(v)
        run_all(verify, voices, meta)
        save(voices, meta)
    elif cmd == "verify":
        run_all(verify, voices, meta)
        save(voices, meta)
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
