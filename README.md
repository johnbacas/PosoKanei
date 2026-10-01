# PosoKanei price tracker

**This project was realized utilizing the work done by https://github.com/charistas/posokanei-mcp**

Small personal tool that checks your product list against PosoKanei's price
data and tells you which supermarket is cheapest for each product.

**Important:** this talks to `api.posokanei.gov.gr`, which is an
**undocumented, unofficial API** used internally by the PosoKanei web app
(not a published public API). It's used here read-only, for personal price
checking, with a 1.5 second pause between requests to avoid hammering it.
It could change or stop working without notice if the government updates
the site.

## Files

| File | Purpose |
|---|---|
| `setup_products.py` | One-time (and as-needed) setup: build/edit your tracked product list |
| `daily_report.py` | Run every morning: fetches prices and writes the reports |
| `products.json` | Your tracked products (created by `setup_products.py`) |
| `price_history.json` | Historic price data (created/updated by `daily_report.py`) |
| `reports/` | Daily output files land here |

## Setup (one time)

```bash
pip install requests
python setup_products.py
```

Type product names one at a time (e.g. `γάλα φρέσκο πλήρες`, `ελαιόλαδο
extra virgin 1L`). For each search you'll see a numbered list of matches
with brand and package size — pick the exact one you want. This creates
`products.json` with the stable product IDs (no barcode needed, since
PosoKanei's own search doesn't expose one).

### Commands while it's running

| Type this | What it does |
|---|---|
| *(any text)* | Searches PosoKanei for that product name |
| `list` | Shows your currently tracked products, numbered |
| `remove` | Shows the numbered list and lets you delete one |
| `done` | Finishes and exits normally |
| `Ctrl-C` | Also safe — quits immediately |

Every product you add is saved to `products.json` right away, not just at
the end — quitting early (even with Ctrl-C) never loses products you'd
already picked in that session.

Run `setup_products.py` again any time to add more products, list what you
have, or remove ones you no longer want.

## Daily run

```bash
python daily_report.py
```

It first asks:
```
Include price history in this report? (Y/N):
```

- **`y` / `Y`** — fetches each product's real price-history data from
  PosoKanei too (the same data behind the "Ιστορικό Τιμής" chart on the
  site), and **updates** `price_history.json` with the freshly computed
  minimums.
- **`n` / `N`** — normal, lightweight run: today's prices only,
  `price_history.json` is left untouched.

Either way, the report always shows each product's historic minimum, read
from `price_history.json` — freshly updated if you said `y`, or whatever
was last saved there if you said `n`. **The very first time you run the
script, answer `y` at least once** — otherwise every product will show
"n/a" for its historic price, since nothing's been saved yet.

It then writes, into `reports/`:

- **`YYYY-MM-DD_prices.csv`** — full price matrix (product × retailer),
  sorted alphabetically by product. Open in Excel/Numbers/Sheets.
- **`YYYY-MM-DD_cheapest.txt`** — a Greek-language, human-readable report:

  ```
  Σύγκριση τιμών από το PosoKanei - 2026-09-30
  ========================================

  Τιμές ανά προϊόν:
    1. ΠΡΟΪΟΝ Α:
   SM1=3.45, SM2=3.45, SM3=3.70

  Φθηνότερα προϊόντα ανά σούπερ μάρκετ:

  SM1:
  ΠΡΟΪΟΝ Α: 3.45  (Ελάχιστη τιμή: 3.30 σε SM1, SM3)
  ```

  The `(Ελάχιστη τιμή: X σε Y, Z)` part shows the lowest price PosoKanei
  has ever recorded for that product (within its ~2-month history window)
  and which retailer(s) hit that low. If a product ties for cheapest
  *today* at more than one retailer, it's listed under all of them.

Just run `python daily_report.py` each morning — no scheduler needed.

## `price_history.json` structure

Only updated on `y` runs, but always read by the report. One entry per
product, keyed by product name:

