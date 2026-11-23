# Blind Squirrel Energy

*Even a blind squirrel finds the cheapest plan.*

A Texas electricity plan finder. Upload a year of your Smart Meter Texas usage and the site prices every plan in your area against your real month-by-month kWh. It shows the three plans that cost you the least, what each monthly bill would be, and (optionally) whether it's worth paying your early termination fee to switch now.

Everything runs in the visitor's browser. Usage files and EFLs are never uploaded to a server.

## What's in here

| Path | What it is |
|---|---|
| `index.html` | The whole site: layout, styles, CSV/EFL parsing and the cost engine |
| `plans.json` | Plan list from Power to Choose (one plan per line) |
| `meta.json` | Date the plan list was last refreshed (shown in the footer) |
| `logo.webp` | Logo with transparent background |
| `data/verified.json` | Hand-verified EFL pricing, keyed by Power to Choose plan ID |
| `data/logo-original.jpg` | Original logo artwork |
| `scripts/update_plans.py` | Refreshes `plans.json` from Power to Choose |
| `.github/workflows/refresh-plans.yml` | Runs the refresh daily and commits changes |

## Run it locally

`index.html` loads `plans.json` with `fetch`, so it needs a web server (opening the file directly won't work):

```bash
python3 -m http.server 8000
# then open http://localhost:8000
```

## Publish with GitHub Pages

1. Push this folder to a GitHub repository.
2. **Settings → Pages → Build and deployment**: Source = *Deploy from a branch*, Branch = `main`, folder = `/ (root)`.
3. The site appears at `https://<your-user>.github.io/<repo>/`. Add a custom domain in the same screen if you have one.

## Keeping prices fresh

The workflow in `.github/workflows/refresh-plans.yml` runs `scripts/update_plans.py` every morning and commits the new `plans.json`. You can also run it by hand from the **Actions** tab (*Refresh plan prices → Run workflow*) or locally:

```bash
python3 scripts/update_plans.py
```

The script refuses to overwrite `plans.json` if fewer than 50 plans come back, so a bad response won't wipe the site.

To cover more of Texas, add ZIP codes to `ZIPS` in the script (for example one Oncor, AEP Central and AEP North ZIP) and add those utilities to the dropdown in `index.html`.

## How plans are priced

- **Verified plans** (`data/verified.json`): priced from the full EFL (energy charge, base charge, bill credits or free-hours windows) plus CenterPoint delivery charges ($4.90/month + 6.5611¢/kWh as of Nov 2026; update `TDU` in `index.html` when CenterPoint changes rates).
- **All other plans**: estimated from the EFL's average prices at 500, 1,000 and 2,000 kWh. Bill-credit plans are detected and flagged. Because EFLs round those averages, plans within ~$60/yr are shown as tied.
- **Free nights/weekends plans** are priced only when verified and only with 15-minute interval data.

To verify a plan, read its EFL and add an entry to `data/verified.json`:

```json
"39240": { "kind": "flat", "e": 4.72, "base": 0, "note": "Energy 4.72¢/kWh, no base charge" }
```

Bill credit: add `"credit": [1000, 125]` (minimum kWh, dollars). Free-hours plan: `{"kind":"tou","base":9.95,"day":6.59,"night":0,"from":23,"to":6}`.

## Known limits (prototype)

- Plan data covers CenterPoint and TNMP (ZIP 77584) only.
- Only a handful of plans have verified EFL pricing.
- Reading a visitor's current EFL is best effort; the fields stay editable.
- Not an electricity provider. Before earning referral fees, check Texas PUC broker registration rules.
