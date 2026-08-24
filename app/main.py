import sys

from app.gui import JCLClickerApp


def main():
    app = JCLClickerApp()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
