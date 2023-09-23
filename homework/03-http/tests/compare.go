package hw3test

import (
	"bufio"
	"fmt"
	"github.com/stretchr/testify/require"
	"io"
	"os"
	"path"
)

// RequireFileContent requires that the contents of the file match the contents of the reader.
func RequireFileContent(t *TC, workdir, p string, f *EnvFile) {
	fullpath := path.Join(workdir, p)
	file, err := os.Open(fullpath)
	require.NoError(t, err, "failed to open file %s, expected it exists on disk", p)
	defer file.Close()

	stat, err := file.Stat()
	require.NoError(t, err, "failed to stat file %s", p)
	require.Equal(t, f.Size, stat.Size(), "file %s has wrong size", p)
	require.NoError(t, CompareFileContent(t, file, f), "file %s has wrong content", p)
}

// CompareFileContent compares first f.Size bytes of the reader with generated content.
func CompareFileContent(t *TC, r io.Reader, f *EnvFile) error {
	bufr := bufio.NewReader(r)
	buff := bufio.NewReader(f.Open())

	for i := int64(0); i < f.Size; i++ {
		b1, err1 := bufr.ReadByte()
		b2, err2 := buff.ReadByte()
		if err1 != nil || err2 != nil {
			if err1 == io.EOF && err2 == io.EOF {
				// unexpected early EOF
				return nil
			}
			if err1 != nil {
				return fmt.Errorf("unexpected file error: %w", err1)
			}
			if err2 != nil {
				return fmt.Errorf("unexpected generator error: %w", err2)
			}
		}
		if b1 != b2 {
			return fmt.Errorf("position %d, expected byte %d, got %d", i, b2, b1)
		}
	}

	return nil
}

// RequireDir ensures that the directory exists on disk.
func RequireDir(t *TC, workdir string, p string, dir *EnvDir) {
	fullpath := path.Join(workdir, p)
	stat, err := os.Stat(fullpath)
	require.NoError(t, err, "failed to stat directory %s, expected it exists on disk", p)
	require.True(t, true, stat.IsDir(), "expected %s to be a directory", p)
}

// RequireNotExists ensures that the file/directory does not exist on disk.
func RequireNotExists(t *TC, workdir string, p string) {
	fullpath := path.Join(workdir, p)
	_, err := os.Stat(fullpath)
	require.True(t, os.IsNotExist(err), "expected %s to not exist on disk", p)
}

// RequireExists ensures that the file/directory exists on disk.
func RequireExists(t *TC, workdir string, p string) {
	fullpath := path.Join(workdir, p)
	_, err := os.Stat(fullpath)
	require.NoError(t, err, "failed to stat %s, expected it exists on disk", p)
}
