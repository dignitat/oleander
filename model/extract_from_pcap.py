import dpkt
from pydantic import BaseModel
import numpy as np
import csv
from features import Features, extract_features
import sys
import os

ARTIFACTS_FOLDER = "artifacts"

if (not os.path.isdir(ARTIFACTS_FOLDER)):
    os.makedirs(ARTIFACTS_FOLDER)

OUTPUT_FILE = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ARTIFACTS_FOLDER, "dataset.csv")

IS_FROM_PROXY = sys.argv[2] == "true" if len(sys.argv) > 2 else False

BOT_AGENTS = [
    "robot",
    "bot",
    "crawler",
    "spider",
    "worm",
    "search",
    "track",
    "harvest",
    "hack",
    "trap",
    "archive",
    "scrap"
]

file = open("http.pcap", "rb")
reader = dpkt.pcap.Reader(file)

users = []
bots = []

def write_csv():
    # Prepare header
    header = [
        "is_bot",
        "is_first_request",
        "stdev_time_between_requests",
        "mean_time_between_requests",
        "min_time_between_requests",
        "uri_entropy",
        "accept_language_entropy",
        "accept_entropy",
        "burstiness",
    ]

    # Combine bots and users
    all_features = []
    for f in bots:
        row = [1]  # is_bot = 1
        row.extend([
            f.is_first_request,
            getattr(f, "stdev_time_between_requests", -1),
            getattr(f, "mean_time_between_requests", -1),
            getattr(f, "min_time_between_requests", -1),
            getattr(f, "uri_entropy", -1),
            getattr(f, "accept_language_entropy", -1),
            getattr(f, "accept_entropy", -1),
            getattr(f, "burstiness", -1),
        ])
        all_features.append(row)

    for f in users:
        row = [0]  # is_bot = 0
        row.extend([
            f.is_first_request,
            getattr(f, "stdev_time_between_requests", -1),
            getattr(f, "mean_time_between_requests", -1),
            getattr(f, "min_time_between_requests", -1),
            getattr(f, "uri_entropy", -1),
            getattr(f, "accept_language_entropy", -1),
            getattr(f, "accept_entropy", -1),
            getattr(f, "burstiness", -1),
        ])
        all_features.append(row)

    # Write CSV
    with open(OUTPUT_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(all_features)

    print("Exported dataset.csv with", len(all_features), "rows")
    print(len(bots), "bots and", len(users), "users")

try:
    for timestamp, buf in reader:
        eth = dpkt.ethernet.Ethernet(buf)

        if (not isinstance(eth.data, dpkt.ip.IP)):
            continue
        
        ip = eth.data
        if (not isinstance(ip.data, dpkt.tcp.TCP)):
            continue
        
        tcp = ip.data
        # Now see if we can parse the contents as a HTTP request
        try:
            request = dpkt.http.Request(tcp.data)
        except (dpkt.dpkt.NeedData, dpkt.dpkt.UnpackError):
            continue
        
        do_not_fragment = bool(ip.off & dpkt.ip.IP_DF)
        more_fragments = bool(ip.off & dpkt.ip.IP_MF)
        fragment_offset = ip.off & dpkt.ip.IP_OFFMASK
        
        uri = request.uri
        body = request.body
        headers = request.headers
        method = request.method

        # Do not process api or cdn calls
        if ("cdn" in uri.lower() or "api" in uri.lower()): continue

        # Filter for known bots
        has_bot_agent = ("user-agent" in headers and any(bot_agent in headers["user-agent"].lower() for bot_agent in BOT_AGENTS))
        is_bot = ("from" in headers or has_bot_agent or not "user-agent" in headers)

        if ("from" in headers and "bingbot" in headers["from"]): # BINGBOT DOES WEIRD THINGS
            continue
        
        if (IS_FROM_PROXY and not "x-real-ip" in headers):
            continue

        real_ip = headers["x-real-ip"] if "x-real-ip" in headers else ip

        features = extract_features(timestamp, request, real_ip)
        if (is_bot): bots.append(features)
        else: users.append(features)
except dpkt.dpkt.NeedData as e:
    print("Skipped packet:", str(e))
write_csv()