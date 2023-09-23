package hw3test

import "math/rand"

// EnvGen contains config for generating test environment.
// Test environment is a directory with files and subdirectories.
type EnvGen struct {
	// Generated file tree will not contain subdirectories deeper than this depth.
	MaxDepth int
	// Generated file tree will not contain more than this number of subdirs.
	MaxDirs int
	// Generated file tree will not contain more than this number of files.
	MaxFiles int
	// Generated files will be text files.
	TextOnly bool
	// Maximum file size in KB
	MaxFileSizeKB int
	// TempDirectory will contain subdirectory for every new environment.
	TempDirectory string
	// Allow to use env for configuration.
	AllowEnv bool
	// Filename generator.
	FilenameGen func(r *rand.Rand) string
}

// GenerateFile returns file with random contents.
func (g *EnvGen) GenerateFile(r *rand.Rand) *EnvFile {
	return &EnvFile{
		GenSeed:  r.Int63(),
		Size:     r.Int63n(1024 * int64(g.MaxFileSizeKB)),
		TextOnly: g.TextOnly,
	}
}

// Generate generates whole file tree.
func (g *EnvGen) Generate(seed int64) (*Env, error) {
	r := rand.New(rand.NewSource(seed))
	root := &EnvDir{Listing: map[string]EnvNode{}}

	dirs := []*EnvDir{root}

	for i := 0; i < g.MaxDirs; i++ {
		parent := dirs[r.Intn(len(dirs))]
		if parent.Depth >= g.MaxDepth {
			continue
		}

		name := g.FilenameGen(r)
		newDir, exist := parent.CreateDir(name)
		if exist {
			continue
		}
		dirs = append(dirs, newDir)
	}

	for i := 0; i < g.MaxFiles; i++ {
		parent := dirs[r.Intn(len(dirs))]

		name := g.FilenameGen(r)
		_, exist := parent.Listing[name]
		if exist {
			continue
		}

		parent.Listing[name] = g.GenerateFile(r)
	}

	return &Env{
		RootDir: root,
	}, nil
}
