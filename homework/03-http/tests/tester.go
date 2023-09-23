package hw3test

import (
	"context"
	"fmt"
	"math/rand"
	"net/http"
	"os"
	"path"
	"time"

	"github.com/stretchr/testify/require"
	"go.uber.org/zap"
)

// RunTestEmptyWorkDir will check that server does exit(1) if working directory is empty.
func RunTestEmptyWorkDir(t *TC, seed int64, runner Runner) {
	t.RunBySeed(seed, func(t *TC) {
		r := rand.New(rand.NewSource(seed))

		port, err := GetFreePort()
		require.NoError(t, err, "failed to get free port for the server")
		runOpts := RunOpts{
			Port:             port,
			WorkingDirectory: "",
			ServerDomain:     "",
			ListenAddr:       "0.0.0.0",
			ExitCode:         make(chan int),
		}

		// Start the solution.
		runOpts.GenerateRunConfig(t, r, &EnvGen{})
		stop, err := runner.Run(t, runOpts)
		require.NoError(t, err, "failed to start solution")
		defer stop()

		select {
		case <-time.After(time.Second * 10):
			require.FailNow(t, "Server didn't exit(1) in 10 seconds")
		case ec := <-runOpts.ExitCode:
			require.Equal(t, 1, ec, "Server exited with wrong code")
		}
	})
}

func RunTests(t *TC, seed int64, runner Runner, envGen *EnvGen, queriesGen *QueriesGen) {
	failed := !t.RunBySeed(seed, func(t *TC) {
		env, err := envGen.Generate(seed)
		require.NoError(t, err, "failed to generate environment")

		r := rand.New(rand.NewSource(seed))

		queriesSeeds := make([]int64, queriesGen.Count)
		for i := range queriesSeeds {
			queriesSeeds[i] = r.Int63n(100000)
		}

		envDirName := GenFilename(r, 16)
		envDir := path.Join(envGen.TempDirectory, envDirName)
		_ = os.RemoveAll(envDir)

		err = env.RootDir.WriteToDisk(envDir)
		require.NoError(t, err, "failed to write environment to disk")
		defer os.RemoveAll(envDir)

		port, err := GetFreePort()
		require.NoError(t, err, "failed to get free port for the server")
		runOpts := RunOpts{
			Port:             port,
			WorkingDirectory: envDir,
			ServerDomain:     "",
			ListenAddr:       "0.0.0.0",
		}
		if queriesGen.AllHeaders {
			possibleDomains := []string{
				"",
				"",
				"example.com",
				"z0r.de",
				"localhost",
				"distsys-course.homework.net",
			}
			runOpts.ServerDomain = possibleDomains[r.Intn(len(possibleDomains))]
		}

		queries := queriesGen.Generate(t, env, envGen, queriesSeeds, runOpts)

		// Start the solution.
		runOpts.GenerateRunConfig(t, r, envGen)
		stop, err := runner.Run(t, runOpts)
		require.NoError(t, err, "failed to start solution")
		defer stop()

		// Await server to bind to port.
		err = WaitForServer(t, runOpts)
		require.NoError(t, err, "failed to wait for server")

		// Run the queries.
		for i, query := range queries {
			query := query
			ok := t.RunBySeed(query.Seed, func(t *TC) {
				RunQuery(t, env, envDir, runOpts, query)
			})
			shouldAbort := !ok
			if shouldAbort {
				Warn(t, "Skipping next queries because of the failed query", zap.Int("skipped", len(queries)-1-i), zap.String("failed", fmt.Sprintf("%s/%v", t.Name(), query.Seed)))
				break
			}
		}
	})

	shouldAbort := failed
	if shouldAbort {
		Warn(t, "Skipping next tests in a group because last test has failed")
		t.FailNow()
	}
}

func WaitForServer(t *TC, opts RunOpts) error {
	for i := 0; i < 60; i++ {
		ctx, cancel := context.WithTimeout(t, 1*time.Second)
		defer cancel()
		req, err := http.NewRequestWithContext(ctx, "GET", opts.Address(), nil)
		if err != nil {
			return fmt.Errorf("failed to create context request: %w", err)
		}
		resp, err := http.DefaultClient.Do(req)
		//var netError *net.OpError
		//errors.As(err, &netError)
		//if netError == nil && err != io.EOF {
		//	Debug(t, "Ignoring non-network error", zap.Error(err))
		//	err = nil
		//}
		if err == nil {
			if resp != nil {
				resp.Body.Close()
			}
			return nil
		}
		Debug(t, "Waiting 100ms for server startup", zap.Int("attempt", i), zap.Error(err))
		time.Sleep(time.Millisecond * 100)
	}
	Warn(t, "Server didn't get up in time, aborting")
	return fmt.Errorf("server did not start in 10 seconds")
}

// RunQuery runs a single query. Server address and its configuration is taken from runOpts.
// Initial environment is described by env, but it may be changed with queries. Actual
// environment is located in envDir. Query describes the query itself.
func RunQuery(t *TC, env *Env, envDir string, opts RunOpts, query Query) {
	queryURL := fmt.Sprintf("%s/%s", opts.Address(), query.Path)
	Debug(
		t,
		"Sending query",
		zap.String("method", query.Method),
		zap.String("path", query.Path),
		zap.String("url", queryURL),
	)

	transport := &http.Transport{
		TLSHandshakeTimeout:   10 * time.Second,
		DisableKeepAlives:     true,
		DisableCompression:    !query.Gzip,
		MaxIdleConns:          1,
		IdleConnTimeout:       90 * time.Second,
		ExpectContinueTimeout: 1 * time.Second,
		ForceAttemptHTTP2:     false,
	}
	client := &http.Client{
		Transport: transport,
	}

	action := query.Action(env, &opts)
	if action != nil {
		action.VerifyBefore(t, envDir)
	}

	req := query.CreateRequest(t, queryURL)

	resp, err := client.Do(req)
	require.NoError(t, err, "failed to run query on server")
	defer resp.Body.Close()

	query.CommonValidate(t, req, resp)

	if action != nil {
		action.VerifyResponse(t, req, resp)
		action.VerifyAfter(t, envDir)
		action.ApplyEnv(t, env)
	}
}