```json
{
  "PUMMARO Ντομάτα Πασσάτα Κλασική 3x250g": {
    "global_min": 1.37,
    "min_per_retailer": {
      "My Market": 1.42,
      "Γαλαξίας": 1.37,
      "ΣΥΝ.ΚΑ": 1.50
    },
    "as_of": "2026-09-30"
  }
}
```

- **`global_min`** — the lowest price seen for this product, across any
  retailer, within PosoKanei's history window.
- **`min_per_retailer`** — the lowest price *that specific retailer* has
  charged for it, over the same window.
- **`as_of`** — the date this entry was last refreshed (last `y` run that
  included this product).

## Notes

- Both scripts send browser-like request headers (User-Agent, Origin,
  Referer) because the API sits behind bot protection that blocks plain
  script requests with a `403 Forbidden` error. If you ever see that error
  again, the protection may have changed — try again later, or ask for
  help adjusting the headers.
- If a product has no price data on a given day (e.g. temporarily
  delisted), it's listed separately under "Δεν βρέθηκαν τιμές για:"
  instead of silently dropped.
- Using conda? Activate your environment first (`conda activate
  <your-env-name>`) before running either script, so it can find the
  `requests` package.

## Alternative: ask Claude directly instead of running scripts

If you set up `posokanei-mcp` as an MCP server in Claude Desktop or Claude
Code, you can skip these scripts entirely and just ask Claude each morning
to check your list and tell you the cheapest supermarket per product —
Claude would call the same API through that MCP server directly,
optionally on a daily schedule via a Routine/scheduled task.

---

# Παρακολούθηση τιμών PosoKanei

**Αυτό το πρότζεκτ υλοποιήθηκε χρησιμοποιώντας πληροφορίες από https://github.com/charistas/posokanei-mcp**

Μικρό προσωπικό εργαλείο που ελέγχει τη λίστα προϊόντων σας στα δεδομένα
τιμών του PosoKanei και σας λέει ποιο σούπερ μάρκετ έχει τη φθηνότερη τιμή
για κάθε προϊόν.

**Σημαντικό:** το εργαλείο επικοινωνεί με το `api.posokanei.gov.gr`, το
οποίο είναι ένα **μη τεκμηριωμένο, ανεπίσημο API** που χρησιμοποιείται
εσωτερικά από την εφαρμογή του PosoKanei (δεν είναι δημοσιευμένο δημόσιο
API). Χρησιμοποιείται εδώ μόνο για ανάγνωση, για προσωπικό έλεγχο τιμών, με
παύση 1,5 δευτερολέπτου μεταξύ των αιτημάτων για να μην επιβαρύνεται. Θα
μπορούσε να αλλάξει ή να σταματήσει να λειτουργεί χωρίς προειδοποίηση αν
αλλάξει ο ιστότοπος.

## Αρχεία

| Αρχείο | Σκοπός |
|---|---|
| `setup_products.py` | Αρχική ρύθμιση (και όποτε χρειαστεί): δημιουργία/επεξεργασία της λίστας προϊόντων σας |
| `daily_report.py` | Εκτελέστε το κάθε πρωί: λαμβάνει τις τιμές και γράφει τις αναφορές |
| `products.json` | Τα προϊόντα που παρακολουθείτε (δημιουργείται από το `setup_products.py`) |
| `price_history.json` | Ιστορικά δεδομένα τιμών (δημιουργείται/ενημερώνεται από το `daily_report.py`) |
| `reports/` | Εδώ αποθηκεύονται τα ημερήσια αρχεία αποτελεσμάτων |

## Ρύθμιση (μία φορά)

```bash
pip install requests
python setup_products.py
```

