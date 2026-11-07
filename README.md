# বাংলা ভয়েস ক্যাটালগ

ElevenLabs-এর যেসব ভয়েস বাংলা বলতে পারে, সেগুলোর ডেমো (মডেল `eleven_v4`, সব ভয়েসে একই লাইন)।

🔗 https://fahmidhasann.github.io/bangla-voice-catalog/

## আপডেট করা (ElevenLabs CLI লাগবে)

```bash
python3 tools/catalog.py find                       # নতুন বাংলা ভয়েস খোঁজা (ক্রেডিট লাগে না)
python3 tools/catalog.py add <voice_id> M native    # নতুন ভয়েস যোগ
python3 tools/catalog.py regen --model eleven_v5    # নতুন মডেলে সব আবার জেনারেট
git add -A && git commit -m "update" && git push
```

`voices.json` = ভয়েস তালিকা · `meta.json` = মডেল আর ডেমো স্ক্রিপ্ট · `audio/` = ক্লিপ
