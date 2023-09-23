package hw3test

import "math/rand"

// QueriesGen contains config for generating queries.
type QueriesGen struct {
	// Number of queries to generate.
	Count int

	GetFile          bool // Allow GET requests for files.
	GetFileNoErrors  bool // Disable requests for non-existing files.
	GetDirectory     bool // Allow GET requests for directories.
	GetDirectoryFull bool // Verify full directory listing.
	Compression      bool // Allow compression in GET requests.
	Post             bool // Allow POST requests.
	Put              bool // Allow PUT requests.
	Delete           bool // Allow DELETE requests.
	AllHeaders       bool // Allow extra headers.
}

func (g *QueriesGen) Generate(t *TC, env *Env, gen *EnvGen, seeds []int64, opts RunOpts) []Query {
	env = env.Clone()

	stats := &Stats{}
	env.RootDir.Stats("", stats)
	stats.Normalize()

	var methods []string
	if g.GetFile || g.GetDirectory {
		methods = append(methods, "GET")
	}
	if g.Post {
		methods = append(methods, "POST")
	}
	if g.Put {
		methods = append(methods, "PUT")
	}
	if g.Delete {
		methods = append(methods, "DELETE")
	}

	var queries []Query
	for _, seed := range seeds {
		r := rand.New(rand.NewSource(seed))
		method := methods[r.Intn(len(methods))]

		var genPaths []string
		if len(stats.DirPaths) > 0 && !(method == "GET" && !g.GetDirectory) {
			genPaths = append(genPaths, stats.DirPaths[r.Intn(len(stats.DirPaths))])
			genPaths = append(genPaths, stats.DirPaths[r.Intn(len(stats.DirPaths))])
		}
		if len(stats.FilePaths) > 0 && !(method == "GET" && !g.GetFile) {
			genPaths = append(genPaths, stats.FilePaths[r.Intn(len(stats.FilePaths))])
			genPaths = append(genPaths, stats.FilePaths[r.Intn(len(stats.FilePaths))])
		}
		if !(method == "GET" && g.GetFileNoErrors) {
			// TODO: better non-existing path generator
			randomPath := gen.FilenameGen(r) + "/" + gen.FilenameGen(r)
			genPaths = append(genPaths, randomPath)

			if len(stats.DirPaths) > 0 {
				randomDir := stats.DirPaths[r.Intn(len(stats.DirPaths))]
				num := 2
				if method == "POST" {
					num = 4
				}

				for i := 0; i < num; i++ {
					genPaths = append(genPaths, randomDir+"/"+gen.FilenameGen(r))
				}
			}
		}

		if len(genPaths) == 0 {
			continue
		}

		hostHeader := opts.ServerDomain
		if g.AllHeaders && r.Intn(5) == 0 {
			// to get 400
			hostHeader = "hse.ru"
		}

		path := genPaths[r.Intn(len(genPaths))]
		query := Query{
			Seed:                seed,
			Method:              method,
			Path:                path,
			Gzip:                g.Compression && (r.Intn(2) == 1),
			CreateDirectory:     method == "POST" && (r.Intn(2) == 1),
			RemoveDirectory:     method == "DELETE" && (r.Intn(2) == 1),
			HostHeader:          hostHeader,
			VerifyDirectoryFull: g.GetDirectoryFull,
			VerifyHeaders:       g.AllHeaders,
		}

		if (method == "POST" && !query.CreateDirectory) || method == "PUT" {
			query.FileContent = gen.GenerateFile(r)
		}

		queries = append(queries, query)

		action := query.Action(env, &opts)
		if action != nil {
			changed := action.ApplyEnv(t, env)
			if changed {
				stats = &Stats{}
				env.RootDir.Stats("", stats)
				stats.Normalize()
			}
		}
	}

	return queries
}
