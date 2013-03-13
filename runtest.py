#!/usr/bin/python
import sys
from os import system


def main(argc, argv):
    try:
        params = [ x for x in argv if x.startswith('-') ]
        suite = [ x for x in argv if not x.startswith('-') ]
        
        test_class, test_case = suite[1].split(".", 1)
        return system("nosetests test/%s.py:%s %s" % (test_class, test_case,
           " ".join(params)))
    except:
        print("usage: %s [params] testsuite.class.case ")
        return 1

if __name__ == '__main__':
    (argc, argv) = (len(sys.argv), sys.argv)
    exit(main(argc, argv))
