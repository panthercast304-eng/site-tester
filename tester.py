import asyncio, json, os, random, time
from playwright.async_api import async_playwright

CFG = json.loads(os.environ["CONFIG"])
GROUP = int(os.environ.get("GROUP", "1"))
BOTS = int(os.environ.get("BOTS", "10"))
BASE = os.environ.get("URL") or CFG["base_url"]
UA = "YourTesterBot/1.0 (+https://yoursite.com/bot)"  # honest name, change it
DEVICES = ["iPhone 13", "Pixel 5", "Desktop Chrome"]
results = []


async def verify_owner(ctx):
    """Customer must put your code in https://their-site/tester-verify.txt"""
    code = CFG.get("verify_code")
    if not code:
        print("WARNING: no verify_code set. Only test sites you own.")
        return True
    try:
        r = await ctx.request.get(BASE.rstrip("/") + "/tester-verify.txt")
        return r.status == 200 and code in (await r.text())
    except Exception:
        return False


async def bot(p, browser, n):
    gid = (GROUP - 1) * BOTS + n  # unique bot number 0..49
    name = DEVICES[gid % len(DEVICES)]
    opts = {} if name == "Desktop Chrome" else p.devices[name]
    accs = CFG.get("accounts", [])
    acc = accs[gid % len(accs)] if accs else None
        ctx = await browser.new_context(**{**opts, "user_agent": UA})
    page = await ctx.new_page()
    errors, problems, timings = [], [], {}
    page.on("console", lambda m: errors.append(m.text[:100]) if m.type == "error" else None)
    try:
        await asyncio.sleep(random.uniform(0, 5))  # stagger starts
        L = CFG.get("login")
        if L and acc:
            await page.goto(BASE + L["path"], timeout=30000)
            await page.fill(L["email"], acc["email"])
            await asyncio.sleep(random.uniform(0.5, 2))
            await page.fill(L["password"], acc["password"])
            await page.click(L["submit"])
            await page.wait_for_selector(L["success"], timeout=15000)
        for s in CFG.get("sections", ["/"]):
            t = time.time()
            r = await page.goto(BASE + s, timeout=30000)
            ms = int((time.time() - t) * 1000)
            timings[s] = ms
            if r.status >= 400:
                problems.append(f"{s} returned {r.status}")
            await page.mouse.wheel(0, random.randint(300, 1200))
            await asyncio.sleep(random.uniform(1, 4))
        for st in CFG.get("steps", []):
            d = st["do"]
            if d == "click":
                await page.click(st["selector"], timeout=10000)
            elif d == "fill":
                await page.fill(st["selector"], st["value"])
            elif d == "expect_text":
                await page.wait_for_selector(f"text={st['text']}", timeout=10000)
            await asyncio.sleep(random.uniform(0.5, 2))
    except Exception as e:
        problems.append(str(e)[:150])
    status = "PASS" if not problems else "FAIL"
    print(f"[bot {gid}] {name} {status} console_errors={len(errors)} {problems}")
    results.append({"bot": gid, "device": name, "status": status,
                    "timings_ms": timings, "console_errors": errors,
                    "problems": problems})
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
        await asyncio.gather(*(bot(p, browser, n) for n in range(BOTS)))
        await browser.close()
    passed = sum(r["status"] == "PASS" for r in results)
    print(f"GROUP {GROUP}: {passed}/{len(results)} bots passed")
    with open(f"results_{GROUP}.json", "w") as f:
        json.dump(results, f, indent=2)

asyncio.run(main())
