package inference

import (
	"math"
	"net/http"
	"slices"
	"sync"

	"gonum.org/v1/gonum/stat"
)

const REQ_WINDOW = 10

type FeatureExtractor struct {
	reqTimestamps        map[string][]int64
	reqTimestampsMutexes map[string]*sync.Mutex
	mapMutex             sync.Mutex
}

func NewFeatureExtractor() *FeatureExtractor {
	return &FeatureExtractor{
		reqTimestamps:        make(map[string][]int64),
		reqTimestampsMutexes: make(map[string]*sync.Mutex),
	}
}

func stringEntropy(str string) float32 {
	// Returns Shannon entropy normalized between 0 and 1

	if len(str) == 0 {
		return 0
	}

	// Count occurrences of each character
	counts := make(map[rune]int)
	for _, c := range str {
		counts[c]++
	}

	// Compute probabilities
	probs := make([]float64, 0, len(counts))
	for _, cnt := range counts {
		probs = append(probs, float64(cnt)/float64(len(str)))
	}

	// Calculate raw entropy
	entropy := 0.0
	for _, p := range probs {
		entropy += -p * math.Log2(p)
	}

	// Maximum possible entropy
	nUnique := len(counts)
	if nUnique <= 1 {
		return 0.0
	}
	maxEntropy := math.Log2(float64(nUnique))

	// Normalized entropy
	return float32(entropy / maxEntropy)

}

func (fe *FeatureExtractor) addTimestamp(timestamp int64, realAddr string) (timestamps []int64, isFirst bool) {
	fe.mapMutex.Lock()
	defer fe.mapMutex.Unlock()

	_, exists := fe.reqTimestamps[realAddr]
	if !exists {
		fe.reqTimestamps[realAddr] = []int64{}
	}

	if len(fe.reqTimestamps[realAddr]) > REQ_WINDOW {
		fe.reqTimestamps[realAddr] = fe.reqTimestamps[realAddr][1:]
	}

	fe.reqTimestamps[realAddr] = append(fe.reqTimestamps[realAddr], timestamp)

	return fe.reqTimestamps[realAddr], !exists
}

func (fe *FeatureExtractor) Extract(timestamp int64, request *http.Request, realAddr string) *Features {
	features := NewFeatures()

	timestamps, isFirst := fe.addTimestamp(timestamp, realAddr)
	features.IsFirstRequest = isFirst

	// Create and fill inter-request times
	irTimes := make([]float64, 0, len(timestamps)-1)
	for i := 1; i < len(timestamps); i++ {
		delta := timestamps[i] - timestamps[i-1]
		irTimes = append(irTimes, float64(delta))
	}

	irTimesLen := len(irTimes)

	// Basic time features
	if irTimesLen == 0 {
		features.StdevInterReqTime = -1
		features.MeanInterReqTime = -1
		features.MinInterReqTime = -1
	} else {
		features.StdevInterReqTime = float32(stat.PopStdDev(irTimes, nil))
		features.MeanInterReqTime = float32(stat.Mean(irTimes, nil))
		features.MinInterReqTime = float32(slices.Min(irTimes))
	}

	// Entropy features

	features.UriEntropy = stringEntropy(request.RequestURI)

	features.AcceptLangEntropy = stringEntropy(request.Header.Get("Accept-Language"))
	features.AcceptEntropy = stringEntropy(request.Header.Get("Accept"))

	// Burstiness and memory coefficients
	// Formula from DOI 10.1209/0295-5075/81/48002
	// Burstiness and memory in complex systems - Goh & Barabási, 2008
	features.Burstiness = (features.StdevInterReqTime - features.MeanInterReqTime) / (features.StdevInterReqTime + features.MeanInterReqTime)
	if irTimesLen < 2 || features.StdevInterReqTime <= 0 {
		features.Memory = 0
	} else {
		num := 0.0
		for i := 0; i < irTimesLen-1; i++ {
			num += (irTimes[i] - float64(features.MeanInterReqTime)) * (irTimes[i+1] - float64(features.MeanInterReqTime))
		}

		denom := float64(irTimesLen-1) * math.Pow(float64(features.StdevInterReqTime), 2)
		features.Memory = float32(num / denom)
	}

	return features
}
