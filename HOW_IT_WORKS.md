# How the Site Tester works (simple)

## The idea
You tap "Run workflow" on GitHub. GitHub lends you 5 free computers.
Each computer opens 10 bots. 5 x 10 = 50 bots testing a site at the same time.
Your phone is only the remote control.

## The 4 files

### 1. test.yml  (the starter)
Put at: .github/workflows/test.yml
- Starts 5 free computers ("runners") at the same time.
- On each one it installs Playwright (the tool that controls a browser).
- Then it runs tester.py and saves the results.
- Edit BOTS: "10" to a smaller number if runs time out.

### 2. tester.py  (the bot's brain)
Each bot does this, in order:
1. Waits a few random seconds (so they don't all start in the same second).
2. Checks the site owner allowed the test (tester-verify.txt). Stops if not.
3. Opens the login page, types its own email + password, taps login.
4. Visits every section in your list and records: status, load time.
5. Scrolls and pauses like a visitor would.
6. Runs your extra steps (click, fill, expect_text).
7. Prints PASS or FAIL and saves the details to results_N.json.
Bots use different devices (iPhone, Android, desktop) and say honestly that
they are a tester bot in their user agent.

### 3. config (the CONFIG secret, from config.example.json)
This is WHAT to test. You edit this, not the code:
- base_url: the site
- verify_code: the code the owner puts in tester-verify.txt
- login: the page and the field/button selectors
- accounts: test emails and passwords (one per bot, they repeat if fewer)
- sections: pages to visit
- steps: extra actions and what text should appear

### 4. README.md  (setup steps)
The GitHub steps, in order.

## Where passwords go
Never in the public repo. Only in GitHub Secrets (Settings > Secrets > CONFIG).

## Reading results
Actions tab > open the run > click a job > "Run python tester.py".
Each line is one bot: PASS or FAIL and the problem.
Detailed files: results-1 ... results-5 under "Artifacts" at the bottom of the run.

## Rules
- Test only sites you own or that the owner verified.
- Keep it gentle: no hammering other people's sites.
