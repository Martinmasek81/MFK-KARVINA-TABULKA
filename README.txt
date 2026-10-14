MFK Karviná U11 – PWA
======================

Obsah:
- index.html: aplikace
- manifest.webmanifest: nastavení instalace
- service-worker.js: základní offline cache
- icon-192.png a icon-512.png: ikony aplikace

DŮLEŽITÉ:
Aby šla aplikace na iPhonu přidat na plochu jako PWA, musí být zveřejněná přes HTTPS.
Tento balíček sám o sobě ještě není veřejná internetová adresa.

Jednoduché bezplatné zveřejnění:
1. Vytvoř účet na GitHubu, pokud ho nemáš.
2. Vytvoř nový veřejný repozitář, například mfk-karvina-u11.
3. Nahraj do něj všechny soubory z tohoto balíčku.
4. V repozitáři otevři Settings → Pages.
5. U Build and deployment vyber Deploy from a branch, větev main a složku /(root), pak Save.
6. Po zveřejnění otevři v iPhonu adresu, kterou GitHub Pages ukáže, v Safari.
7. Klepni na Sdílet → Přidat na plochu.

Poznámka k výsledkům:
Aplikace zatím zobrazuje data vložená v index.html. Offline režim ukládá aplikaci do cache.
Samotná PWA zatím neumí bezpečně a automaticky získávat nové výsledky z Fotbal.cz; stránka FAČR dříve vracela HTTP 403. Aktualizaci dat je nutné vyřešit samostatně (například aktualizačním skriptem a následným nahráním nového index.html).
