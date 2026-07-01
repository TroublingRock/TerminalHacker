# Hubpage — TerminalHacker subfolder deploy

Copy `terminalhacker/` into the **root** of the **hubpage** repo (alongside `magicbook/`, `shopquote/`, etc.). Netlify publishes hubpage as nickwalldesign.com.

## Deploy steps (when ready)

1. Copy `terminalhacker/` → `hubpage/terminalhacker/`
2. Add the portfolio app entry from `portfolio-terminalhacker-entry.json` to the site's apps config (same array as Magic Book and ShopQuote AI).
3. Add sitemap URL: `https://nickwalldesign.com/terminalhacker`
4. Push hubpage — Netlify serves it at `/terminalhacker/` like the other subfolder apps.

## Notes

- This is a **landing page** for the Python desktop game. Source code lives at [TroublingRock/TerminalHacker](https://github.com/TroublingRock/TerminalHacker).
- Magic Book uses `appUrl: "/magicbook/"` — TerminalHacker uses `appUrl: "/terminalhacker/"`.
- Adding TerminalHacker as a **separate** Netlify site does not create the `/terminalhacker/` path on nickwalldesign.com; the folder must live in hubpage.
- Play locally anytime: `python3 main.py` (no GitHub push or Netlify required).
