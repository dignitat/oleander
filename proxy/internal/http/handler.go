package http

import (
	"dignitat/oleander/internal/inference"
	"dignitat/oleander/internal/logging"
	"dignitat/oleander/internal/pow"
	"io"
	"net/http"
	"time"
)

type OleanderHandler struct {
	Target     string
	predictor  *inference.Predictor
	powManager *pow.POWManager
}

func NewOleanderHandler(target string, predictor *inference.Predictor) *OleanderHandler {
	return &OleanderHandler{target, predictor, pow.NewPOWManager()}
}

func (h *OleanderHandler) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	realAddr := h.getIPAddress(r)

	if _, val := h.powManager.IsValidChallengeURL(r.RequestURI, r.Method); val {
		h.powManager.HandleHTTP(w, r, false)
		defer logging.LogRequest(r, 0)
		return
	}

	botProb := h.predictor.Predict(r, realAddr)
	defer logging.LogRequest(r, botProb)

	h.powManager.HandleHTTP(w, r, true)
	return

	/*if botProb > 0.15 {
		h.powManager.HandleHTTP(w, r, true)
		return
	}*/

	response := h.forwardRequest(w, r, h.Target, realAddr)
	if response == nil {
		// TODO: Log request with error
		return
	}

	h.forwardResponse(w, r, response)

}

func (h *OleanderHandler) forwardRequest(
	incomingWriter http.ResponseWriter,
	incomingReq *http.Request,
	target string,
	clientAddr string) *http.Response {

	var response *http.Response
	var err error
	var req *http.Request

	client := &http.Client{
		Timeout: time.Second * 45,
		Transport: &http.Transport{
			MaxIdleConns:          1000,
			MaxIdleConnsPerHost:   100,
			IdleConnTimeout:       30 * time.Second,
			TLSHandshakeTimeout:   10 * time.Second,
			ExpectContinueTimeout: 1 * time.Second,
			DisableCompression:    true,
			ForceAttemptHTTP2:     false,
		},
	}

	// TODO: Http vs https
	uri := target + incomingReq.RequestURI

	req, err = http.NewRequest(incomingReq.Method, uri, incomingReq.Body)

	if err != nil {
		http.Error(incomingWriter, err.Error(), http.StatusInternalServerError)
		return nil
	}

	// Set headers
	for name, value := range incomingReq.Header {
		if name == "X-Forwarded-For" {
			continue
		}

		req.Header.Set(name, value[0])
	}

	req.Header.Set("X-Forwarded-For", clientAddr)

	response, err = client.Do(req)

	if err != nil {
		http.Error(incomingWriter, err.Error(), http.StatusInternalServerError)
		return nil
	}

	return response
}

func (h *OleanderHandler) forwardResponse(
	w http.ResponseWriter,
	req *http.Request,
	resp *http.Response) {

	for name, value := range resp.Header {
		w.Header().Set(name, value[0])
	}

	w.WriteHeader(resp.StatusCode)
	io.Copy(w, resp.Body)
	defer req.Body.Close()

}

func (h *OleanderHandler) logRequest(r *http.Request) {

}

func (h *OleanderHandler) getIPAddress(req *http.Request) string {

	addr := req.Header.Get("X-Real-Ip")

	if addr == "" {
		addr = req.Header.Get("X-Forwarded-For")
	}

	if addr == "" {
		addr = req.RemoteAddr
	}

	return addr
}
