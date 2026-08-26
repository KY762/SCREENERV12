# Interface prototypes

## `swing-deck.html` — current

Built for a 3–15 day holding period, which changes the priorities:
relative strength, participation, volatility, rotation and CATALYSTS matter;
book value and long-run profitability do not move a stock in a week.

Three things it does that the earlier prototype did not:

**Asks whether to trade at all, before asking what to trade.** The regime panel
sits above the candidate list on purpose. Over a two-week hold the tape does a
lot of the work, and the strongest setup in a hostile market is still a long
position in a hostile market. It reports conditions, never a forecast -- the
distinction is stated on the page.

**Counts down to earnings, and lets that veto a trade.** A report can gap a
stock further than the stop in one session, which makes both the stop and the
position size wrong. Any earnings date inside the planned hold is a veto in the
position panel, not a footnote. Dates come from SEC filings, which lag the
actual announcement -- the page says so.

**Shows sector rotation and macro as relative moves.** Oil's price is not the
information. Energy outperforming utilities, or high yield lagging Treasuries,
is the information.

## `candidate-board.html`

The daily screen, as a self-contained page. Open it in a browser -- no server,
no build step, no dependencies.

**The data is invented and labelled as such on the page.** The layout, the
columns, and the sizing rules are the real proposal.

What is genuinely live in it:

- **Position sizing** mirrors `calc/sizing.py` exactly, including the
  concentration cap and the reasons a trade gets vetoed. Select a high-priced
  symbol and watch the cap fire -- that is the constraint discussed in
  `docs/07-STOP-DESIGN-QUESTION.md` §2, made visible.
- **Breadth** is computed across the whole universe rather than the filtered
  view, because "is this move real?" is a question about participation, not
  about the rows currently on screen.
- **Sparklines** are drawn from the row's own 60-day path.

What it deliberately does NOT do: rank candidates by expected profit, or
present setup geometry as an edge. No hypothesis has passed validation, and a
screen that implied otherwise would be inventing confidence the research does
not support. Setups are flagged as *geometry present*, and the caveats sit on
the page rather than in a footnote.

### Turning this into the real thing

Streamlit, when the time comes. One Python file that imports the existing
package and calls the same functions the CLI already calls -- no second
language, no build step, no deployment story. `pip install streamlit`, then
`streamlit run app.py`.

React and FastAPI were the original Phase 5 plan. They earn their place only
if this ever needs to run somewhere other than your own machine.
