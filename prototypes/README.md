# Interface prototypes

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
