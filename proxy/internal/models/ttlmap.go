// https://stackoverflow.com/a/25487392

package models

import (
	"sync"
	"time"
)

type item[V any] struct {
	value      V
	lastAccess int64
}

type TTLMap[K comparable, V any] struct {
	m map[K]*item[V]
	l sync.Mutex
}

func NewTTLMap[K comparable, V any](ln int, maxTTL time.Duration) *TTLMap[K, V] {
	m := &TTLMap[K, V]{
		m: make(map[K]*item[V], ln),
	}

	go func() {
		ticker := time.NewTicker(time.Second)
		defer ticker.Stop()

		for now := range ticker.C {
			m.l.Lock()
			for k, v := range m.m {
				if time.Unix(v.lastAccess, 0).Add(maxTTL).Before(now) {
					delete(m.m, k)
				}
			}
			m.l.Unlock()
		}
	}()

	return m
}

func (m *TTLMap[K, V]) Len() int {
	m.l.Lock()
	defer m.l.Unlock()
	return len(m.m)
}

func (m *TTLMap[K, V]) Put(k K, v V) {
	m.l.Lock()
	defer m.l.Unlock()

	it, ok := m.m[k]
	if !ok {
		it = &item[V]{}
		m.m[k] = it
	}

	it.value = v
	it.lastAccess = time.Now().Unix()
}

func (m *TTLMap[K, V]) Get(k K) (v V, ok bool) {
	m.l.Lock()
	defer m.l.Unlock()

	if it, found := m.m[k]; found {
		it.lastAccess = time.Now().Unix()
		return it.value, true
	}

	var zero V
	return zero, false
}
