package hw3test

import (
	"fmt"
	"go.uber.org/zap"
	"go.uber.org/zap/zapcore"
	"os"
	"sync"
)

func logLevelFromEnv() zap.AtomicLevel {
	levelStr := os.Getenv("LOG_LEVEL")
	if levelStr == "" {
		return zap.NewAtomicLevelAt(zap.DebugLevel)
	}

	level, err := zap.ParseAtomicLevel(levelStr)
	if err != nil {
		panic(fmt.Errorf("failed to parse log level: %w", err))
	}
	return level
}

var global *zap.Logger
var globalOnce sync.Once

func Global() *zap.Logger {
	if global == nil {
		globalOnce.Do(func() {
			encoder := zapcore.EncoderConfig{
				// Keys can be anything except the empty string.
				TimeKey:        "",
				LevelKey:       "L",
				NameKey:        "_",
				CallerKey:      "C",
				FunctionKey:    "F",
				MessageKey:     "M",
				StacktraceKey:  "S",
				LineEnding:     zapcore.DefaultLineEnding,
				EncodeLevel:    zapcore.CapitalColorLevelEncoder,
				EncodeTime:     zapcore.ISO8601TimeEncoder,
				EncodeDuration: zapcore.StringDurationEncoder,
				EncodeCaller:   zapcore.ShortCallerEncoder,
			}
			cfg := zap.Config{
				Level:             logLevelFromEnv(),
				Development:       true,
				DisableCaller:     true,
				DisableStacktrace: true,
				Encoding:          "console",
				EncoderConfig:     encoder,
				OutputPaths:       []string{"stderr"},
				ErrorOutputPaths:  []string{"stderr"},
			}
			options := []zap.Option{
				zap.AddCallerSkip(1),
			}

			var err error
			global, err = cfg.Build(options...)
			if err != nil {
				panic(fmt.Errorf("failed to initialize global logger: %w", err))
			}
		})
	}

	return global
}

func Logger(t *TC) *zap.Logger {
	logger := Global()
	logger = logger.Named(t.Name())
	return logger
}

func Debug(t *TC, msg string, args ...zap.Field) {
	Logger(t).Debug(msg, args...)
	_ = Logger(t).Sync()
}

func Info(t *TC, msg string, args ...zap.Field) {
	Logger(t).Info(msg, args...)
	_ = Logger(t).Sync()
}

func Warn(t *TC, msg string, args ...zap.Field) {
	Logger(t).Warn(msg, args...)
	_ = Logger(t).Sync()
}

func Error(t *TC, msg string, args ...zap.Field) {
	Logger(t).Error(msg, args...)
	_ = Logger(t).Sync()
}
