package hw3test

import (
	"fmt"
	"os"
	"path"
	"testing"
	"text/template"

	"github.com/stretchr/testify/require"
	"go.uber.org/zap"
)

func TestHW(tt *testing.T) {
	t := NewTestContext(tt)
	Info(t, "Starting tests")

	useDocker := boolFromEnv("USE_DOCKER", false)

	// loading commandline args template from disk, to run solution with it
	launchTmpl := os.Getenv("LAUNCH_TMPL")
	if launchTmpl == "" {
		launchTmpl = "./default_solution.tmpl"
		if useDocker {
			launchTmpl = "./docker_solution.tmpl"
		}
	}

	tmplContent, err := os.ReadFile(launchTmpl)
	require.NoError(t, err, "failed to read template file")
	launchTemplate := template.Must(template.New("launch").Parse(string(tmplContent)))

	runner := NewCmdRunner(launchTemplate, useDocker)
	tmpDir, err := os.Getwd()
	require.NoError(t, err, "failed to get current directory")
	tmpDir = path.Join(tmpDir, "tmp")
	require.NoError(t, os.MkdirAll(tmpDir, 0777), "failed to create tmp dir")

	score := 0

	type RunResult struct {
		Name   string
		Scored int
		Max    int
	}
	runResults := []RunResult{}

	runGroup := func(name string, points int, f func(t *TC)) {
		t.RunByName(name, func(t *TC) {
			Info(t, "Starting tests group", zap.Int("points", points))
			t.Cleanup(func() {
				r := RunResult{
					Name: name,
					Max:  points,
				}

				ok := !t.Failed()
				if ok {
					score += points
					r.Scored = points

					Info(t, "Tests group passed", zap.String("name", name), zap.Int("score", score))
				} else {
					Warn(t, "Tests group failed", zap.String("name", name), zap.Int("score", score))
				}

				runResults = append(runResults, r)
			})
			f(t)
		})
	}

	textEnv := &EnvGen{
		MaxDepth:      1,
		MaxDirs:       3,
		MaxFiles:      5,
		TextOnly:      true,
		MaxFileSizeKB: 64,
		TempDirectory: tmpDir,
		FilenameGen:   SimpleFilenameGenerator(8),
		AllowEnv:      false,
	}
	binaryEnv := &EnvGen{
		MaxDepth:      4,
		MaxDirs:       16,
		MaxFiles:      25,
		TextOnly:      false,
		MaxFileSizeKB: 1024,
		TempDirectory: tmpDir,
		FilenameGen:   SimpleFilenameGenerator(16),
		AllowEnv:      true,
	}
	largeEnv := &EnvGen{
		MaxDepth:      1,
		MaxDirs:       6,
		MaxFiles:      6,
		TextOnly:      false,
		MaxFileSizeKB: 256 * 1024, // 256 MB
		TempDirectory: tmpDir,
		FilenameGen:   SimpleFilenameGenerator(16),
		AllowEnv:      true,
	}

	// Simple GET queries for existing text files, 3 points.
	runGroup("G1", 3, func(t *TC) {
		RunTestEmptyWorkDir(t, 42, runner)

		env := textEnv
		queries := &QueriesGen{
			Count:            20,
			GetFile:          true,
			GetFileNoErrors:  true,
			GetDirectory:     false,
			GetDirectoryFull: false,
			Post:             false,
			Put:              false,
			Delete:           false,
			Compression:      false,
			AllHeaders:       false,
		}
		RunTests(t, 1337, runner, env, queries)
		RunTests(t, 1338, runner, env, queries)
		RunTests(t, 1339, runner, env, queries)
	})

	// Simple GET queries for existing binary files, 1 point.
	runGroup("G2", 1, func(t *TC) {
		env := binaryEnv
		queries := &QueriesGen{
			Count:            40,
			GetFile:          true,
			GetFileNoErrors:  true,
			GetDirectory:     false,
			GetDirectoryFull: false,
			Post:             false,
			Put:              false,
			Delete:           false,
			Compression:      false,
			AllHeaders:       false,
		}
		RunTests(t, 93, runner, env, queries)
		RunTests(t, 2945, runner, env, queries)
		RunTests(t, 3110, runner, env, queries)
	})

	// Any GET queries, 1 point.
	runGroup("G3", 1, func(t *TC) {
		env := textEnv
		queries := &QueriesGen{
			Count:            30,
			GetFile:          true,
			GetFileNoErrors:  false,
			GetDirectory:     true,
			GetDirectoryFull: false,
			Post:             false,
			Put:              false,
			Delete:           false,
			Compression:      false,
			AllHeaders:       false,
		}
		RunTests(t, 5311, runner, env, queries)
		RunTests(t, 2863, runner, env, queries)
		RunTests(t, 6712, runner, env, queries)
		RunTests(t, 7233, runner, env, queries)
		RunTests(t, 7067, runner, env, queries)
		RunTests(t, 3930, runner, env, queries)
	})

	// Simple file server, 2 points.
	runGroup("G4", 2, func(t *TC) {
		env := binaryEnv
		queries := &QueriesGen{
			Count:            30,
			GetFile:          true,
			GetDirectory:     true,
			GetDirectoryFull: false,
			Post:             true,
			Put:              true,
			Delete:           true,
			Compression:      false,
			AllHeaders:       false,
		}
		RunTests(t, 3152, runner, env, queries)
		RunTests(t, 2929, runner, env, queries)
		RunTests(t, 6554, runner, env, queries)
		RunTests(t, 1388, runner, env, queries)
		RunTests(t, 1672, runner, env, queries)
		RunTests(t, 1769, runner, env, queries)
	})

	// Extra headers, 1 point.
	runGroup("G5", 1, func(t *TC) {
		env := binaryEnv
		queries := &QueriesGen{
			Count:            30,
			GetFile:          true,
			GetDirectory:     true,
			GetDirectoryFull: false,
			Post:             true,
			Put:              true,
			Delete:           true,
			Compression:      false,
			AllHeaders:       true,
		}
		RunTests(t, 7942, runner, env, queries)
		RunTests(t, 1479, runner, env, queries)
		RunTests(t, 3324, runner, env, queries)
		RunTests(t, 6519, runner, env, queries)
		RunTests(t, 3746, runner, env, queries)
		RunTests(t, 1961, runner, env, queries)
	})

	// Full directory listing, 1 point.
	runGroup("G6", 1, func(t *TC) {
		env := largeEnv
		queries := &QueriesGen{
			Count:        25,
			GetFile:      true,
			GetDirectory: true,
			// docker has a bug which doesn't preserve time https://github.com/moby/moby/issues/17018
			GetDirectoryFull: true && !useDocker,
			Post:             true,
			Put:              true,
			Delete:           true,
			Compression:      false,
			AllHeaders:       false,
		}
		RunTests(t, 7824, runner, env, queries)
		RunTests(t, 1671, runner, env, queries)
		RunTests(t, 3793, runner, env, queries)
		RunTests(t, 272, runner, env, queries)
		RunTests(t, 2715, runner, env, queries)
		RunTests(t, 1436, runner, env, queries)
	})

	// No limits, 1 point.
	runGroup("G7", 1, func(t *TC) {
		env := largeEnv
		queries := &QueriesGen{
			Count:            30,
			GetFile:          true,
			GetDirectory:     true,
			GetDirectoryFull: true && !useDocker,
			Post:             true,
			Put:              true,
			Delete:           true,
			Compression:      true,
			AllHeaders:       true,
		}
		RunTests(t, 3224, runner, env, queries)
		RunTests(t, 7507, runner, env, queries)
		RunTests(t, 4172, runner, env, queries)
		RunTests(t, 7777, runner, env, queries)
		RunTests(t, 6666, runner, env, queries)
		RunTests(t, 6094, runner, env, queries)
		RunTests(t, 6442, runner, env, queries)
	})

	for _, r := range runResults {
		Info(t, fmt.Sprintf("Score for group [%s]: %d / %d", r.Name, r.Scored, r.Max))
	}

	Info(t, "Tests finished", zap.Int("score", score))
}
