package logging

import (
	"fmt"
	"net/http"
)

func LogRequest(r *http.Request, botProb float64) {
	fmt.Printf("[%d %%] [%s] %s : %s\n", int16(botProb*100), r.Method, r.RemoteAddr, r.URL.Path)
}
