package main

import (
	"dignitat/oleander/internal/http"
	"dignitat/oleander/internal/inference"
	"dignitat/oleander/internal/models"
)

func main() {

	config := models.NewConfig("0.0.0.0", 8080, "http://127.0.0.1:8000")

	predictor := inference.NewPredictor()
	defer predictor.Destroy()

	server := http.NewHTTPServer(config)
	server.ServeHTTP()
}
