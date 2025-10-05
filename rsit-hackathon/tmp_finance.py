import yfinance as yf, json, os, datetime as dt
os.makedirs("docs/data", exist_ok=True)
end=dt.date.today(); start=end-dt.timedelta(days=30)
df=yf.download("AMZN", start=start.isoformat(), end=end.isoformat(), progress=False)
rows=[{"date":i.strftime("%Y-%m-%d"),"close":float(r["Close"])} for i,r in df.iterrows()]
json.dump({"symbol":"AMZN","daily":rows}, open("docs/data/finance_amzn_recent.json","w"), indent=2)
print("Wrote docs/data/finance_amzn_recent.json", len(rows))