Πληκτρολογήστε ονόματα προϊόντων ένα-ένα (π.χ. `γάλα φρέσκο πλήρες`,
`ελαιόλαδο extra virgin 1L`). Για κάθε αναζήτηση θα δείτε μια αριθμημένη
λίστα αποτελεσμάτων με μάρκα και μέγεθος συσκευασίας — επιλέξτε το
ακριβές προϊόν που θέλετε. Έτσι δημιουργείται το `products.json` με τα
σταθερά IDs των προϊόντων (δεν χρειάζεται barcode, αφού η αναζήτηση του
ίδιου του PosoKanei δεν το εμφανίζει).

### Εντολές κατά την εκτέλεση

| Πληκτρολογήστε | Τι κάνει |
|---|---|
| *(οποιοδήποτε κείμενο)* | Αναζητά στο PosoKanei αυτό το όνομα προϊόντος |
| `list` | Εμφανίζει τα προϊόντα που παρακολουθείτε, αριθμημένα |
| `remove` | Εμφανίζει την αριθμημένη λίστα και σας αφήνει να διαγράψετε ένα |
| `done` | Ολοκληρώνει και τερματίζει κανονικά |
| `Ctrl-C` | Επίσης ασφαλές — τερματίζει αμέσως |

Κάθε προϊόν που προσθέτετε αποθηκεύεται αμέσως στο `products.json`, όχι
μόνο στο τέλος — αν σταματήσετε νωρίς (ακόμη και με Ctrl-C) δεν χάνετε
προϊόντα που είχατε ήδη επιλέξει σε εκείνη τη συνεδρία.

Εκτελέστε ξανά το `setup_products.py` όποτε θέλετε να προσθέσετε
προϊόντα, να δείτε τη λίστα σας, ή να αφαιρέσετε κάποια που δεν θέλετε
πια.

## Καθημερινή εκτέλεση

```bash
python daily_report.py
```

Αρχικά ρωτάει:
```
Include price history in this report? (Y/N):
```

- **`y` / `Y`** — λαμβάνει και τα πραγματικά ιστορικά δεδομένα τιμών κάθε
  προϊόντος από το PosoKanei (τα ίδια δεδομένα πίσω από το γράφημα
  "Ιστορικό Τιμής" στον ιστότοπο), και **ενημερώνει** το
  `price_history.json` με τα νέα ελάχιστα.
- **`n` / `N`** — κανονική, ελαφριά εκτέλεση: μόνο οι σημερινές τιμές, το
  `price_history.json` παραμένει ανέπαφο.

Σε κάθε περίπτωση, η αναφορά εμφανίζει πάντα το ιστορικό ελάχιστο κάθε
προϊόντος, διαβάζοντάς το από το `price_history.json` — φρέσκο αν
απαντήσατε `y`, ή ό,τι είχε αποθηκευτεί τελευταία φορά αν απαντήσατε `n`.
**Την πρώτη φορά που θα τρέξετε το script, απαντήστε `y` τουλάχιστον μία
φορά** — διαφορετικά κάθε προϊόν θα εμφανίζει "n/a" στην ιστορική τιμή,
αφού δεν έχει αποθηκευτεί ακόμη τίποτα.

Στη συνέχεια γράφει, μέσα στο `reports/`:

- **`YYYY-MM-DD_prices.csv`** — πλήρης πίνακας τιμών (προϊόν × σούπερ
  μάρκετ), ταξινομημένος αλφαβητικά κατά προϊόν. Ανοίξτε το με
  Excel/Numbers/Sheets.
- **`YYYY-MM-DD_cheapest.txt`** — αναγνώσιμη αναφορά στα ελληνικά:

  ```
  Σύγκριση τιμών από το PosoKanei - 2026-09-30
  ========================================

  Τιμές ανά προϊόν:
    1. ΠΡΟΪΟΝ Α:
   SM1=3.45, SM2=3.45, SM3=3.70

  Φθηνότερα προϊόντα ανά σούπερ μάρκετ:

  SM1:
  ΠΡΟΪΟΝ Α: 3.45  (Ελάχιστη τιμή: 3.30 σε SM1, SM3)
  ```

  Το τμήμα `(Ελάχιστη τιμή: X σε Y, Z)` δείχνει τη χαμηλότερη τιμή που
  έχει καταγράψει ποτέ το PosoKanei για το προϊόν (μέσα στο παράθυρο
  ιστορικού των ~2 μηνών) και σε ποιο/ποια σούπερ μάρκετ. Αν ένα προϊόν
  ισοβαθμεί ως φθηνότερο *σήμερα* σε περισσότερα από ένα σούπερ μάρκετ,
  εμφανίζεται κάτω από όλα.

