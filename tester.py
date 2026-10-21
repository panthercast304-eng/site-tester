import asyncio, json, os, random, re, time
from playwright.async_api import async_playwright

CFG = json.loads(os.environ["CONFIG"])
GROUP = int(os.environ.get("GROUP", "1"))
BOTS = int(os.environ.get("BOTS", "10"))
WAVE_MIN = float(os.environ.get("WAVE_MINUTES") or "0")
GAP = float(os.environ.get("LOGIN_GAP_SECONDS") or "0")
BASE = (os.environ.get("URL") or CFG["base_url"]).rstrip("/")
UA = "YourTesterBot/1.0 (+https://yoursite.com/bot)"  # honest name
DEVICES = ["iPhone 13", "Pixel 5", "Desktop Chrome"]
BLOCKED = re.compile(
    r"\b(ads?|advert\w*|rewards?|watch|play|withdraw\w*|claim|coins?)\b", re.I
)
results = []


async def verify_owner(ctx):
    """Customer must put their code in https://their-site/tester-verify.txt"""
    code = CFG.get("verify_code")
    if not code:
        print("WARNING: no verify_code set. Only test sites you own.")
        return True
    try:
        r = await ctx.request.get(BASE + "/tester-verify.txt")
        return r.status == 200 and code in (await r.text())
    except Exception:
        return False


async def find_pages(page, limit):
    """Open the home page and collect internal links (same site only)."""
    await page.goto(BASE + "/", timeout=30000)
    hrefs = await page.eval_on_selector_all(
        "a[href]", "els => els.map(e => e.href)"
    )
    found = []
    for h in hrefs:
        h = h.split("#")[0].split("?")[0]
        if h.startswith(BASE) and h != BASE + "/" and h != BASE:
            path = h[len(BASE):]
            if path not in found and not path.endswith(
                (".pdf", ".zip", ".png", ".jpg")
            ):
                found.append(path)
    return ["/"] + found[:limit]


async def do_login(page, email, password):
    L = CFG["login"]
    await page.goto(BASE + L.get("path", "/"), timeout=30000)
    await page.fill(L["email"], email)
    await asyncio.sleep(random.uniform(0.5, 2))
    await page.fill(L["password"], password)
    await page.click(L["submit"])
    if L.get("success"):
        await page.wait_for_selector(L["success"], timeout=15000)
    else:  # default: login form disappears
        await page.wait_for_selector(L["email"], state="hidden", timeout=15000)


async def run_step(page, st, n):
    d = st["do"]
    if d == "click":
        label = f"{st.get('selector', '')} {st.get('text', '')}"
        if BLOCKED.search(label):
            raise Exception(f"BLOCKED click: {label.strip()}")
        if "selector" in st:
            target = page.locator(st["selector"])
        else:
            target = page.get_by_text(st["text"], exact=True)
        await target.first.click(timeout=10000)
    elif d == "fill":
        await page.fill(st["selector"], st["value"])
    elif d == "expect_text":
        await page.wait_for_selector(f"text={st['text']}", timeout=10000)
    elif d == "expect_selector":  # presence only, never clicks
        await page.locator(st["selector"]).first.wait_for(
            state="visible", timeout=10000
        )
    elif d == "scroll":
        for _ in range(st.get("times", 4)):
            await page.mouse.wheel(0, random.randint(300, 700))
            await asyncio.sleep(random.uniform(0.5, 1.2))
    elif d == "bad_login":  # only 1 bot per runner, fake account
        if n != 1:
            return
        L = CFG["login"]
        await page.fill(L["email"], "nobody@example.invalid")
        await page.fill(L["password"], "wrong-password-123")
        await page.click(L["submit"])
        if st.get("expect"):
            await page.wait_for_selector(f"text={st['expect']}", timeout=10000)
    else:
        raise Exception(f"unknown step: {d}")
    await asyncio.sleep(random.uniform(0.5, 2))


def build_accounts():
    """userplay001..N. Default password from TEST_PASSWORD.
    A secret named TEST_PASSWORD_008 overrides account 008, and so on."""
    pw = os.environ.get("TEST_PASSWORD", "")
    pat = CFG.get("account_pattern")
    accounts = []
    if pat and pw:
        for i in range(1, CFG.get("account_count", 0) + 1):
            accounts.append({
                "email": pat.format(i),
                "password": os.environ.get(f"TEST_PASSWORD_{i:03d}") or pw,
            })
    return accounts


async def bot(p, browser, n):
    gid = (GROUP - 1) * BOTS + n  # unique bot number 0..49
    name = DEVICES[gid % len(DEVICES)]
    opts = {} if name == "Desktop Chrome" else p.devices[name]
    ctx = await browser.new_context(**{**opts, "user_agent": UA})
    page = await ctx.new_page()
    errors, problems, timings, ads = [], [], {}, {}
    page.on("console", lambda m: errors.append(m.text[:100]) if m.type == "error" else None)
    try:
        accounts = build_accounts()
        has_acc = bool(CFG.get("login")) and gid < len(accounts)
        # bots with an account start GAP seconds apart; bots without start now
        await asyncio.sleep((gid * GAP if has_acc else 0) + random.uniform(0, 5))
        pages = CFG.get("sections", ["/"])
        if CFG.get("crawl"):
            pages = await find_pages(page, CFG.get("max_pages", 15))
        for s in pages:
            t = time.time()
            r = await page.goto(BASE + s, timeout=30000)
            timings[s] = int((time.time() - t) * 1000)
            if r and r.status >= 400:
                problems.append(f"{s} returned {r.status}")
            await page.mouse.wheel(0, random.randint(300, 1200))
            for sel in CFG.get("ad_selectors", []):  # check only, never click
                ads[f"{s} {sel}"] = await page.locator(sel).count()
            await asyncio.sleep(random.uniform(1, 4))
        for st in CFG.get("steps", []):
            await run_step(page, st, n)
        # logged-in part: each bot uses its own test account
        if has_acc:
            acc = accounts[gid]
            await do_login(page, acc["email"], acc["password"])
            for st in CFG.get("after_login_steps", []):
                await run_step(page, st, n)
    except Exception as e:
        problems.append(str(e)[:150])
    status = "PASS" if not problems else "FAIL"
    print(f"[bot {gid}] {name} {status} pages={len(timings)} console_err={len(errors)}")
    results.append({"bot": gid, "device": name, "status": status,
                    "timings_ms": timings, "ad_slots": ads,
                    "console_errors": errors, "problems": problems})
    await ctx.close()


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        check = await browser.new_context(user_agent=UA)
        if not await verify_owner(check):
            print("STOPPED: ownership not verified.")
            await browser.close()
            return
        await check.close()
        if WAVE_MIN:
            wait = (GROUP - 1) * WAVE_MIN * 60
            print(f"Wave {GROUP}: waiting {wait/60:.0f} min")
            await asyncio.sleep(wait)
        await asyncio.gather(*(bot(p, browser, n) for n in range(BOTS)))
        await browser.close()
    passed = sum(r["status"] == "PASS" for r in results)
    print(f"GROUP {GROUP}: {passed}/{len(results)} bots passed")
    with open(f"results_{GROUP}.json", "w") as f:
        json.dump(results, f, indent=2)


asyncio.run(main())
