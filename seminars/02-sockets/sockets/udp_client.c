#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <string.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <arpa/inet.h>
#include <netinet/in.h>

#define MAXLINE 1024

int main(int argc, char** argv) {
  int sockfd;
  char buffer[MAXLINE];
  char *hello = "Hello from client";
  struct sockaddr_in client;

  if ((sockfd = socket(AF_INET, SOCK_DGRAM, 0)) < 0) {
    perror("socket creation failed");
    _exit(EXIT_FAILURE);
  }

  memset(&client, 0, sizeof(client));

  client.sin_family = AF_INET;
  client.sin_addr.s_addr = INADDR_ANY;
  client.sin_port = htons(strtoul(argv[1], NULL, 10));
  int n;
  int len;
  sendto(sockfd, (const char *)hello, strlen(hello),
         MSG_CONFIRM, (const struct sockaddr *)&client,
          sizeof(client));
  printf("Hello message sent.\n");

  n = recvfrom(sockfd, (char *)buffer, MAXLINE,
               MSG_WAITALL, (struct sockaddr *)&client,
               &len);
  buffer[n] = '\0';
  printf("Server : %s\n", buffer);

  close(sockfd);
  return 0;
}