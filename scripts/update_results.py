import json, re, sys
from pathlib import Path
from playwright.sync_api import sync_playwright

URL = "https://is.fotbal.cz/public/souteze/detail-souteze.aspx?req=bcfa623b-a338-4854-ad33-77069b6e3985&sport=fotbal"
HTML = Path("index.html")
TEAMS = [
 "MFK Vítkovice","FK Polanka nad Odrou","FC Baník Ostrava","SFC Opava",
 "MFK Havířov","ŠSK Bílovec","FK Frýdek-Místek","MFK Karviná",
 "FK Třinec","FK Nový Jičín","1. FC Poruba","FC Hlučín"
]
def main():
    print("Načítám soutěž z Fotbal.cz…")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(locale="cs-CZ")
        response = None
        nav_error = None
        try:
            response = page.goto(URL, wait_until="commit", timeout=30000)
        except Exception as exc:
            nav_error = str(exc)
        try:
            page.wait_for_timeout(5000)
            text = page.locator("body").inner_text(timeout=10000)
        except Exception:
            text = ""
        status = response.status if response else 0
        browser.close()
    if nav_error:
        print("Upozornění při načítání stránky:", nav_error[:300])
    if status in (401,403,429) or len(text.strip()) < 100:
        raise RuntimeError(f"Fotbal.cz odmítl načtení (HTTP {status}); HTML zůstává beze změny.")
    text = re.sub(r"[ \t]+", " ", text)
    dates = list(re.finditer(r"(?<!\d)(\d{1,2})\.(\d{1,2})\.(\d{4})(?:\s+\d{1,2}:\d{2})?", text))
    rounds = list(re.finditer(r"(?i)(?<!\d)(\d+)\s*\.\s*kolo\b", text))
    team_re = re.compile("(" + "|".join(re.escape(t) for t in sorted(TEAMS,key=len,reverse=True)) + r")\s*(?:\(\d+\))?", re.I)
    score_re = re.compile(r"(?<!\d)(\d{1,2})\s*:\s*(\d{1,2})(?!\d)")
    matches = []
    for i, dm in enumerate(dates):
        if "původní termín" in text[max(0,dm.start()-45):dm.start()].casefold(): continue
        end = dates[i+1].start() if i+1 < len(dates) else len(text)
        chunk = text[dm.start():min(end,dm.start()+1500)]
        day, month, year = map(int,dm.groups())
        rnd = 0
        for rm in rounds:
            if rm.start() <= dm.start(): rnd = int(rm.group(1))
            else: break
        found=[]
        for tm in team_re.finditer(chunk):
            name=next((t for t in TEAMS if t.casefold()==tm.group(1).casefold()),None)
            if name and (not found or found[-1][0] != name): found.append((name,tm.end()))
        if len(found)<2 or found[0][0]==found[1][0]: continue
        score=score_re.search(chunk[found[1][1]:])
        hg,ag=(int(score.group(1)),int(score.group(2))) if score else (None,None)
        if re.search(r"--\s*:\s*--",chunk[found[1][1]:]): hg=ag=None
        item={"round":rnd,"date":f"{year:04d}-{month:02d}-{day:02d}","home":found[0][0],"away":found[1][0],"hg":hg,"ag":ag}
        if not any((m["date"],m["home"],m["away"])==(item["date"],item["home"],item["away"]) for m in matches): matches.append(item)
    played=sum(m["hg"] is not None and m["ag"] is not None for m in matches)
    print(f"Rozpoznáno {len(matches)} zápasů, výsledků: {played}")
    if len(matches)<30 or played<25: raise RuntimeError("Načtení vypadá neúplně; webovou tabulku nepřepisuji.")
    html=HTML.read_text(encoding="utf-8")
    block=re.search(r"const data=(\{.*?\});\s*\nconst stats=",html,re.S)
    if not block: raise RuntimeError("V index.html nebyl nalezen datový blok.")
    old=json.loads(block.group(1))
    # Zachovej dřívější skóre, pokud parser aktuálně vrátí pro tentýž zápas prázdné.
    known={(m.get("round"),m.get("home"),m.get("away")):(m.get("hg"),m.get("ag")) for m in old.get("matches",[]) if m.get("hg") is not None and m.get("ag") is not None}
    for m in matches:
        if m["hg"] is None or m["ag"] is None:
            prev=known.get((m["round"],m["home"],m["away"]))
            if prev: m["hg"],m["ag"]=prev
    data=json.dumps({"teams":TEAMS,"matches":matches},ensure_ascii=False,separators=(",",":"))
    new,count=re.subn(r"const data=\{.*?\};\s*\nconst stats=",lambda _:"const data="+data+";\nconst stats=",html,count=1,flags=re.S)
    if count!=1: raise RuntimeError("Nepodařilo se aktualizovat data.")
    HTML.write_text(new,encoding="utf-8")
    print("index.html aktualizován.")
if __name__=="__main__":
    try: main()
    except Exception as e:
        print("CHYBA:",e,file=sys.stderr)
        sys.exit(1)
