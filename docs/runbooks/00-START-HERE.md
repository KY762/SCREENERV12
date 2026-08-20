# Start Here

Follow these in order. Copy each grey box, paste it into the black terminal
window, press Enter, wait for it to finish, move to the next one.

You are not writing code. You are pasting.

---

## Before you start

Open the terminal. That is where everything gets pasted.

- **Mac:** press Cmd+Space, type `terminal`, press Enter.
- **Windows:** press the Windows key, type `powershell`, press Enter.

Leave that window open for the whole guide.

---

## 1. Install Docker

Go to <https://www.docker.com/products/docker-desktop/>, download it, install it, **open it**.

Wait until it says "Engine running". Leave it open. If Docker is closed, nothing else works.

## 2. Install Python

Go to <https://www.python.org/downloads/>, download, install.

**Windows only:** on the first installer screen, tick the box that says
**"Add python.exe to PATH"** before clicking Install.

## 3. Get the code

```
cd ~
git clone https://github.com/KY762/SCREENERV12.git
cd SCREENERV12
git checkout claude/trading-platform-design-9i2pba
```

## 4. Install the project

Mac:
```
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Windows:
```
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
```

Takes a few minutes and prints a lot of text. That is fine.

You should now see `(.venv)` at the start of your terminal line.

## 5. Check it works

```
pytest -q
```

Green line saying tests passed → keep going.
Red or "FAILED" → stop, send me what it printed.

## 6. Get free data keys

1. Go to <https://alpaca.markets>, sign up (free).
2. In the sidebar, switch to **Paper Trading**.
3. Click **API Keys** → **Generate**.
4. Copy the **Key ID** and the **Secret Key** somewhere. The secret is shown once only.

## 7. Save your keys

```
cp .env.example .env
open .env
```

Windows: use `copy .env.example .env` then `notepad .env`

A text file opens. Find these two lines:

```
ALPACA_API_KEY_ID=
ALPACA_API_SECRET_KEY=
```

Paste your Key ID after the first `=`. Paste your Secret after the second `=`.
No spaces. No quotes. Ignore every other line in the file. Save. Close.

## 8. Start the database

```
docker compose up -d
screener db init
```

## 9. Download prices

```
screener ingest --symbols SPY,QQQ,AAPL --start 2019-01-01
```

Should say **succeeded** in green.

## 10. Check the prices are correct

```
screener verify
```

**This is the important one.** It compares our prices against a completely
different data source.

- **PASS / green** → done. Tell me and we move on.
- **FAIL / red** → stop. Send me what it printed. Do not continue.

If it mentions volume being different, that is normal and not a failure.

---

# You're done

That's it. Send me the result of step 10.

---

## Every time you come back

Open the terminal and paste these three lines first, every time:

Mac:
```
cd ~/SCREENERV12
source .venv/bin/activate
docker compose up -d
```

Windows:
```
cd ~/SCREENERV12
.venv\Scripts\activate
docker compose up -d
```

Then you can run `screener` commands.

---

## If something breaks

| It says | Do this |
| --- | --- |
| `command not found: screener` | Paste the three "every time you come back" lines above |
| `connection refused` | Open Docker Desktop, wait for "Engine running", try again |
| `Alpaca credentials missing` | Redo step 7 |
| `no such file or directory` | Paste `cd ~/SCREENERV12` and try again |
| anything else | Copy the whole message, send it to me |

Nothing here can be broken by running it twice. If you're unsure, run it again.
