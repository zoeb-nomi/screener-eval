# Start here

## The easy way (no Terminal)

1. **Unzip** `screener-eval-for-mac.zip` (double-click it in Finder). You should end up
   with a `screener-eval` folder.
2. **Double-click `Screener.command`** inside that folder. A small window opens (first
   run takes ~30-60 seconds to set itself up), then your browser opens the control
   panel automatically.
3. **If macOS says it "cannot verify the developer"**: right-click (or Control-click)
   `Screener.command` → **Open** → click **Open** again on the dialog that appears.
   You only need to do this once — after that, double-clicking works normally.

From the control panel: paste your API keys in the **Keys** tab and click Save, click
**Check keys**, then use the **Run** tab to run the pilot and, once you're happy with
the rep count, the full comparison. The **Log** tab shows live output; **Reports**
lists finished reports and lets you download a results bundle. Leave the small
Terminal window open while you work — closing it stops the server.

Where to get each key:
- **Anthropic key:** console.anthropic.com → sign in → "API keys" → "Create key".
  A couple of dollars of prepaid credit covers everything here.
- **OpenAI key:** platform.openai.com → sign in → "API keys" → "Create new secret key".
  Same — a couple of dollars is plenty.

---

## Alternative: Terminal path

8 steps, about 10 minutes, roughly $0.05 total for the pilot in step 7.

1. **Unzip** `screener-eval-for-mac.zip` (double-click it in Finder). You should end up
   with a `screener-eval` folder.

2. **Open Terminal.** Press `Cmd+Space`, type `Terminal`, hit Enter.

3. **Go into the folder.** In Terminal, type (dragging the folder into the Terminal
   window after `cd ` also works instead of typing the path):
   ```
   cd ~/Downloads/screener-eval
   ```

4. **Install everything and create your key file:**
   ```
   make setup
   ```
   This installs the Python and Node packages this repo needs and creates a file
   called `.env` for your API keys.

5. **Open `.env` and paste your keys in:**
   ```
   open -e .env
   ```
   That opens it in TextEdit. It looks like this:
   ```
   ANTHROPIC_API_KEY=
   OPENAI_API_KEY=
   ```
   Paste each key after its `=` (no quotes, no spaces), save (`Cmd+S`), close the window.
   Where to get each key:
   - **Anthropic key:** go to console.anthropic.com → sign in → "API keys" in the left
     sidebar → "Create key". You'll need a bit of prepaid credit on the account
     (a couple of dollars covers everything here).
   - **OpenAI key:** go to platform.openai.com → sign in → "API keys" → "Create new
     secret key". Same — a couple of dollars of prepaid credit is plenty.

6. **Check your keys work** (makes one tiny real call to each provider, a fraction of
   a cent):
   ```
   make keys-check
   ```
   If it prints `FAIL` for either provider, the key you pasted is wrong or the
   account has no credit — fix that and run `make keys-check` again before continuing.

7. **Run the pilot** — one real job description, both models, 10 repeated calls each,
   to see how noisy the scores are before committing to a full run:
   ```
   make pilot
   ```
   Projected cost: **about $0.04** (1 job description × 10 reps × 2 models × one
   résumé condition, at the per-token prices in `config/config.yaml`). It writes
   `reports/pilot_anthropic-pm-beneficial-deployments-001.md`.

8. **Send the report back.** Find the file in Finder
   (`screener-eval/reports/pilot_anthropic-pm-beneficial-deployments-001.md`, or
   just search Spotlight for `pilot_anthropic`) and send it back so the next step —
   sizing and running the full comparison — can be planned from real numbers.

---

**Troubleshooting:**

If `make` says `command not found`, run `xcode-select --install` once, then try `make setup` again.

If something else breaks: copy the exact error text (from the Log tab in the UI, or
from Terminal) and send it back — don't try to debug it yourself. `make pilot-mock`
(no keys, no cost, no network) is a good way to check the pipeline itself still runs
if you're not sure whether a failure is your keys or something else.
