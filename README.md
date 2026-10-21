# Site Tester - setup (phone, free)

## Files
- tester.py          -> the bot (put in repo root)
- test.yml           -> put at .github/workflows/test.yml
- config.example.json-> what to test (copy its content into a GitHub Secret)

## Steps
1. Make a free GitHub account, create a PUBLIC repo "site-tester".
2. Add file tester.py (paste content).
3. Add file .github/workflows/test.yml (paste content).
4. Repo > Settings > Secrets and variables > Actions > New secret
   Name: CONFIG   Value: your edited config JSON.
5. On your test site, create a file tester-verify.txt containing your verify_code.
6. Actions tab > Site test > Run workflow.
7. Open the run: each bot prints PASS/FAIL. Download results-*.json for details.

## Change what is tested
Edit the CONFIG secret: sections, accounts, steps. No code change needed.

## Rules
- Only test sites that are yours or verified by the owner.
- Never put passwords in the public repo, only in Secrets.
- If runs time out, set BOTS to "6" in test.yml.
