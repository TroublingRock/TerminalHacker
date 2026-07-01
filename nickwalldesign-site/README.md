# Nick Wall Design — TerminalHacker deploy bundle

Copy the `terminalhacker/` folder into the **root** of the nickwalldesign.com repository (alongside `magicbook/`, `shopquote/`, etc.).

## Deploy steps

1. Copy `terminalhacker/` → `<nickwalldesign.com-repo>/terminalhacker/`
2. Add the portfolio app entry from `portfolio-terminalhacker-entry.json` to the site's apps/projects config (same array as Etsy Pricing Calculator, Magic Book, ShopQuote AI).
3. Add sitemap URL: `https://nickwalldesign.com/terminalhacker`
4. Commit and push — Netlify will serve it at `/terminalhacker/` like the other subfolder apps.

## Notes

- This is a **landing page** for the Python desktop game. Source code lives at [TroublingRock/TerminalHacker](https://github.com/TroublingRock/TerminalHacker).
- Magic Book uses `appUrl: "/magicbook/"` — TerminalHacker follows the same pattern with `appUrl: "/terminalhacker/"`.
