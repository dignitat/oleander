import sys
sys.path.append("..")

import dpkt
from pydantic import BaseModel
import numpy as np
import csv
from features import Features, extract_features, MAX_REQ_MEMORY
import os
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse
from tqdm import tqdm

if (not os.path.isdir("graphs")): os.mkdir("graphs")

IS_FROM_PROXY = sys.argv[1] == "true" if len(sys.argv) > 1 else False

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

file = open("../http.pcap", "rb")
reader = dpkt.pcap.Reader(file)

users = []
bots = []
gpt_bot = []
claude_bot = []

try:
    for timestamp, buf in tqdm(reader):
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

        #if (features.stdev_time_between_requests > 200 and "user-agent" in headers):
        #    print(headers["user-agent"])

        if (features._req_num < MAX_REQ_MEMORY): continue

        if (is_bot): bots.append(features)
        else: users.append(features)

        if ("user-agent" in headers and "gptbot" in headers["user-agent"].lower()):
            gpt_bot.append(features)

        if ("user-agent" in headers and "claudebot" in headers["user-agent"].lower()):
            claude_bot.append(features)

except dpkt.dpkt.NeedData as e:
    print("Skipped packet:", str(e))

print("len(bots): " + str(len(bots)))
print("len(users): " + str(len(users)))

bot_bm = [(f.burstiness, f.memory) for f in bots]
human_bm = [(f.burstiness, f.memory) for f in users]
gpt_bm = [(f.burstiness, f.memory) for f in gpt_bot]
claude_bm = [(f.burstiness, f.memory) for f in claude_bot]

bot_x, bot_y = zip(*bot_bm) if bot_bm else ([], [])
human_x, human_y = zip(*human_bm) if human_bm else ([], [])
gpt_x, gpt_y = zip(*gpt_bm) if gpt_bm else ([], [])
claude_x, claude_y = zip(*claude_bm) if claude_bm else ([], [])

def plot_cov_ellipse(x, y, n_std=2):
    data = np.column_stack([x, y])
    mean = data.mean(axis=0)
    cov = np.cov(data, rowvar=False)

    vals, vecs = np.linalg.eigh(cov)
    order = vals.argsort()[::-1]
    vals, vecs = vals[order], vecs[:, order]

    theta = np.degrees(np.arctan2(*vecs[:, 0][::-1]))
    width, height = 2 * n_std * np.sqrt(vals)

    ell = Ellipse(
        xy=mean,
        width=width,
        height=height,
        angle=theta,
        fill=False
    )
    plt.gca().add_patch(ell)

    plt.scatter(mean[0], mean[1], marker="+", s=100)

# Bots
plt.figure()

plt.scatter(bot_x, bot_y, alpha=0.3, marker="x", s=2, label="Bots")
plot_cov_ellipse(bot_x, bot_y)

plt.xlabel("Burstiness")
plt.ylabel("Memory")
plt.ylim(-1, 1)
plt.xlim(-1, 1)
plt.legend()
plt.savefig("graphs/bm_scatter_bots.png", dpi=150)
plt.close()

# Humans
plt.figure()

plt.scatter(human_x, human_y, alpha=0.1, marker="o", s=2, label="Humans")
plot_cov_ellipse(human_x, human_y)

plt.xlabel("Burstiness")
plt.ylabel("Memory")
plt.ylim(-1, 1)
plt.xlim(-1, 1)
plt.legend()
plt.savefig("graphs/bm_scatter_humans.png", dpi=150)
plt.close()

# GPT Bot
plt.figure()

plt.scatter(gpt_x, gpt_y, alpha=1, marker="x", s=2, label="GPTBot")
plot_cov_ellipse(gpt_x, gpt_y)

plt.xlabel("Burstiness")
plt.ylabel("Memory")
plt.ylim(-1, 1)
plt.xlim(-1, 1)
plt.legend()
plt.savefig("graphs/bm_scatter_gpt.png", dpi=150)
plt.close()

# Claude Bot
plt.figure()

plt.scatter(claude_x, claude_y, alpha=1, marker="x", s=2, label="ClaudeBot")
plot_cov_ellipse(claude_x, claude_y)

plt.xlabel("Burstiness")
plt.ylabel("Memory")
plt.ylim(-1, 1)
plt.xlim(-1, 1)
plt.legend()
plt.savefig("graphs/bm_scatter_claude.png", dpi=150)
plt.close()

bot_b = [f.burstiness for f in bots]
human_b = [f.burstiness for f in users]

plt.figure()
plt.boxplot(
    [human_b, bot_b],
    tick_labels=["Humans", "Bots"],
    showfliers=False
)

plt.ylabel("Burstiness of inter-request time")
plt.savefig("graphs/burstiness_box.png", dpi=150, bbox_inches="tight")
plt.close()

bot_m = [f.memory for f in bots]
human_m = [f.memory for f in users]

plt.figure()
plt.boxplot(
    [human_m, bot_m],
    tick_labels=["Humans", "Bots"],
    showfliers=False
)

plt.ylabel("Memory of inter-request time")
plt.savefig("graphs/memory_box.png", dpi=150, bbox_inches="tight")
plt.close()

bot_stdev = [f.stdev_time_between_requests for f in bots]
human_stdev = [f.stdev_time_between_requests for f in users]
gpt_stdev = [f.stdev_time_between_requests for f in gpt_bot]
claude_stdev = [f.stdev_time_between_requests for f in claude_bot]

plt.figure()
plt.boxplot(
    [human_stdev, bot_stdev],
    tick_labels=["Humans", "Bots"],
    showfliers=False
)

plt.ylabel("Std. dev. of inter-request time")
plt.savefig("graphs/stdev_box.png", dpi=150, bbox_inches="tight")
plt.close()

plt.figure()
plt.boxplot(
    [human_stdev, gpt_stdev],
    tick_labels=["Humans", "GPTBot"],
    showfliers=False
)

plt.ylabel("Std. dev. of inter-request time")
plt.savefig("graphs/stdev_box_gpt.png", dpi=150, bbox_inches="tight")
plt.close()

plt.figure()
plt.boxplot(
    [human_stdev, claude_stdev],
    tick_labels=["Humans", "ClaudeBot"],
    showfliers=False
)

plt.ylabel("Std. dev. of inter-request time")
plt.savefig("graphs/stdev_box_claude.png", dpi=150, bbox_inches="tight")
plt.close()


plt.figure()
plt.violinplot(
    [human_stdev, bot_stdev],
    showmeans=True,
    showextrema=False
)

plt.xticks([1, 2], ["Humans", "Bots"])
plt.ylabel("Std. dev. of inter-request time")
plt.savefig("graphs/stdev_violin.png", dpi=150, bbox_inches="tight")
plt.close()

bot_uri_entr = [f.uri_entropy for f in bots]
gpt_uri_entr = [f.uri_entropy for f in gpt_bot]
human_uri_entr = [f.uri_entropy for f in users]

plt.figure()
plt.boxplot(
    [human_uri_entr, bot_uri_entr],
    tick_labels=["Humans", "Bots"],
    showfliers=False
)

plt.ylabel("URI Entropy")
plt.savefig("graphs/uri_entropy_box.png", dpi=150, bbox_inches="tight")
plt.close()

plt.figure()
plt.boxplot(
    [human_uri_entr, gpt_uri_entr],
    tick_labels=["Humans", "GPTBot"],
    showfliers=False
)

plt.ylabel("URI Entropy")
plt.savefig("graphs/uri_entropy_box_gpt.png", dpi=150, bbox_inches="tight")
plt.close()