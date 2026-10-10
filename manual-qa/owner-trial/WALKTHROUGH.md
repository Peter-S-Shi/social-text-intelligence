# Owner exploratory trial: a short walkthrough

**Status: PENDING OWNER.** This is an early, lightweight, owner-led trial of the
native desktop. It is not the M9 scenario-based UAT, it does not replace it, and
nothing here has been run by the owner yet. Do not read this file as evidence that
any step passed. Record what you actually see in [FRICTION_LOG.md](FRICTION_LOG.md).

The data is invented. [scenario.csv](scenario.csv) has 29 rows of made-up product
feedback in three groups (`app_store`, `support`, `forum`) with deliberate edge
cases: one empty text, one record id used twice, one French and one German row, a
cell that starts with `=` (a spreadsheet formula), and a few sarcastic or
ambiguous lines. Of the 29 rows, 26 should import as ready.

## 0. Start without touching your own data

The app keeps projects under your per-user application-data folder. For a trial it
is safest to use a disposable folder instead. Either of these works:

- **Demo helper (recommended).** From the repository root in Windows PowerShell:

  ```powershell
  .\tools\demo\start_demo.bat
  ```

  It opens the desktop on `_local\demo` (never your real folder) with one invented
  project, and imports the pinned models from `model_cache` if you have them there.
  Add `--reset` to start over. Import `scenario.csv` yourself in step 2.
- **Normal start.** `sti-desktop` uses your real per-user folder. Delete the trial
  project afterwards (step 9).

Window size: the window can be resized; 900 pixels wide is the minimum. Try 100%
and 150% display scaling if you are able to.

## 1. First launch and models

1. Is the window title and the sidebar readable? Does the sidebar say whether the
   two models are ready?
2. If the models are not installed, the setup window explains what is needed.
   Download them, or use a models folder you already have (offline). Do not stop
   the download midway unless you want to test that.
3. Choose **Later** at the setup window once: can you still reach Projects?

## 2. Import

1. In **Projects**, choose **Import CSV…** and pick `scenario.csv`.
2. If asked which column holds the text, choose `text`.
3. On **Import & validation**: how many rows are ready, and how many are
   rejected? (Expected: 29 rows, 26 ready, 3 rejected: the empty text, and both rows
   that use `t-023`.) Is the reason for each rejection clear?
4. Are the metadata columns shown as present (`record_id`, `source_label`, `topic`,
   `timestamp`)?

## 3. Analyse, cancel, analyse

1. Choose **Analyze 26 rows**, and cancel while the progress bar is moving.
   Nothing should be saved from a cancelled run, and the project should look as it
   did before.
2. Analyse again and let it finish. The page should move to **Results**.

## 4. Results

1. Do the sentiment, dominant-emotion and activation figures read clearly? Do the
   counts add up the way the page says?
2. Is there a language warning for the French and German rows? Does the wording say
   the models support English only?
3. Use the row filters (All, Analysed, Not analysed) and the two combos.
4. Select a row and open it in **Review**.
5. Export the normalized CSV, open it in a spreadsheet, and check that the cell
   starting with `=` is not evaluated as a formula.

## 5. Review

1. The queue on the left lists the records. Choose a few; does the selected line
   always match the record shown on the right?
2. Judge several records with **Accept**, **Correct** and **Uncertain**. Try
   **Save and next**, **Next unreviewed**, and the review-state tabs.
3. Leave an edit unsaved and try to move to another record: you should be asked
   before it is discarded.
4. Is it always clear which card is the AI's record (read-only) and which is yours?

## 6. Agreement, insights, notes

1. **Agreement** after at least ten judgments: does "agreement, not accuracy" come
   across, and is every percentage written with its denominator?
2. **Insights · compare**: group by `source_label`, tick **Compare 2 to 4 groups**,
   choose all three, and show the view. Try each perspective.
3. **Insights · notes & cases**: add one context note, then pick a case rule and open
   a case in Review.
4. Export the reviewed CSV and the insights CSV; check where they were saved.

## 7. Failure feel (optional)

- Make the destination folder read-only or full and try an export: is the message
  accurate and does your data remain?
- Close the window mid-analysis and note what happens (the design intends a clean finish or cancel; this has not been checked by you yet).

## 8. A second launch

Close and reopen the app. Is the project still listed, with your reviews intact?

## 9. Delete

Delete the trial project from **Projects**. Is the confirmation wording
conservative and accurate? (It must not claim secure erasure.)

## What to hand back

Fill in [FRICTION_LOG.md](FRICTION_LOG.md): one line per friction point or defect,
with the screen and what you expected. Subjective design fidelity against the Round 3
reference is a separate owner decision recorded in
[docs/V2_M8_TRACK_B_FIDELITY.md](../../docs/V2_M8_TRACK_B_FIDELITY.md); it is not
decided by this trial's pass or fail.
