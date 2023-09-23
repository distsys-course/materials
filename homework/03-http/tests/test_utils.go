package hw3test

import (
	"context"
	"fmt"
	"net"
	"os"
	"strconv"
	"strings"
	"testing"
)

// TC implements *testing.T and context.Context at the same time.
// Also has some helper methods.
type TC struct {
	*testing.T
	ctx context.Context
}

func NewTestContext(t *testing.T) *TC {
	return &TC{
		ctx: context.Background(),
		T:   t,
	}
}

func (tc *TC) Errorf(format string, args ...any) {
	str := fmt.Sprintf(format, args...)
	if strings.HasPrefix(str, "\n\tError Trace:") {
		_, after, ok := strings.Cut(str, "\tError:")
		if ok {
			str = "\n\tError:" + after
		}
	}
	Error(tc, str)
	tc.T.Errorf(str)
}

func (tc *TC) RunByName(name string, f func(*TC)) bool {
	return tc.Run(name, func(t *testing.T) {
		f(tc.derive(t))
	})
}

func (tc *TC) RunBySeed(seed int64, f func(*TC)) bool {
	return tc.Run(strconv.FormatInt(seed, 10), func(t *testing.T) {
		f(tc.derive(t))
	})
}

func (tc *TC) Done() <-chan struct{} {
	return tc.ctx.Done()
}

func (tc *TC) Err() error {
	return tc.ctx.Err()
}

func (tc *TC) Value(key any) any {
	return tc.ctx.Value(key)
}

// derive copies *TC and replaces *testing.T
func (tc TC) derive(t *testing.T) *TC {
	tc.T = t
	return &tc
}

// Get bool from envvars
func boolFromEnv(key string, def bool) bool {
	value := os.Getenv(key)
	if value == "" {
		return def
	}

	value = strings.ToLower(value)
	switch value {
	case "t":
		return true
	case "true":
		return true
	case "y":
		return true
	case "yes":
		return true
	}
	return false
}

// GetFreePort asks the kernel for a free open port that is ready to use.
func GetFreePort() (int, error) {
	addr, err := net.ResolveTCPAddr("tcp", "localhost:0")
	if err != nil {
		return 0, err
	}

	l, err := net.ListenTCP("tcp", addr)
	if err != nil {
		return 0, err
	}
	defer l.Close()
	return l.Addr().(*net.TCPAddr).Port, nil
}
