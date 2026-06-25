import urllib.request
import json

try:
    url = "https://ifsc.razorpay.com/SBIN0001608"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as response:
        html = response.read().decode('utf-8')
        print(html)
except Exception as e:
    print("Error:", e)
