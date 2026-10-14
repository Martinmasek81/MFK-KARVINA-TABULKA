import json, re, sys
from pathlib import Path
import requests
from bs4 import BeautifulSoup
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
    text = ""
    status = 0
    # Nejprve běžný HTTP požadavek; může fungovat i tam, kde Chromium čeká na odpověď.
    try:
        response = requests.get(
            URL,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130.0 Safari/537.36",
                "Accept-Language": "cs-CZ,cs;q=0.9,en;q=0.8",
            },
            timeout=(10, 25),
        )
        status = response.status_code
        if response.ok:
            text = BeautifulSoup(response.content, "html.parser").get_text(" ", strip=True)
            print(f"HTTP načtení: {status}, textu {len(text)} znaků")
        else:
            print(f"HTTP požadavek vrátil stav {status}")
    except Exception as exc:
        print("Přímé HTTP načtení se nepodařilo:", str(exc)[:250])

    # Záložní pokus přes Chromium, pokud přímý požadavek nepřinesl obsah.
    if len(text.strip()) < 100:
        print("Zkouším načtení přes prohlížeč Chromium…")
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch()
                page = browser.new_page(locale="cs-CZ")
                try:
                    response = page.goto(URL, wait_until="domcontentloaded", timeout=20000)
                    page.wait_for_timeout(4000)
                    text = page.locator("body").inner_text(timeout=10000)
                    status = response.status if response else status
                finally:
                    browser.close()
        except Exception as exc:
            print("Načtení přes Chromium se nepodařilo:", str(exc)[:250])

    if status in (401, 403, 429) or len(text.strip()) < 100:
        raise RuntimeError(f"Fotbal.cz neposkytl použitelný obsah (HTTP {status}); HTML zůstává beze změny.")
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
