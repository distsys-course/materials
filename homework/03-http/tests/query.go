package hw3test

import (
	"fmt"
	"github.com/stretchr/testify/require"
	"io"
	"mime"
	"net/http"
	"os"
	"path"
)

// Query represents a query to the solution server.
type Query struct {
	// Seed is used as a query ID.
	Seed int64

	// Method of a request, e.g. "GET", "POST", "PUT", "DELETE".
	Method string

	// Simple file path, splitted by slashes. E.g. "foo/bar/baz".
	Path string

	// If true, will use `Accept-Encoding` for GET query.
	Gzip bool

	// If true, will pass `Create-Directory: True` in POST query.
	CreateDirectory bool

	// If true, will pass `Remove-Directory: True` in DELETE query.
	RemoveDirectory bool

	// Pass the Host header.
	HostHeader string

	// Verify full directory listing.
	VerifyDirectoryFull bool

	// Verify all server headers: `Content-Length`, `Content-Type`, `Server`.
	VerifyHeaders bool

	// FileContent when creating a file.
	FileContent *EnvFile
}

func (q *Query) CreateRequest(t *TC, queryURL string) *http.Request {
	var body io.Reader
	if q.FileContent != nil {
		body = q.FileContent.Open()
	}

	req, err := http.NewRequest(q.Method, queryURL, body)
	require.NoError(t, err, "failed to create go request")

	if q.FileContent != nil {
		req.ContentLength = q.FileContent.Size
	}
	if q.CreateDirectory {
		req.Header.Set("Create-Directory", "True")
	}
	if q.RemoveDirectory {
		req.Header.Set("Remove-Directory", "True")
	}
	if q.HostHeader != "" {
		req.Host = q.HostHeader
	}

	return req
}

func (q *Query) CommonValidate(t *TC, r *http.Request, resp *http.Response) {
	if q.VerifyHeaders {
		require.NotEmpty(t, resp.Header.Values("Server"), "missing Server header")
	}
}

type Action interface {
	// VerifyBefore verifies file content on disk before sending query to the server.
	VerifyBefore(t *TC, workdir string)

	// VerifyAfter verifies file content on disk after sending query to the server.
	VerifyAfter(t *TC, workdir string)

	// ApplyEnv applies the action to the environment.
	ApplyEnv(t *TC, env *Env) (changed bool)

	// VerifyResponse verifies the response from the server.
	VerifyResponse(t *TC, r *http.Request, resp *http.Response)
}

// HttpErrorAction is an Action, which expect specific status code in response.
type HttpErrorAction struct {
	Status int
}

func (h HttpErrorAction) VerifyBefore(t *TC, workdir string) {
	return
}

func (h HttpErrorAction) VerifyAfter(t *TC, workdir string) {
	return
}

func (h HttpErrorAction) ApplyEnv(t *TC, env *Env) bool {
	return false
}

func (h HttpErrorAction) VerifyResponse(t *TC, r *http.Request, resp *http.Response) {
	require.Equal(t, h.Status, resp.StatusCode, "expected http status code")
}

// GetFileAction is an Action, which returns file content in response.
type GetFileAction struct {
	Path        string
	File        *EnvFile
	Compression bool
}

func (g GetFileAction) VerifyBefore(t *TC, workdir string) {
	RequireFileContent(t, workdir, g.Path, g.File)
}

func (g GetFileAction) VerifyAfter(t *TC, workdir string) {
	RequireFileContent(t, workdir, g.Path, g.File)
}

func (g GetFileAction) ApplyEnv(t *TC, env *Env) bool {
	return false
}

func (g GetFileAction) VerifyResponse(t *TC, r *http.Request, resp *http.Response) {
	require.Equal(t, 200, resp.StatusCode, "expected OK")
	if g.Compression {
		require.True(t, resp.Uncompressed, "expected compressed response from the server")
	} else {
		require.Equal(t, g.File.Size, resp.ContentLength, "expected content length")
	}
	_, _, err := mime.ParseMediaType(resp.Header.Get("Content-Type"))
	require.NoError(t, err, "expected valid content type")
	require.NoError(t, CompareFileContent(t, resp.Body, g.File), "file content mismatch")
}

