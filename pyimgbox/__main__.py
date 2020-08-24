def main():
    import sys

    from . import _cli
    sys.exit(_cli.run(sys.argv[1:]))
