package inference

import (
	"net/http"
	"os"
	"time"

	ort "github.com/yalue/onnxruntime_go"
)

type Predictor struct {
	featureExtractor *FeatureExtractor
	session          *ort.AdvancedSession
	inputTensor      *ort.Tensor[float32]
	outputTensor     *ort.Tensor[float32]
}

func NewPredictor() *Predictor {
	return &Predictor{
		featureExtractor: NewFeatureExtractor(),
	}
}

func (p *Predictor) LoadModel(modelPath string) {
	// Set ONNX runtime library path if needed
	if runtimePath := os.Getenv("ONNXRUNTIME_LIB"); runtimePath != "" {
		ort.SetSharedLibraryPath(runtimePath)
	}

	// Initialize environment
	if err := ort.InitializeEnvironment(); err != nil {
		panic(err)
	}

	inputShape := ort.NewShape(1, FEATURE_NUM)
	inputTensor, err := ort.NewEmptyTensor[float32](inputShape)
	if err != nil {
		panic(err)
	}

	// Output tensor shape can be inferred, or preallocate
	outputShape := ort.NewShape(1, 2) // for 2-class probability
	outputTensor, err := ort.NewEmptyTensor[float32](outputShape)
	if err != nil {
		panic(err)
	}

	session, err := ort.NewAdvancedSession(
		modelPath,
		[]string{"float_input"},
		[]string{"probabilities"},
		[]ort.Value{inputTensor},
		[]ort.Value{outputTensor},
		nil,
	)
	if err != nil {
		panic(err)
	}

	p.session = session
	p.inputTensor = inputTensor
	p.outputTensor = outputTensor
}

func (p *Predictor) Destroy() {
	p.inputTensor.Destroy()
	p.outputTensor.Destroy()

	if p.session != nil {
		p.session.Destroy()
	}
	ort.DestroyEnvironment()
}

func (p *Predictor) Predict(r *http.Request, realAddr string) float64 {
	// Returns bot probability

	features := p.featureExtractor.Extract(time.Now().Unix(), r, realAddr)
	return p.predict(features)
}

func (p *Predictor) predict(features *Features) float64 {
	// Returns bot probability

	inputData := features.AsArray()
	copy(p.inputTensor.GetData(), inputData)

	err := p.session.Run()
	if err != nil {
		panic(err)
	}

	return float64(p.outputTensor.GetData()[1])

}
