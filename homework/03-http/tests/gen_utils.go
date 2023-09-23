package hw3test

import (
	"io"
	"math/rand"
)

func SimpleFilenameGenerator(maxLen int) func(r *rand.Rand) string {
	return func(r *rand.Rand) string {
		return GenFilename(r, maxLen)
	}
}

func GenFilename(r *rand.Rand, maxLen int) string {
	// TODO: better filename generation, right now it's only uppercase english letters
	n := r.Intn(maxLen) + 1
	b := make([]byte, n)
	for i := 0; i < n; i++ {
		b[i] = byte(r.Intn(26) + 65)
	}
	return string(b)
}

// TextReader is io.Reader filtering out non-text characters.
type TextReader struct {
	r io.Reader
}

func (t *TextReader) Read(p []byte) (n int, err error) {
	for {
		n, err = t.r.Read(p)
		if n == 0 || err != nil {
			return
		}

		m := 0
		for i := 0; i < n; i++ {
			// p[i] is a plain text character
			if p[i] == '\n' || (p[i] >= 32 && p[i] <= 126) {
				p[m] = p[i]
				m++
			}
		}
		if m == 0 {
			continue
		}
		return m, nil
	}
}
