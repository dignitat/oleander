package inference

const FEATURE_NUM = 9

type Features struct {
	IsFirstRequest    bool
	StdevInterReqTime float32
	MeanInterReqTime  float32
	MinInterReqTime   float32
	UriEntropy        float32
	AcceptLangEntropy float32
	AcceptEntropy     float32
	Burstiness        float32
	Memory            float32
}

func NewFeatures() *Features {
	return &Features{}
}

func (f *Features) AsArray() []float32 {

	var isFirst float32 = 0
	if f.IsFirstRequest {
		isFirst = 1
	}

	return []float32{
		isFirst,
		f.StdevInterReqTime,
		f.MeanInterReqTime,
		f.MinInterReqTime,
		f.UriEntropy,
		f.AcceptLangEntropy,
		f.AcceptEntropy,
		f.Burstiness,
		f.Memory,
	}
}
