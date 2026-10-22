# QuarterFill

A missing number can make it hard to compare a company’s quarters or finish a financial model. Sometimes the company reports a total for the year but does not show the last quarter on its own. Finding that quarter means opening reports, checking dates, and doing the math yourself.

QuarterFill brings those steps together. Enter a company’s ticker, pull up its financial statements, and see whether a missing number can be worked out from its SEC reports. When QuarterFill calculates a number, it shows the starting amounts, the subtraction, and links to the reports so you can follow along.

[Open QuarterFill for free](https://quarterfill.streamlit.app)

## What you can do

- **Quarterly Lookup:** Find a company’s quarterly financial statements and see where a number came from.
- **Three-Statement Builder:** View its income statement, balance sheet, and cash flow statement in one place.
- **Missing Data Investigator:** Check a missing item and see the calculation when enough information is available.
- **SEC Filing Explorer:** Open the original company reports and look for a word or line item.
- **Methodology and Data Health:** Learn how the calculations work and see which reports could be checked.

## How to use it

1. [Open the website](https://quarterfill.streamlit.app). You do not need to install anything or pay for an account.
2. Enter a ticker, such as **NEOG** or **AAPL**, and choose the years you want.
3. Select **Show financial statements**.
4. Choose a statement, then pick a line item and quarter to see how the number was found or calculated.

The explanations show each step in plain language. A calculated last quarter might look like this:

**Full year − first three quarters = last quarter**

The actual amounts and company reports appear with the calculation.

## What to keep in mind

QuarterFill is still being improved. Companies do not all report their numbers in the same way, and sometimes a report does not contain enough information to fill a gap. When that happens, the app leaves the number blank and tells you why. A blank does not mean zero.

The app has been checked using real company filings, but it has not had a complete independent financial review. If you plan to use a number in a model or an investment decision, open the source reports and make sure the comparison makes sense. QuarterFill helps you do the research; it does not replace your judgment.

If you want to run your own copy, the [setup guide](DEPLOYMENT.md) explains how. You do not need to do that to use the website.

QuarterFill is free to use and shared under the [MIT License](LICENSE). It is an independent project and is not affiliated with the SEC. It is a research tool, not investment advice.
