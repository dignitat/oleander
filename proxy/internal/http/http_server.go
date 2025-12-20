package http

import (
	"fmt"
	"net/http"
	"time"

	"dignitat/oleander/internal/inference"
	"dignitat/oleander/internal/models"
)

type HTTPServer struct {
	IP        string
	Port      int
	Target    string
	predictor *inference.Predictor
}

func NewHTTPServer(predictor *inference.Predictor) *HTTPServer {
	config := models.GetConfig()
	return &HTTPServer{config.Host, config.Port, config.Target, predictor}
}

func (h *HTTPServer) ServeHTTP() {
	srv := &http.Server{
		ReadHeaderTimeout: 20 * time.Second,
		WriteTimeout:      2 * time.Minute,
		ReadTimeout:       1 * time.Minute,
		Handler:           NewOleanderHandler(h.Target, h.predictor),
		Addr:              fmt.Sprintf("%s:%d", h.IP, h.Port),
	}

	fmt.Println("Listening on", srv.Addr)
	if err := srv.ListenAndServe(); err != nil {
		panic(err)
	}
}
