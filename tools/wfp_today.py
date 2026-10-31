#!/usr/bin/env python3
"""Фактичні оплати WayForPay за сьогодні (Київ). Ключі — лише з env:
WFP_MERCHANT / WFP_SECRET, WFP_MERCHANT_2 / WFP_SECRET_2. Нічого не зберігає."""
import hmac, hashlib, json, os, time, urllib.request, collections, datetime, zoneinfo
kyiv = zoneinfo.ZoneInfo("Europe/Kyiv")
now = datetime.datetime.now(kyiv)
t0 = int(now.replace(hour=0, minute=0, second=0, microsecond=0).timestamp()); t1 = int(time.time())
pairs = [(os.environ.get("WFP_MERCHANT"), os.environ.get("WFP_SECRET")),
         (os.environ.get("WFP_MERCHANT_2"), os.environ.get("WFP_SECRET_2"))]
tot = collections.Counter(); hours = collections.Counter()
for m, s in pairs:
    if not (m and s): continue
    sig = hmac.new(s.encode(), f"{m};{t0};{t1}".encode(), hashlib.md5).hexdigest()
    body = json.dumps({"apiVersion": 1, "transactionType": "TRANSACTION_LIST", "merchantAccount": m,
                       "merchantSignature": sig, "dateBegin": t0, "dateEnd": t1}).encode()
    d = json.loads(urllib.request.urlopen(urllib.request.Request("https://api.wayforpay.com/api", data=body,
                   headers={"Content-Type": "application/json"}), timeout=30).read())
    if str(d.get("reasonCode")) != "1100": print(m, d.get("reasonCode"), d.get("reason")); continue
    for t in d.get("transactionList") or []:
        if t["transactionStatus"] != "Approved": continue
        tot[(m, t["amount"])] += 1
        if t["amount"] == "290.00": hours[(int(t["createdDate"]) - t0) // 3600] += 1
for k, v in sorted(tot.items()): print(k, v)
print("290 по годинах (Київ):", dict(sorted(hours.items())))
