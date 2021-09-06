#include <errno.h>
#include <inttypes.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <arpa/inet.h>
#include <netdb.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <sys/types.h>
#include <unistd.h>

int main(int argc, char **argv) {
  signal(SIGPIPE, SIG_IGN);
  int fd;
  struct addrinfo hints, *res;
  const char *hello = "Hello from client";
  char buffer[1024] = {0};
  int err;
  memset(&hints, 0, sizeof(hints));
  hints.ai_family = AF_INET;
  hints.ai_socktype = SOCK_STREAM;
  err = getaddrinfo(argv[1], argv[2], &hints, &res);
  if (err != 0) {
      printf("%s\n", gai_strerror(err));
      _exit(EXIT_FAILURE);
  }
  if ((fd = socket(PF_INET, SOCK_STREAM, 0)) < 0) {
      perror("socket");
      _exit(EXIT_FAILURE);
  }
  if (connect(fd, res->ai_addr, res->ai_addrlen) < 0) {
      perror("connect");
      close(fd);
      _exit(EXIT_FAILURE);
  }

  freeaddrinfo(res);
  if (write(fd, hello, strlen(hello)) < 0) {
    perror("write");
    close(fd);
    _exit(1);
  }
  if (read(fd, buffer, 1024) < 0) {
    perror("read");
    close(fd);
    _exit(1);
  }
  printf("%s\n", buffer);
  close(fd);
  return 0;
}
