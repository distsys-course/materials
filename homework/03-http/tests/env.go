package hw3test

import (
	"io"
	"math/rand"
	"os"
	"path"
	"sort"
	"strings"
)

// Env contains information about all files in the test environment.
// Can be written to disk.
type Env struct {
	RootDir *EnvDir
}

// Lookup returns the node for the given path.
func (e *Env) Lookup(p string) (*EnvDir, EnvNode) {
	p = path.Clean(p)
	dir, file := path.Split(p)

	dirs := strings.Split(dir, "/")
	dirs = dirs[:len(dirs)-1]

	parent := e.RootDir
	for _, d := range dirs {
		nxt, ok := parent.Listing[d]
		if !ok {
			return nil, nil
		}
		parent, ok = nxt.(*EnvDir)
		if !ok {
			// not a directory
			return nil, nil
		}
	}

	nxt := parent.Listing[file]
	return parent, nxt
}

// Clone returns deep clone of an Env.
func (e *Env) Clone() *Env {
	return &Env{
		RootDir: e.RootDir.Clone().(*EnvDir),
	}
}

// EnvNode is a file/dir.
type EnvNode interface {
	// WriteToDisk persists node and its children to disk.
	WriteToDisk(path string) error

	// Stats aggregates stats of the node and its children.
	Stats(path string, stats *Stats)

	// Clone creates a deep copy of the node.
	Clone() EnvNode
}

// EnvDir is a virtual directory, that can be written to disk.
type EnvDir struct {
	Listing map[string]EnvNode
	Depth   int
}

func (d *EnvDir) WriteToDisk(p string) error {
	err := os.Mkdir(p, 0777)
	if err != nil {
		return err
	}

	for name, writter := range d.Listing {
		nxt := path.Join(p, name)
		err := writter.WriteToDisk(nxt)
		if err != nil {
			return err
		}
	}
	return nil
}

func (d *EnvDir) Stats(p string, stats *Stats) {
	stats.Dirs++
	stats.DirPaths = append(stats.DirPaths, p)
	for name, node := range d.Listing {
		node.Stats(path.Join(p, name), stats)
	}
}

func (d *EnvDir) Clone() EnvNode {
	newDir := &EnvDir{
		Listing: map[string]EnvNode{},
		Depth:   d.Depth,
	}

	for name, node := range d.Listing {
		newDir.Listing[name] = node.Clone()
	}
	return newDir
}

func (d *EnvDir) CreateDir(name string) (dir *EnvDir, exist bool) {
	_, exist = d.Listing[name]
	if exist {
		return nil, exist
	}

	newDir := &EnvDir{
		Listing: map[string]EnvNode{},
		Depth:   d.Depth + 1,
	}
	d.Listing[name] = newDir
	return newDir, false
}

// EnvFile is a virtual file, that can be written to disk.
type EnvFile struct {
	GenSeed  int64
	Size     int64
	TextOnly bool
}

func (f *EnvFile) Open() io.Reader {
	var gen io.Reader = rand.New(rand.NewSource(f.GenSeed))
	if f.TextOnly {
		gen = &TextReader{gen}
	}
	gen = io.LimitReader(gen, f.Size)
	return gen
}

func (f *EnvFile) WriteToDisk(p string) error {
	file, err := os.OpenFile(p, os.O_RDWR|os.O_CREATE|os.O_TRUNC, 0666)
	if err != nil {
		return err
	}
	defer file.Close()

	reader := f.Open()
	_, err = io.Copy(file, reader)
	return err
}

func (f *EnvFile) Stats(p string, stats *Stats) {
	stats.Files++
	stats.Size += f.Size
	stats.FilePaths = append(stats.FilePaths, p)
}

func (f *EnvFile) Clone() EnvNode {
	return &EnvFile{
		GenSeed:  f.GenSeed,
		Size:     f.Size,
		TextOnly: f.TextOnly,
	}
}

// Stats is a helper for listing all files/dirs in environment.
type Stats struct {
	// Number of directories in the environment.
	Files int

	// Count of directories in the environment.
	Dirs int

	// Size of all files in the environment.
	Size int64

	// FilePaths to all files in the environment.
	FilePaths []string

	// DirPaths to all directories in the environment.
	DirPaths []string
}

// Normalize will fix stats to be deterministic and don't contain root dir.
func (s *Stats) Normalize() {
	sort.Strings(s.FilePaths)
	sort.Strings(s.DirPaths)

	if len(s.DirPaths) > 0 && s.DirPaths[0] == "" {
		s.DirPaths = s.DirPaths[1:]
	}
}
