package http

import (
	"fmt"
	"net/http"
	"time"

	"dignitat/oleander/internal/models"
)

type HTTPServer struct {
	IP     string
	Port   int
	Target string
}

func NewHTTPServer(config *models.Config) *HTTPServer {
	return &HTTPServer{config.Host, config.Port, config.Target}
}

func (h *HTTPServer) ServeHTTP() {
	srv := &http.Server{
		ReadHeaderTimeout: 20 * time.Second,
		WriteTimeout:      2 * time.Minute,
		ReadTimeout:       1 * time.Minute,
		Handler:           NewOleanderHandler(h.Target),
		Addr:              fmt.Sprintf("%s:%d", h.IP, h.Port),
	}

	fmt.Println("Listening on", srv.Addr)
	if err := srv.ListenAndServe(); err != nil {
		panic(err)
	}
}
