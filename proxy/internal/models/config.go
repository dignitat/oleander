package models

import "sync"

type Config struct {
	Host   string `json:"host"`
	Port   int    `json:"port"`
	Target string `json:"target"`
}

var (
	globalConfig *Config
	once         sync.Once
)

func InitConfig(host string, port int, target string) {
	once.Do(func() {
		globalConfig = &Config{
			Host:   host,
			Port:   port,
			Target: target,
		}
	})
}

func GetConfig() *Config {
	return globalConfig
}

func UpdateConfig(host string, port int, target string) {
	if globalConfig == nil {
		InitConfig(host, port, target)
		return
	}

	globalConfig.Host = host
	globalConfig.Port = port
	globalConfig.Target = target
}
