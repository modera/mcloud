#include <fcntl.h>
#include <sched.h>
#include <unistd.h>
#include <stdlib.h>
#include <stdio.h>
#include <locale.h>

/* A simple error-handling function: print an error message based
   on the value in 'errno' and terminate the calling process */

#define errExit(msg)    do { perror(msg); exit(EXIT_FAILURE); \
                        } while (0)

int main(int argc, char *argv[])
{
    int fd;

    if (argc < 3) {
        fprintf(stderr, "%s PID cmd [arg...]\n", argv[0]);
        exit(EXIT_FAILURE);
    }

    char *namespaces[5] = { "uts", "pid", "net", "ipc", "mnt" };

    int i;
    for (i = 0 ; i < 5 ; i++ )
    {
        char str[20];

        snprintf(str, 20, "/proc/%s/ns/%s", argv[1], namespaces[i]);

        fd = open(str, O_RDONLY);   /* Get descriptor for namespace */
        if (fd == -1)
            errExit("open");

        if (setns(fd, 0) == -1)         /* Join that namespace */
            errExit("setns");
    }

    execvp(argv[2], &argv[2]);      /* Execute a command in namespace */
    errExit("execvp");
}