// GetDirAction is an Action, which returns directory listing in response.
type GetDirAction struct {
	Path       string
	Dir        *EnvDir
	FullVerify bool
	PathOnDisk string
}

func (g GetDirAction) VerifyBefore(t *TC, workdir string) {
	RequireDir(t, workdir, g.Path, g.Dir)
}

func (g GetDirAction) VerifyAfter(t *TC, workdir string) {
	RequireDir(t, workdir, g.Path, g.Dir)
}

func (g GetDirAction) ApplyEnv(t *TC, env *Env) bool {
	return false
}

func (g GetDirAction) VerifyResponse(t *TC, r *http.Request, resp *http.Response) {
	require.Equal(t, 200, resp.StatusCode, "expected OK")
	content, err := io.ReadAll(resp.Body)
	require.NoError(t, err, "expected response to be read without errors")

	strlist := string(content)
	for name := range g.Dir.Listing {
		require.Contains(t, strlist, name, "expected dir listing to contain child %s", name)
	}

	if !g.FullVerify {
		return
	}

	// On macOS install coreutils and use ls->gls.
	// ls "-lA" "--time-style=+%Y-%m-%d %H:%M:%S"
	entries, err := os.ReadDir(g.PathOnDisk)
	require.NoError(t, err, "expected to read dir %s without errors", g.PathOnDisk)

	// Checking that for every entry there is a corresponding entry in the listing, in the format:
	// dr-xr-xr-x naorlov naorlov 100 2020-01-01 12:34:00 directory_name
	for _, entry := range entries {
		info, err := entry.Info()
		require.NoError(t, err, "expected to read info for entry %s", entry.Name())

		entryStr := fmt.Sprintf("%d %s %s",
			info.Size(),
			info.ModTime().Format("2006-01-02 15:04:05"),
			info.Name(),
		)
		require.Contains(t, strlist, entryStr, "expected dir listing to contain entry %s with full info", entryStr)
	}
}

// CreateDirAction is an Action, which creates a directory.
type CreateDirAction struct {
	Path       string
	Name       string
	Parent     *EnvDir
	PathOnDisk string
}

func (c CreateDirAction) VerifyBefore(t *TC, workdir string) {
	RequireNotExists(t, workdir, c.Path)
}

func (c CreateDirAction) VerifyAfter(t *TC, workdir string) {
	RequireDir(t, workdir, c.Path, c.Parent)
	entries, err := os.ReadDir(c.PathOnDisk)
	require.NoError(t, err, "expected to read dir %s without errors", c.PathOnDisk)
	require.Empty(t, entries, "expected dir %s to be empty", c.PathOnDisk)
}

func (c CreateDirAction) ApplyEnv(t *TC, env *Env) bool {
	_, exist := c.Parent.CreateDir(c.Name)
	require.False(t, exist)
	return true
}

func (c CreateDirAction) VerifyResponse(t *TC, r *http.Request, resp *http.Response) {
	// TODO: we may require specific status code, should we?
	return
}

// CreateFileAction is an Action, which creates a file.
type CreateFileAction struct {
	Path    string
	Name    string
	Parent  *EnvDir
	Content *EnvFile
}

func (c CreateFileAction) VerifyBefore(t *TC, workdir string) {
	RequireNotExists(t, workdir, c.Path)
}

func (c CreateFileAction) VerifyAfter(t *TC, workdir string) {
	RequireFileContent(t, workdir, c.Path, c.Content)
}

func (c CreateFileAction) ApplyEnv(t *TC, env *Env) bool {
	c.Parent.Listing[c.Name] = c.Content
	return true
}

func (c CreateFileAction) VerifyResponse(t *TC, r *http.Request, resp *http.Response) {
	// TODO: we may require specific status code, should we?
	return
}

