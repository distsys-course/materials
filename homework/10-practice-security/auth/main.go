package main

import (
	"crypto/rsa"
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"

	"github.com/golang-jwt/jwt/v5"
)

type UsernamePassword struct {
	Username string `json:"username"`
	Password string `json:"password"`
}

type AuthHandlers struct {
	passwords  map[string][16]byte
	jwtPrivate *rsa.PrivateKey
	jwtPublic  *rsa.PublicKey
}

func NewAuthHandlers(jwtprivateFile string, jwtPublicFile string) *AuthHandlers {
	private, err := os.ReadFile(jwtprivateFile)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	public, err := os.ReadFile(jwtPublicFile)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	jwtPrivate, err := jwt.ParseRSAPrivateKeyFromPEM(private)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	jwtPublic, err := jwt.ParseRSAPublicKeyFromPEM(public)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	return &AuthHandlers{
		passwords:  make(map[string][16]byte),
		jwtPrivate: jwtPrivate,
		jwtPublic:  jwtPublic,
	}
}

func (h *AuthHandlers) signup(w http.ResponseWriter, req *http.Request) {
	if req.Method != http.MethodPost {
		w.WriteHeader(http.StatusBadRequest)
		fmt.Fprintf(w, "signup can be done only with POST HTTP method")
		return
	}
	body := make([]byte, req.ContentLength)
	read, err := req.Body.Read(body)
	defer req.Body.Close()
	if read != int(req.ContentLength) {
		w.WriteHeader(http.StatusBadRequest)
		return
	}
	if err != io.EOF {
		w.WriteHeader(http.StatusInternalServerError)
		fmt.Fprintf(w, "Error reading body: %v", err)
		return
	}
	creds := UsernamePassword{}
	err = json.Unmarshal(body, &creds)
	if err != nil {
		w.WriteHeader(http.StatusBadRequest)
		fmt.Fprintf(w, "Error unmarshalling body: %v", err)
		return
	}

	// TODO: register user, check if exists, generate jwt token and cookie

	http.SetCookie(w, &http.Cookie{
		Name:  "jwt",
		Value: "TODO", // jwt token string
	})
}

func (h *AuthHandlers) login(w http.ResponseWriter, req *http.Request) {
	if req.Method != http.MethodPost {
		w.WriteHeader(http.StatusBadRequest)
		fmt.Fprintf(w, "login can be done only with POST HTTP method")
		return
	}
	body := make([]byte, req.ContentLength)
	read, err := req.Body.Read(body)
	defer req.Body.Close()
	if read != int(req.ContentLength) {
		w.WriteHeader(http.StatusBadRequest)
		return
	}
	if err != io.EOF {
		w.WriteHeader(http.StatusInternalServerError)
		fmt.Fprintf(w, "Error reading body: %v", err)
		return
	}
	creds := UsernamePassword{}
	err = json.Unmarshal(body, &creds)
	if err != nil {
		w.WriteHeader(http.StatusBadRequest)
		fmt.Fprintf(w, "Error unmarshalling body: %v", err)
		return
	}

	// TODO: check if user exists, check password and generate cookie

	http.SetCookie(w, &http.Cookie{
		Name:  "jwt",
		Value: "TODO", // jwt token string
	})
}

func (h *AuthHandlers) whoami(w http.ResponseWriter, req *http.Request) {
	username := "TODO" // TODO: get username from jwt token

	// TODO: check if user exists

	w.Write([]byte("Hello, " + username))
}

func main() {
	privateFile := flag.String("private", "", "path to JWT private key `file`")
	publicFile := flag.String("public", "", "path to JWT public key `file`")
	port := flag.Int("port", 8091, "http server port")
	flag.Parse()

	if port == nil {
		fmt.Fprintln(os.Stderr, "Port is required")
		os.Exit(1)
	}

	if privateFile == nil || *privateFile == "" {
		fmt.Fprintln(os.Stderr, "Please provide a path to JWT private key file")
		os.Exit(1)
	}

	if publicFile == nil || *publicFile == "" {
		fmt.Fprintln(os.Stderr, "Please provide a path to JWT public key file")
		os.Exit(1)
	}

	absoluteprivateFile, err := filepath.Abs(*privateFile)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}

	absolutePublicFile, err := filepath.Abs(*publicFile)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}

	authHandlers := NewAuthHandlers(absoluteprivateFile, absolutePublicFile)

	http.HandleFunc("/signup", authHandlers.signup)
	http.HandleFunc("/login", authHandlers.login)
	http.HandleFunc("/whoami", authHandlers.whoami)

	fmt.Println("Starting server on port", *port, "with jwt private key file", absoluteprivateFile, "and jwt public key file", absolutePublicFile)

	if err = http.ListenAndServe(fmt.Sprintf(":%d", *port), nil); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}
