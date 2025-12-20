package pow

import (
	"crypto/sha256"
	"dignitat/oleander/internal/models"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"math/rand/v2"
	"net/http"
	"os"
	"strconv"
	"strings"
	"time"

	"github.com/google/uuid"
)

const DATA_LENGTH = 5
const DIFFICULTY = 4

var letters = []rune("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ")

type challenge struct {
	id         string
	data       string
	difficulty int
	expires    int64
}

type pow struct {
	Hash  string `json:"hash"`
	Nonce int    `json:"nonce"`
}

type POWManager struct {
	template          string
	currentChallenges *models.TTLMap[string, challenge]
	powPrefix         string
}

func randomSequence(n int) string {
	b := make([]rune, n)
	for i := range b {
		b[i] = letters[rand.IntN(len(letters))]
	}
	return string(b)
}

func NewPOWManager() *POWManager {

	templateFile := "web/pow.html"

	dat, err := os.ReadFile(templateFile)
	if err != nil {
		panic(err)
	}

	return &POWManager{
		template:          string(dat),
		currentChallenges: models.NewTTLMap[string, challenge](100, time.Minute),
		powPrefix:         randomSequence(10),
	}
}

func (m *POWManager) newChallenge() *challenge {
	uuid, _ := uuid.NewUUID()
	id := uuid.String()
	data := randomSequence(DATA_LENGTH)

	return &challenge{
		id:         id,
		data:       data,
		difficulty: DIFFICULTY,
		expires:    time.Now().Unix() + 60,
	}
}

func (m *POWManager) getPOWFile(challenge *challenge) string {

	result := m.template
	result = strings.ReplaceAll(result, "{%data%}", challenge.data)
	result = strings.ReplaceAll(result, "{%difficulty%}", fmt.Sprint(challenge.difficulty))
	result = strings.ReplaceAll(result, "{%url%}", "/"+m.powPrefix+challenge.id)

	return result

}

func (m *POWManager) sendNewChallenge(w http.ResponseWriter) {
	challenge := m.newChallenge()
	m.currentChallenges.Put(challenge.id, *challenge)

	response := m.getPOWFile(challenge)

	w.WriteHeader(200)
	w.Write([]byte(response))
	w.Header().Add("content-type", "text/html; charset=utf-8")
}

func (m *POWManager) IsChallengePefix(uri string) bool {
	return strings.HasPrefix(uri, "/"+m.powPrefix)
}

func (m *POWManager) IsValidChallengeURL(uri string, method string) (challenge, bool) {

	challengeUUID := strings.Replace(uri, "/"+m.powPrefix, "", 1)
	challenge, exists := m.currentChallenges.Get(challengeUUID)

	return challenge, m.IsChallengePefix(uri) && exists && method == "POST"

}

func (m *POWManager) verifyPOW(challenge challenge, hash string, nonce int) bool {

	data := challenge.data + strconv.Itoa(nonce)

	hashBytes := sha256.Sum256([]byte(data))
	computed := hex.EncodeToString(hashBytes[:])

	if computed != hash {
		return false
	}

	if !strings.HasSuffix(hash, strings.Repeat("0", challenge.difficulty)) {
		return false
	}

	if challenge.expires < time.Now().Unix() {
		return false
	}

	return true

}

func (m *POWManager) processPOW(w http.ResponseWriter, r *http.Request, challenge challenge) {

	var recvPOW pow
	err := json.NewDecoder(r.Body).Decode(&recvPOW)
	if err != nil {
		http.Error(w, "Invalid JSON", http.StatusBadRequest)
		return
	}

	if m.verifyPOW(challenge, recvPOW.Hash, recvPOW.Nonce) {
		w.WriteHeader(200)
		w.Write([]byte("{\"status\": \"ok\"}"))

		// TODO: Remove challenge
		return
	} else {
		w.WriteHeader(400)
		return
	}

}

func (m *POWManager) HandleHTTP(w http.ResponseWriter, r *http.Request, blocked bool) bool {

	challenge, valid := m.IsValidChallengeURL(r.RequestURI, r.Method)

	if valid {
		// Existing challenge
		m.processPOW(w, r, challenge)
		return true

	} else if blocked {
		m.sendNewChallenge(w)
		return true
	}

	return false

}