// ReplaceFileAction is an Action, which replaces file content.
type ReplaceFileAction struct {
	Path       string
	Name       string
	Parent     *EnvDir
	OldContent *EnvFile
	NewContent *EnvFile
}

func (r ReplaceFileAction) VerifyBefore(t *TC, workdir string) {
	RequireFileContent(t, workdir, r.Path, r.OldContent)
}

func (r ReplaceFileAction) VerifyAfter(t *TC, workdir string) {
	RequireFileContent(t, workdir, r.Path, r.NewContent)
}

func (r ReplaceFileAction) ApplyEnv(t *TC, env *Env) bool {
	r.Parent.Listing[r.Name] = r.NewContent
	return true
}

func (r ReplaceFileAction) VerifyResponse(t *TC, req *http.Request, resp *http.Response) {
	// TODO: we may require specific status code, should we?
	return
}

// DeleteAction is an Action, which deletes a file or directory.
type DeleteAction struct {
	Path   string
	Parent *EnvDir
	Name   string
}

func (d DeleteAction) VerifyBefore(t *TC, workdir string) {
	RequireExists(t, workdir, d.Path)
}

func (d DeleteAction) VerifyAfter(t *TC, workdir string) {
	RequireNotExists(t, workdir, d.Path)
}

func (d DeleteAction) ApplyEnv(t *TC, env *Env) bool {
	delete(d.Parent.Listing, d.Name)
	return true
}

func (d DeleteAction) VerifyResponse(t *TC, r *http.Request, resp *http.Response) {
	require.Equal(t, 200, resp.StatusCode, "expected OK")
}

// Action returns action for the query, or nil if query shouldn't do anything.
func (q *Query) Action(env *Env, opts *RunOpts) Action {
	if opts.ServerDomain != "" && q.HostHeader != opts.ServerDomain {
		return HttpErrorAction{
			Status: 400,
		}
	}

	parent, child := env.Lookup(q.Path)

	switch q.Method {
	case "GET":
		if child == nil {
			return HttpErrorAction{
				Status: 404,
			}
		}
		if f, ok := child.(*EnvFile); ok {
			return GetFileAction{
				Path:        q.Path,
				File:        f,
				Compression: q.Gzip,
			}
		}
		if d, ok := child.(*EnvDir); ok {
			return GetDirAction{
				Path:       q.Path,
				Dir:        d,
				FullVerify: q.VerifyDirectoryFull,
				PathOnDisk: path.Join(opts.WorkingDirectory, q.Path),
			}
		}

		// shouldn't get here
		return nil
	case "POST":
		if child != nil {
			return HttpErrorAction{
				Status: 409,
			}
		}
		if parent == nil {
			// TODO: we may require specific error, should we?
			return nil
		}
		_, name := path.Split(q.Path)
		if q.CreateDirectory {
			return CreateDirAction{
				Path:       q.Path,
				Name:       name,
				Parent:     parent,
				PathOnDisk: path.Join(opts.WorkingDirectory, q.Path),
			}
		}
		return CreateFileAction{
			Path:    q.Path,
			Name:    name,
			Parent:  parent,
			Content: q.FileContent,
		}
	case "PUT":
		if child == nil {
			// TODO: we may require specific error, should we?
			return nil
		}
		f, ok := child.(*EnvFile)
		if !ok {
			return HttpErrorAction{
				Status: 409,
			}
		}

		_, name := path.Split(q.Path)
		return ReplaceFileAction{
			Path:       q.Path,
			Name:       name,
			Parent:     parent,
			OldContent: f,
			NewContent: q.FileContent,
		}
	case "DELETE":
		if child == nil {
			// TODO: we may require specific error, should we?
			return nil
		}
		_, ok := child.(*EnvDir)
		if ok && !q.RemoveDirectory {
			return HttpErrorAction{
				Status: 406,
			}
		}
		_, name := path.Split(q.Path)
		return DeleteAction{
			Path:   q.Path,
			Parent: parent,
			Name:   name,
		}
	}

	return nil
}
