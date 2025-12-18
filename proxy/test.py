import requests
import time
import string
import random

while True:
    r = requests.get("http://localhost:8080/" + "".join(random.choice(string.ascii_uppercase + string.digits) for _ in range(7)))
    print(r.status_code)
    time.sleep(random.randrange(0, 10))