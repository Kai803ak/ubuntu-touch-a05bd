/* SPDX-License-Identifier: Apache-2.0 */
#include <fcntl.h>
#include <unistd.h>
int main(void) {
    int fd = -1;
    for (int attempt = 0; attempt < 10 && fd < 0; ++attempt) {
        fd = open("/dev/watchdog0", O_WRONLY);
        if (fd < 0) fd = open("/dev/watchdog", O_WRONLY);
        if (fd < 0) sleep(1);
    }
    if (fd < 0) return 1;
    int config = open("/proc/wdk", O_WRONLY);
    if (config >= 0) { (void)write(config, "1 30\n", 5); close(config); }
    for (;;) { if (write(fd, ".", 1) != 1) return 2; sleep(2); }
}
