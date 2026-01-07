try:
    import yfinance as yf
    print("Checking CL=F...")
    t = yf.Ticker("CL=F")
    hist = t.history(period="1mo")
    if hist.empty:
        print("CL=F: Empty")
    else:
        print("CL=F: Found", len(hist))
        print(hist.head())

    print("\nChecking GC=F...")
    t = yf.Ticker("GC=F")
    hist = t.history(period="1mo")
    if hist.empty:
        print("GC=F: Empty")
    else:
        print("GC=F: Found", len(hist))

    print("\nChecking BTC-USD...")
    t = yf.Ticker("BTC-USD")
    hist = t.history(period="1mo")
    if hist.empty:
        print("BTC-USD: Empty")
    else:
        print("BTC-USD: Found", len(hist))

except Exception as e:
    print(e)