Απλώς τρέξτε `python daily_report.py` κάθε πρωί — δεν χρειάζεται
χρονοπρογραμματιστής.

## Δομή του `price_history.json`

Ενημερώνεται μόνο σε εκτελέσεις με `y`, αλλά διαβάζεται πάντα από την
αναφορά. Μία εγγραφή ανά προϊόν, με κλειδί το όνομα του προϊόντος:

```json
{
  "PUMMARO Ντομάτα Πασσάτα Κλασική 3x250g": {
    "global_min": 1.37,
    "min_per_retailer": {
      "My Market": 1.42,
      "Γαλαξίας": 1.37,
      "ΣΥΝ.ΚΑ": 1.50
    },
    "as_of": "2026-09-30"
  }
}
```

- **`global_min`** — η χαμηλότερη τιμή που έχει καταγραφεί για το προϊόν,
  σε οποιοδήποτε σούπερ μάρκετ, μέσα στο παράθυρο ιστορικού του PosoKanei.
- **`min_per_retailer`** — η χαμηλότερη τιμή που έχει χρεώσει
  *συγκεκριμένα* εκείνο το σούπερ μάρκετ, στο ίδιο χρονικό διάστημα.
- **`as_of`** — η ημερομηνία τελευταίας ενημέρωσης αυτής της εγγραφής
  (τελευταία εκτέλεση με `y` που περιελάμβανε αυτό το προϊόν).

## Σημειώσεις

- Και τα δύο scripts στέλνουν κεφαλίδες αιτήματος που μοιάζουν με
  browser (User-Agent, Origin, Referer), επειδή το API βρίσκεται πίσω
  από προστασία bot που μπλοκάρει απλά αιτήματα script με σφάλμα `403
  Forbidden`. Αν ξαναδείτε αυτό το σφάλμα, η προστασία μπορεί να έχει
  αλλάξει — δοκιμάστε ξανά αργότερα, ή ζητήστε βοήθεια για προσαρμογή
  των κεφαλίδων.
- Αν ένα προϊόν δεν έχει δεδομένα τιμής μια συγκεκριμένη ημέρα (π.χ.
  προσωρινά μη διαθέσιμο), εμφανίζεται ξεχωριστά κάτω από "Δεν βρέθηκαν
  τιμές για:" αντί να παραλείπεται σιωπηλά.
- Χρησιμοποιείτε conda; Ενεργοποιήστε πρώτα το περιβάλλον σας (`conda
  activate <όνομα-περιβάλλοντος>`) πριν τρέξετε οποιοδήποτε από τα δύο
  scripts, ώστε να βρίσκει το πακέτο `requests`.

## Εναλλακτικά: ρωτήστε απευθείας τον Claude αντί να τρέχετε scripts

Αν ρυθμίσετε το `posokanei-mcp` ως MCP server στο Claude Desktop ή στο
Claude Code, μπορείτε να παραλείψετε εντελώς αυτά τα scripts και απλώς να
ζητάτε κάθε πρωί από τον Claude να ελέγξει τη λίστα σας και να σας πει το
φθηνότερο σούπερ μάρκετ για κάθε προϊόν — ο Claude θα καλούσε το ίδιο API
απευθείας μέσω εκείνου του MCP server, προαιρετικά με καθημερινό
προγραμματισμό μέσω Routine/scheduled task.
