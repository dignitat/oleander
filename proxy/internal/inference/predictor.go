package inference

import (
	ort "github.com/yalue/onnxruntime_go"
)

type Predictor struct{}

func NewPredictor() *Predictor {
	return &Predictor{}
}

func (p *Predictor) LoadModel() {
	err := ort.InitializeEnvironment()
	if err != nil {
		panic(err)
	}

	/*session, err := ort.NewSession("resnet18.onnx")
	if err != nil {
		panic(fmt.Errorf("failed to load ONNX model: %w", err))
	}
	defer session.Close()*/

}

func (p *Predictor) Destroy() {
	ort.DestroyEnvironment()
}

func (p *Predictor) Predict() {

}
