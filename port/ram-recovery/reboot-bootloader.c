#include <unistd.h>
#include <sys/syscall.h>
#include <linux/reboot.h>
#include <stdio.h>
int main(int argc, char **argv) {
 (void)argv;
 if (argc != 1) return 2;
 syscall(SYS_reboot, LINUX_REBOOT_MAGIC1, LINUX_REBOOT_MAGIC2,
         LINUX_REBOOT_CMD_RESTART2, "bootloader");
 perror("reboot bootloader");
 return 1;
}
