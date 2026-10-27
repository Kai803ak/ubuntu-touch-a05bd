// SPDX-License-Identifier: GPL-3.0-only
#define _GNU_SOURCE
#include <sys/socket.h>
#include <sys/un.h>
#include <sys/stat.h>
#include <unistd.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <fcntl.h>
int main(int argc, char **argv) {
  if (strstr(argv[0], "session")) {
    if(access("/run/a05bd-ram-recovery", F_OK)) return 90;
    if(setgid(0) || setuid(0)) return 91;
    if(argc>1) execl("/bin/sh","sh","-c",argv[1],NULL);
    else execl("/bin/sh","sh",NULL);
    return 92;
  }
  mkdir("/dev/socket",0755);
  int s=socket(AF_UNIX,SOCK_STREAM,0);
  struct sockaddr_un a={.sun_family=AF_UNIX};
  strcpy(a.sun_path,"/dev/socket/adbd"); unlink(a.sun_path);
  if(s<0 || bind(s,(struct sockaddr*)&a,sizeof(a)) || listen(s,4)) {perror("adbd socket"); return 1;}
  if(s!=3) {if(dup2(s,3)<0) return 2;close(s);} fcntl(3,F_SETFD,0);
  char pid[32];snprintf(pid,sizeof(pid),"%d",getpid());
  setenv("LISTEN_PID",pid,1);setenv("LISTEN_FDS","1",1);setenv("LISTEN_FDNAMES","adbd",1);
  setenv("ANDROID_SOCKET_adbd","3",1);setenv("ADBD_SECURE","0",1);
  setenv("LD_LIBRARY_PATH","/usr/lib/aarch64-linux-gnu/android:/lib/aarch64-linux-gnu",1);
  execl("/usr/bin/adbd","adbd",NULL);perror("exec adbd");return 3;
}
