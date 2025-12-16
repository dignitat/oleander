import math
from difflib import SequenceMatcher
import numpy as np

MAX_REQ_MEMORY = 7 # requests

def string_entropy(string):
    # Returns Shannon entropy normalized between 0 and 1
    
    if not string:
        return 0.0

    # calculate raw entropy
    prob = [float(string.count(c)) / len(string) for c in dict.fromkeys(string)]
    entropy = -sum(p * math.log(p, 2) for p in prob)

    # maximum possible entropy
    n_unique = len(set(string))
    if n_unique <= 1:
        return 0.0

    max_entropy = math.log2(n_unique)

    # normalized entropy
    return entropy / max_entropy

def string_similarity(a, b):
    return SequenceMatcher(None, a, b).ratio()

class Features():
    is_first_request: bool
    stdev_time_between_requests: float
    mean_time_between_requests: float
    min_time_between_requests: float
    uri_entropy: float
    accept_language_entropy: float
    accept_entropy: float
    burstiness: float

    def as_np_array(self):
        return np.array([
            float(self.is_first_request),
            self.stdev_time_between_requests,
            self.mean_time_between_requests,
            self.min_time_between_requests,
            self.uri_entropy,
            self.accept_language_entropy,
            self.accept_entropy,
            self.burstiness,
        ], dtype=float)

    def __str__(self):
        return str({
        })
    
request_timestamps = {}
last_uris = {}

class Request():
    uri: str
    headers: dict
    method: str
    body: bytes

def extract_features(timestamp, request, real_ip):

    global request_timestamps, last_uris

    features = Features()

    is_first_request = False

    # Add timestamp
    if (not real_ip in request_timestamps):
        request_timestamps[real_ip] = []
        is_first_request = True

    if (len(request_timestamps[real_ip]) >= MAX_REQ_MEMORY):
        request_timestamps[real_ip].pop(0)

    request_timestamps[real_ip].append(timestamp)

    # Is first request
    features.is_first_request = is_first_request

    # Time between requests
    times = np.array([t2 - t1 for t1, t2 in zip(request_timestamps[real_ip], request_timestamps[real_ip][1:])])
    features.stdev_time_between_requests = times.std() if times.any() else -1
    features.mean_time_between_requests = times.mean() if times.any() else -1
    features.min_time_between_requests = np.min(times) if times.any() else -1

    # URI entropy
    features.uri_entropy = string_entropy(request.uri)
    features.accept_language_entropy = string_entropy(request.headers["accept-language"] if "accept-language" in request.headers else "")
    features.accept_entropy = string_entropy(request.headers["accept"] if "accept" in request.headers else "")

    # Bursts (formula from Goh & Barabási, 2008)
    features.burstiness = (features.stdev_time_between_requests - features.mean_time_between_requests) / (features.stdev_time_between_requests + features.mean_time_between_requests)
    
    last_uris[real_ip] = request.uri

    return features