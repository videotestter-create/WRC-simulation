# WRC Rally Saudi Arabia 2025 – Live Simulation Dashboard

Tento dashboard:
- Načítá **Stage Results** z eWRC (včetně *Average Speed*),
- počítá **ETA dojezdu** etap podle délky a průměrné rychlosti,
- simuluje **pořadí šampionátu** podle aktuálních pozic (placeholder),
- ukazuje grafy rozdílů bodů.

## Nasazení na Streamlit Cloud (bez instalace lokálně)
1. Vytvoř si účet na https://streamlit.io/cloud.
2. Založ veřejný GitHub repozitář a nahraj soubory:
   - `app.py` (dashboard),
   - `requirements.txt`.
3. Ve Streamlit Cloud zvol **Deploy a public app from GitHub** a nastav `app.py` jako hlavní soubor.

## Lokální spuštění (volitelné)
```bash
pip install -r requirements.txt
streamlit run app.py
```

Poznámka: Struktura eWRC se může měnit, scraper je **best-effort**. Pro 100% jistotu live pořadí zvaž napojení na oficiální live timing WRC.
