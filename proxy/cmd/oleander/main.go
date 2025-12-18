package main

import (
	"dignitat/oleander/internal/http"
	"dignitat/oleander/internal/inference"
	"dignitat/oleander/internal/models"
)

func main() {

	config := models.NewConfig("0.0.0.0", 8080, "https://example.com")

	predictor := inference.NewPredictor()
	predictor.LoadModel("model.onnx")
	defer predictor.Destroy()

	server := http.NewHTTPServer(config, predictor)
	server.ServeHTTP()
}
