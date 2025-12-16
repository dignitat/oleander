package models

type Config struct {
	Host   string `json:"host"`
	Port   int    `json:"port"`
	Target string `json:"allowedDomains"`
}

func NewConfig(host string, port int, target string) *Config {
	return &Config{host, port, target}
}
