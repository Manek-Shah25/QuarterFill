# QuarterFill

A missing number can make it hard to compare a company’s quarters or finish a financial model. Sometimes the company reports a total for the year but does not show the last quarter on its own. Finding that quarter means opening reports, checking dates, and doing the math yourself.

QuarterFill brings those steps together. Enter a company’s ticker, pull up its financial statements, and see whether a missing number can be worked out from its SEC reports. When QuarterFill calculates a number, it shows the starting amounts, the subtraction, and links to the reports so you can follow along.

[Open QuarterFill for free](https://quarterfill.streamlit.app)

## What you can do

- **Quarterly Lookup:** Find a company’s quarterly financial statements and see where a number came from. Choose **Revenue by segment** to see which parts of its business bring in revenue.
- **Three-Statement Builder:** View its income statement, balance sheet, cash flow statement, and revenue by segment in one place.
- **Missing Data Investigator:** Check a missing item and see the calculation when enough information is available.
- **SEC Filing Explorer:** Open the original company reports and look for a word or line item.
- **Methodology and Data Health:** Learn how the calculations work and see which reports could be checked.

## How to use it

1. [Open the website](https://quarterfill.streamlit.app). You do not need to install anything or pay for an account.
2. Enter a ticker, such as **AAPL**, and choose the years you want.
3. Select **Show financial statements**.
4. Choose a statement and click a quarter’s value to see how it was found or calculated. The explanation choices update to match that cell. You can also use the dropdowns yourself.

The explanations show each step in plain language. A calculated last quarter might look like this:

**Full year − first three quarters = last quarter**

The actual amounts and company reports appear with the calculation.

You can also choose a full-year view, show only reported or calculated amounts, and check the lines that still need an answer. Open **Do the statements add up?** to see the accounting checks. **Save this statement** downloads an Excel workbook with the numbers, calculations, and report sources. There is no separate export page.

## How the numbers are found

QuarterFill now checks 107 financial line items across the income statement, balance sheet, and cash flow statement. It first looks for the company’s reported numbers, then checks the original reports and their notes. Different names can describe the same item, but similar names can also mean different things. For example, inventory before allowances and inventory after allowances are kept separate.

**Reported** means the company disclosed the amount. **Calculated** means QuarterFill worked it out from matching reported amounts. A missing cost of revenue can sometimes be found by subtracting gross profit from revenue. A missing quarter can sometimes be found from the year total and the other quarters. Clicking the amount shows the work and links to the reports.

The report-values choice lets you compare first-reported and latest-reported amounts. The default checks all versions and leaves a conflict unresolved instead of choosing for you. Some businesses, especially banks, need different accounting rules. QuarterFill does not apply ordinary gross-profit formulas to them.

The latest source-reviewed check covers 24 annual or year-end amounts at Apple, Walmart, Microsoft, Adobe, UnitedHealth, Caterpillar, and JPMorgan. All 24 match the filing rows, compared with 19 in the previous version on the same data. This is a small, recorded coverage check by Codex, not an independent financial audit or a promise that every line at every company will be filled. The [engineering and testing notes](docs/extraction-overhaul.md) explain what changed and what still needs review.

## What to keep in mind

QuarterFill is still being improved. Companies do not all report their numbers in the same way, and sometimes a report does not contain enough information to fill a gap. When that happens, the app leaves the number blank and tells you why. A blank does not mean zero.

The revenue breakdown uses business segments from the company’s reports. It shows quarterly amounts, calculates a missing quarter when the reports support it, and checks whether the segments add up to company revenue. Some companies do not publish a usable segment breakdown, and segment definitions can change. Those gaps stay visible.

Under **Smaller revenue groups**, choose a business to see the products, services, or other groups reported inside it. This works from each company’s filing structure, rather than a list of preset companies. When a report gives a separate product breakdown without naming its parent business, we show it as a separate view. Some reports only put this detail in written notes or untagged tables, so we cannot promise every company’s smallest group will appear. Groups may overlap; the app keeps the views separate and shows when their totals do not match.

For a missing revenue amount, QuarterFill checks the reported quarter, running totals, the full year, and complete group breakdowns that add up in the company’s reports. For example, company revenue minus Animal Safety revenue can give Food Safety revenue. It also shows each segment’s share of company revenue and, when Genomics is reported separately, core revenue calculated as segment revenue minus Genomics.

Choose **Report version** to keep the selected year’s figures separate from the following year’s comparisons. Companies sometimes rename or move smaller groups. A row labeled **Remaining revenue** is explicitly the parent total minus the other listed groups; it does not claim two different category names mean exactly the same thing. If there still is not one supported answer, the amount stays blank. Two filled quarters cannot determine two unknown quarters on their own, and an empty row does not prove that a company does not use the item.

The app has been checked using real company filings, but it has not had a complete independent financial review. If you plan to use a number in a model or an investment decision, open the source reports and make sure the comparison makes sense. QuarterFill helps you do the research; it does not replace your judgment.

If you want to run your own copy, the [setup guide](DEPLOYMENT.md) explains how. You do not need to do that to use the website.

QuarterFill is free to use and shared under the [MIT License](LICENSE). It is an independent project and is not affiliated with the SEC. It is a research tool, not investment advice.
