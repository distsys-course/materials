package hw3test

import (
	"bytes"
	"fmt"
	"io"
	"math/rand"
	"os"
	"os/exec"
	"strings"
	"text/template"

	"go.uber.org/zap"
)

// RunOpts contains command line arguments for the solution.
// Those are passed to the template.
type RunOpts struct {
	// Solution options
	Port             int
	WorkingDirectory string
	ListenAddr       string // Host
	ServerDomain     string

	// Full run config that will be provided to the solution.
	CommandLineArgs string
	Env             []string

	// Full run config if solution will be running in docker.
	DockerCommandLineArgs string
	DockerEnvArgs         string
	DockerPortArgs        string
	DockerVolumeArgs      string

	// Hack to get exitcode of the solution.
	ExitCode chan int
}

func (o *RunOpts) Address() string {
	host := os.Getenv("SOLUTION_HOST")
	if host == "" {
		host = "localhost"
	}

	return fmt.Sprintf("http://%s:%d", host, o.Port)
}

func (o *RunOpts) GenerateRunConfig(t *TC, r *rand.Rand, gen *EnvGen) {
	o.CommandLineArgs, o.Env = o.BuildConfig(r, gen)

	dirsInDocker := []string{
		"/files",
		"/files0",
		"/files1",
		"/files2",
		"/files3",
	}
	dirInDocker := dirsInDocker[r.Intn(len(dirsInDocker))]

	if o.WorkingDirectory == "" {
		dirInDocker = ""
	} else {
		o.DockerVolumeArgs = fmt.Sprintf(`-v "%s:%s"`, o.WorkingDirectory, dirInDocker)
	}

	o.DockerPortArgs = fmt.Sprintf("-p %d:%d", o.Port, o.Port)

	dockerArgs, dockerEnv := RunOpts{
		ListenAddr:       o.ListenAddr,
		Port:             o.Port,
		WorkingDirectory: dirInDocker,
		ServerDomain:     o.ServerDomain,
	}.BuildConfig(r, gen)

	o.DockerEnvArgs = ""
	for _, env := range dockerEnv {
		o.DockerEnvArgs += "--env \"" + env + "\" "
	}

	o.DockerCommandLineArgs = dockerArgs
}

// BuildConfig uses ListenAddr, Port, WorkingDirectory, ServerDomain.
func (o RunOpts) BuildConfig(r *rand.Rand, gen *EnvGen) (args string, env []string) {
	if o.ListenAddr == "0.0.0.0" && r.Intn(2) == 1 {
		// can omit default value
	} else if gen.AllowEnv && r.Intn(3) == 1 {
		// use env
		env = append(env, fmt.Sprintf("SERVER_HOST=%s", o.ListenAddr))
	} else if o.ListenAddr != "" {
		// use plain cmdline args
		args += fmt.Sprintf(" \"--host=%s\"", o.ListenAddr)

		if r.Intn(2) == 1 {
			// pass dummy env
			env = append(env, fmt.Sprintf("SERVER_HOST=%s", "8.8.8.8"))
		}
	}

	if o.Port == 8080 && r.Intn(2) == 1 {
		// can omit default value
	} else if gen.AllowEnv && r.Intn(3) == 1 {
		// use env
		env = append(env, fmt.Sprintf("SERVER_PORT=%d", o.Port))
	} else {
		// use plain cmdline args
		args += fmt.Sprintf(" \"--port=%d\"", o.Port)

		if r.Intn(2) == 1 {
			// pass dummy env
			env = append(env, fmt.Sprintf("SERVER_PORT=%d", 80))
		}
	}

	if o.WorkingDirectory == "" && r.Intn(2) == 1 {
		// can omit default value
	} else if gen.AllowEnv && r.Intn(3) == 1 {
		// use env
		env = append(env, fmt.Sprintf("SERVER_WORKING_DIRECTORY=%s", o.WorkingDirectory))
	} else if o.WorkingDirectory != "" {
		// use plain cmdline args
		args += fmt.Sprintf(" \"--working-directory=%s\"", o.WorkingDirectory)

		if r.Intn(2) == 1 {
			// pass dummy env
			env = append(env, fmt.Sprintf("SERVER_WORKING_DIRECTORY=%s", "/"))
		}
	}

	if o.ServerDomain == "" && r.Intn(2) == 1 {
		// can omit default value
	} else if gen.AllowEnv && r.Intn(3) == 1 {
		// use env
		env = append(env, fmt.Sprintf("SERVER_DOMAIN=%s", o.ServerDomain))
	} else if o.ServerDomain != "" {
		// use plain cmdline args
		args += fmt.Sprintf(" \"--server-domain=%s\"", o.ServerDomain)

		if r.Intn(2) == 1 {
			// pass dummy env
			env = append(env, fmt.Sprintf("SERVER_DOMAIN=%s", "example.com"))
		}
	}
	return args, env
}

// Runner is a helper for running HTTP server solution.
type Runner interface {
	// Run the solution with the given options.
	// Returns a function that can be used to stop the solution.
	Run(t *TC, opts RunOpts) (stop func(), err error)
}

// CmdRunner runs command based on template.
type CmdRunner struct {
	tmpl      template.Template
	useDocker bool
}

func NewCmdRunner(tmpl *template.Template, useDocker bool) *CmdRunner {
	return &CmdRunner{
		tmpl:      *tmpl,
		useDocker: useDocker,
	}
}

func (r *CmdRunner) Run(t *TC, opts RunOpts) (stop func(), err error) {
	var b bytes.Buffer
	err = r.tmpl.Execute(&b, opts)
	if err != nil {
		return nil, fmt.Errorf("failed to execute template: %v", err)
	}

	envOpts := opts.Env
	if r.useDocker {
		envOpts = nil
	}

	cmdString := strings.TrimSpace(b.String())
	Info(t, "Running command", zap.String("command", cmdString), zap.Strings("env", envOpts))

	cmd := exec.Command("bash", "-c", cmdString)
	cmd.Env = append(os.Environ(), envOpts...)
	cmd.Stdout = NewProxyWriter(os.Stderr)
	cmd.Stderr = NewProxyWriter(os.Stderr)

	err = cmd.Start()
	if err != nil {
		return nil, fmt.Errorf("failed to run command: %v", err)
	}

	go func() {
		err := cmd.Wait()
		if err != nil {
			Warn(t, "Command finished with error", zap.Error(err))
		}
		if opts.ExitCode != nil {
			if e, ok := err.(*exec.ExitError); ok {
				opts.ExitCode <- e.ExitCode()
			} else {
				opts.ExitCode <- 0
			}
		}
	}()

	return func() {
		err := cmd.Process.Kill()
		if err != nil {
			Error(t, "Failed to kill command", zap.Error(err))
		}
	}, nil
}

// ProxyWriter is used to forward solution output to standard output.
type ProxyWriter struct {
	w       io.Writer
	disable bool
}

func NewProxyWriter(w io.Writer) *ProxyWriter {
	return &ProxyWriter{
		w:       w,
		disable: boolFromEnv("DISABLE_SOLUTION_OUTPUT", false),
	}
}

func (w *ProxyWriter) Write(b []byte) (n int, err error) {
	if w.disable {
		return len(b), nil
	}
	// TODO: if there will be sync problems, we can take a global lock
	// 	and read until \n, then flush and apply color
	return w.w.Write(b)
}
