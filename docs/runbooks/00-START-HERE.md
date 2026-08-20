# Start Here — Plain English

You do not need to write any code. You need to **install three programs, paste some
commands, and read what comes back**. Every command below is copy-paste. Nothing here
touches real money — the platform does not place trades.

Total time: about 45 minutes, most of it downloads.

---

## What you are actually doing

Think of it as building a filing cabinet before doing research:

1. **Install the tools** — Python (runs the code), Docker (runs the database), Git (downloads the code).
2. **Download the project** onto your computer.
3. **Start the database** — an empty filing cabinet.
4. **Get a free Alpaca account** — that is where price history comes from.
5. **Download price history** into the cabinet.
6. **Prove the prices are correct** — compare against a totally separate source. This is the gate. If it fails, stop.
7. **Compute the indicators** and see what the setups actually do.

Steps 1–4 are setup you do once. Steps 5–7 you will re-run often.

---

## Step 1 — Install three programs (once)

**On Mac:**

Open the app called **Terminal** (press Cmd+Space, type "terminal", Enter). This is where every
command in this guide gets pasted. Paste this line and press Enter:

```bash
xcode-select --install
```

Click through the installer if it appears. Then install Docker Desktop from
<https://www.docker.com/products/docker-desktop/> — download, drag to Applications, open it,
and **leave it running**. You will see a whale icon in the top menu bar. That whale must be
there whenever you use the platform.

Then check Python:

```bash
python3 --version
```

If it prints 3.11 or higher, you are done. If it prints something lower or errors, install
Python from <https://www.python.org/downloads/>.

**On Windows:**

Install these three, in this order, accepting all defaults **except where noted**:

1. Python from <https://www.python.org/downloads/> — **tick the box "Add python.exe to PATH"** on the first screen. This matters; if you miss it, nothing else works.
2. Git from <https://git-scm.com/download/win>
3. Docker Desktop from <https://www.docker.com/products/docker-desktop/> — open it after installing and leave it running.

Then open the app called **Terminal** or **PowerShell** (press the Windows key, type "powershell",
Enter). That is where every command gets pasted.

> **The one Windows difference:** wherever this guide shows `source .venv/bin/activate`,
> you type `.venv\Scripts\activate` instead. That is the only change.

---

## Step 2 — Download the project (once)

Paste these one line at a time, pressing Enter after each and waiting for it to finish:

```bash
cd ~
git clone https://github.com/KY762/SCREENERV12.git
cd SCREENERV12
git checkout claude/trading-platform-design-9i2pba
```

You now have a folder called `SCREENERV12` in your home directory with all the code in it.

**What `cd` means:** "go into this folder." The terminal is always sitting inside one folder,
and commands only work in the right one. If a command later says "no such file" or "command not
found", the fix is almost always to paste `cd ~/SCREENERV12` first and try again.

---

## Step 3 — Set up Python (once)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

The last one takes a few minutes and prints a lot of text. That is normal.

**What just happened:** `.venv` is a private box holding this project's Python libraries so it
cannot break anything else on your computer. `activate` steps into that box. `pip install`
fills it.

> **Important, and easy to forget:** every time you open a **new** terminal window, you must
> run these two lines again before anything else works:
>
> ```bash
> cd ~/SCREENERV12
> source .venv/bin/activate
> ```
>
> You will know it worked because your prompt gets `(.venv)` at the front. If you see an error
> like `command not found: screener`, this is what you forgot.

Now confirm the code itself is sound:

```bash
pytest -q
```

**Expect:** a row of dots and a green line saying all tests passed. That means the math —
every indicator, every pattern, every position-size calculation — matches values that were
worked out by hand. If anything says FAILED, stop and send me the output.

---

## Step 4 — Get free Alpaca keys (once)

1. Go to <https://alpaca.markets> and sign up. Free.
2. Switch to **Paper Trading** (the toggle in the sidebar). Paper means fake money — we only want the price data, but this keeps you away from anything live.
3. Find **API Keys** → **Generate**.
4. You get two strings: a **Key ID** and a **Secret Key**. **The secret is shown exactly once.** Copy both somewhere immediately.

Now put them in the project. Create your settings file:

```bash
cp .env.example .env
open .env          # Windows: notepad .env
```

A text editor opens. Find these two lines:

```
ALPACA_API_KEY_ID=
ALPACA_API_SECRET_KEY=
```

Paste your key after the first `=`, your secret after the second. No spaces, no quotes.
Ignore every other line in the file — none of them are needed yet. Save and close.

This file is git-ignored, meaning your keys never leave your computer.

---

## Step 5 — Start the database (once per computer restart)

Make sure Docker Desktop is open (whale icon visible), then:

```bash
docker compose up -d
screener db init
```

**Expect:** Docker prints a line about starting `screener-postgres`, and `db init` confirms the
tables were created. You now have an empty database with somewhere to put prices, indicators,
and universe membership.

You only run `db init` once ever. You run `docker compose up -d` again after any computer
restart — it is harmless to run when it is already running.

---

## Step 6 — Download price history

```bash
screener ingest --symbols SPY,QQQ,AAPL --start 2019-01-01
```

