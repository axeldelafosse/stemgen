import sys
import os

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

import pretty


def main():
    pretty.pretty_collection()


if __name__ == "__main__":
    main()
