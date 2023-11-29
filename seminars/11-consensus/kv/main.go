package main

import (
	context "context"
	"encoding/json"
	"io"
	"kv/proto"
	"log"
	"net"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"time"

	"github.com/Jille/raft-grpc-leader-rpc/leaderhealth"
	"github.com/Jille/raft-grpc-leader-rpc/rafterrors"
	transport "github.com/Jille/raft-grpc-transport"
	"github.com/Jille/raftadmin"
	"github.com/caarlos0/env/v6"
	"github.com/hashicorp/raft"
	raftboltdb "github.com/hashicorp/raft-boltdb"
	"google.golang.org/grpc"
	"google.golang.org/grpc/reflection"
)

type kv struct {
	mu sync.RWMutex
	m  map[string]string
}

func (k *kv) get(key string) string {
	k.mu.RLock()
	defer k.mu.RUnlock()
	return k.m[key]
}

func (k *kv) set(key, val string) string {
	k.mu.Lock()
	defer k.mu.Unlock()
	old := k.m[key]
	k.m[key] = val
	return old
}

func (k *kv) json() []byte {
	k.mu.Lock()
	defer k.mu.Unlock()
	b, err := json.Marshal(k.m)
	if err != nil {
		panic(err)
	}
	return b
}

func (k *kv) cas(key, old, new string) string {
	k.mu.Lock()
	defer k.mu.Unlock()
	cur := k.m[key]
	if cur == old {
		k.m[key] = new
	}
	return cur
}

// Apply implements raft.FSM
func (k *kv) Apply(entry *raft.Log) interface{} {
	query := string(entry.Data)
	data := strings.Split(query, ",")

	log.Printf("query: %s", data)

	for len(data) < 4 {
		data = append(data, "")
	}

	switch data[0] {
	case "get":
		return k.get(data[1])
	case "set":
		return k.set(data[1], data[2])
	case "cas":
		return k.cas(data[1], data[2], data[3])
	case "json":
		return string(k.json())
	}

	return nil
}

// Restore implements raft.FSM
func (k *kv) Restore(snapshot io.ReadCloser) error {
	m := map[string]string{}
	if err := json.NewDecoder(snapshot).Decode(&m); err != nil {
		return err
	}
	k.mu.Lock()
	defer k.mu.Unlock()
	k.m = m
	return nil
}

// Snapshot implements raft.FSM
func (k *kv) Snapshot() (raft.FSMSnapshot, error) {
	b := k.json()
	return &kvSnapshot{b}, nil
}

type kvSnapshot struct {
	b []byte
}

// Persist implements raft.FSMSnapshot
func (k *kvSnapshot) Persist(sink raft.SnapshotSink) error {
	if _, err := sink.Write(k.b); err != nil {
		return err
	}
	return sink.Close()
}

// Release implements raft.FSMSnapshot
func (k *kvSnapshot) Release() {
}

var _ raft.FSM = (*kv)(nil)

type rpcInterface struct {
	raft *raft.Raft
	proto.UnimplementedExampleServer
}

// Query implements proto.ExampleServer
func (rpc *rpcInterface) Query(ctx context.Context, q *proto.QueryRequest) (*proto.QueryResponse, error) {
	f := rpc.raft.Apply([]byte(q.GetQuery()), time.Second)
	if err := f.Error(); err != nil {
		return nil, rafterrors.MarkRetriable(err)
	}
	if resp, ok := f.Response().(string); ok {
		return &proto.QueryResponse{Response: resp}, nil
	}

	return &proto.QueryResponse{
		Response: "nil response",
	}, nil
}

// =============
// Raft
// =============

type config struct {
	Addr          string   `env:"ADDR" envDefault:"localhost:50051"`
	Dir           string   `env:"DIR" envDefault:"/srv"`
	RaftBootstrap bool     `env:"RAFT_BOOTSTRAP" envDefault:"true"`
	RaftServers   []string `env:"RAFT_SERVERS" envDefault:"raft1:50051,raft2:50051,raft3:50051"`
}

func main() {
	cfg := config{}
	if err := env.Parse(&cfg); err != nil {
		log.Fatal(err)
	}

	sock, err := net.Listen("tcp", cfg.Addr)
	if err != nil {
		log.Fatal(err)
	}

	c := raft.DefaultConfig()
	c.LocalID = raft.ServerID(cfg.Addr)

	baseDir := cfg.Dir

	ldb, err := raftboltdb.NewBoltStore(filepath.Join(baseDir, "logs.dat"))
	if err != nil {
		log.Fatalf(`boltdb.NewBoltStore(%q): %v`, filepath.Join(baseDir, "logs.dat"), err)
	}

	sdb, err := raftboltdb.NewBoltStore(filepath.Join(baseDir, "stable.dat"))
	if err != nil {
		log.Fatalf(`boltdb.NewBoltStore(%q): %v`, filepath.Join(baseDir, "stable.dat"), err)
	}

	fss, err := raft.NewFileSnapshotStore(baseDir, 3, os.Stderr)
	if err != nil {
		log.Fatalf(`raft.NewFileSnapshotStore(%q, ...): %v`, baseDir, err)
	}

	tm := transport.New(raft.ServerAddress(cfg.Addr), []grpc.DialOption{grpc.WithInsecure()})

	fsm := &kv{m: make(map[string]string)}

	r, err := raft.NewRaft(c, fsm, ldb, sdb, fss, tm.Transport())
	if err != nil {
		log.Fatalf("raft.NewRaft: %v", err)
	}

	if cfg.RaftBootstrap {
		servers := make([]raft.Server, len(cfg.RaftServers))
		for i, addr := range cfg.RaftServers {
			servers[i] = raft.Server{
				ID:      raft.ServerID(addr),
				Address: raft.ServerAddress(addr),
			}
		}
		cfg := raft.Configuration{
			Servers: servers,
		}
		f := r.BootstrapCluster(cfg)
		if err := f.Error(); err != nil {
			log.Printf("raft.BootstrapCluster: %v", err)
		}
	}

	s := grpc.NewServer()
	tm.Register(s)
	proto.RegisterExampleServer(s, &rpcInterface{
		raft: r,
	})
	leaderhealth.Setup(r, s, []string{"Example"})
	raftadmin.Register(s, r)
	reflection.Register(s)
	if err := s.Serve(sock); err != nil {
		log.Fatalf("failed to serve: %v", err)
	}
}
