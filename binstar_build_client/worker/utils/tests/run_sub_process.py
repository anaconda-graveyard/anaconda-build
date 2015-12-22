from __future__ import unicode_literals, print_function

import subprocess as sp


def main():
    p0 = sp.Popen(['sleep', '100'])

    print("p0", p0.pid)

    p0.wait()


if __name__ == '__main__':
    main()
