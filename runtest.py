#!/usr/bin/python
import sys
from os import system


def main(argc, argv):
    if argc:
        test_class, test_case = argv[1].split(".", 1)
        argv.pop(1)
    system("nosetests test/%s.py:%s %s" % (test_class, test_case,
           " ".join(argv)))

if __name__ == '__main__':
    (argc, argv) = (len(sys.argv), sys.argv)
    exit(main(argc, argv))