**Expect:** `succeeded` in green, with a count of bars stored. Takes under a minute for three
symbols.

Look at what arrived:

```bash
screener show SPY -n 10
```

That prints the last ten days of SPY as a table.

**This command is safe to re-run any time.** Running it again over the same dates changes
nothing — it only fills in what is missing. You cannot create duplicates or corrupt the data
by running it twice.

---

## Step 7 — THE GATE: prove the prices are right

This is the most important command in the entire project.

```bash
screener verify
```

**What it does:** takes the most recent bars we stored from Alpaca and compares them against
Stooq — a completely separate data source that shares no code and no vendor with us. If both
independently report the same prices to the cent, the data is real.

**Green / PASS** → Phase 1 is complete. Everything built on top of these prices rests on
solid ground. Continue to Step 8.

**Red / FAIL** → **Stop.** Do not continue. Send me the output. Running research on wrong
prices produces confident, wrong answers, which is worse than no answers.

Volume differing is expected and is not a failure — the free Alpaca feed only sees one
exchange. **Prices** are what must match.

---

## Step 8 — Compute indicators

```bash
screener metrics build
```

This reads the raw prices and calculates every moving average, ATR, relative volume, relative
strength, and distance-from-high, then stores them.

See one:

```bash
screener metrics show SPY -n 10
```

Nothing is guessed here — every number traces to a tested formula. And this whole table can be
deleted and rebuilt from the raw prices at any time, so it is impossible to permanently corrupt.

---

## Step 9 — See what the setups actually do

```bash
screener diagnose signals --symbols SPY,QQQ,AAPL
```

**This runs before any backtest, on purpose, and it answers two questions that can kill a
strategy for free:**

**Question 1 — does the setup select anything?**
It prints how often each setup (H2 fair-value gap, H3 sweep-reclaim, H4 inverse FVG) fires.
A rule that fires on 40% of days is not a signal, it is a description of the market. A rule
that fires four times in seven years cannot be evaluated at all.

**Question 2 — are these actually different ideas?**
It prints an overlap matrix. H3 and H4 are both "a level got broken and then reclaimed"
stories. If they fire on the same days, they are one idea with two names, and counting both
as evidence would be counting the same fact twice.

**The decision rule, written down in advance so it cannot be bent later:** if H4 overlaps H3
by more than 60%, H4 stops being its own hypothesis and gets folded into H3. Send me the
numbers and I will make that call with you.

Also run:

```bash
screener diagnose redundancy
```

Same idea, applied to indicators: any indicator that correlates above 0.85 with one we
already have is dropped. It is costing a parameter and contributing nothing.

---

## Step 10 — Scale up when the above works

Everything so far used three symbols so mistakes are cheap and fast. Once Step 7 passes and
Steps 8–9 make sense, widen it:

```bash
screener ingest --symbols SPY,QQQ,AAPL,MSFT,NVDA,AMZN,META,GOOGL,TSLA,AMD --start 2010-01-01
screener metrics build
screener universe build
```

`universe build` decides, **for each individual day in history**, which stocks were liquid
enough to trade *on that day* — using only what was knowable then. This is not a technicality.
Screening ten years of history against today's list of big companies means you only ever test
stocks that survived and grew, which makes any strategy look brilliant. This avoids that.

Check a specific day:

```bash
screener universe members --on 2021-06-15
```

---

## Your daily routine, once set up

```bash
cd ~/SCREENERV12
source .venv/bin/activate
docker compose up -d

screener ingest --symbols SPY,QQQ,AAPL --start 2024-01-01
screener metrics build --since 2024-01-01
```

That is it. Four setup lines, two work lines.

---

## When something goes wrong

| What you see | What it means | Fix |
| --- | --- | --- |
| `command not found: screener` | You are outside the Python box | `cd ~/SCREENERV12` then `source .venv/bin/activate` |
| `connection refused` / database errors | Database is not running | Open Docker Desktop, then `docker compose up -d` |
| `Alpaca credentials missing` | Keys not read | Check `.env` exists and both key lines are filled in, no quotes or spaces |
| `no such file or directory` | Wrong folder | `cd ~/SCREENERV12` |
| `verify` says FAIL | Data mismatch | **Stop and send me the output.** Do not work around it. |
| Anything else | — | Copy the whole message and send it to me |

**You cannot break this by re-running commands.** Every command here is safe to run twice.
The only genuinely destructive thing available is `docker compose down -v`, which deletes the
database — so do not run that unless you mean it, and even then, re-ingesting rebuilds it.

---

## Where you are in the plan

| | |
| --- | --- |
| Phase 1 — data foundation | Built. **Step 7 is you confirming it.** |
| Phase 2 — indicators | Built. Step 8 runs it. |
| Phase 3 — universe + diagnostics | Built. Steps 9–10 run it. |
| Phase 4 — backtest | Not built. Starts after Step 9's numbers come back. |

**The honest state of things:** nothing has been tested against market history yet. No claim
that any of this makes money exists, and none will until a backtest runs on data the strategy
has never seen. What exists now is the part that has to be right *before* that question can be
asked honestly.

The single most useful thing you can do is Step 7. Everything else waits on it.
