package pow

import "crypto/rand"

type AccessManager struct {
	signingKey []byte
}

func generateSigningKey(bytes int) ([]byte, error) {
	key := make([]byte, bytes)
	_, err := rand.Read(key)
	if err != nil {
		return nil, err
	}
	return key, nil
}

func NewAccessManager() *AccessManager {

	signingKey, err := generateSigningKey()
	if err != nil {
		panic(err)
	}

	return &AccessManager{signingKey: signingKey}
}

func CanAccess()
