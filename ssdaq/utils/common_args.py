import ssdaq


def verbosity(parser):
    parser.add_argument(
        "-V",
        "--verbosity",
        nargs="?",
        const="DEBUG",
        default="INFO",
        dest="verbose",
        type=str,
        help="Set log level",
        choices=["DEBUG", "INFO", "WARN", "ERROR", "FATAL"],
    )


def version(parser):
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version="%(prog)s SSDAQ v" + ssdaq.__version__,
    )


def subport(parser, default=5555):
    parser.add_argument(
        "-l", dest="sub_port", type=int, default=default, help="subscription port"
    )


def subaddr(parser, default="127.0.0.101"):
    parser.add_argument(
        "-i",
        dest="sub_ip",
        type=str,
        default=default,
        help="subscription address/interface",
    )


def n_outputs(parser):
    parser.add_argument(
        "-n",
        dest="n_outputs",
        type=int,
        default=None,
        help="the number of outputs to dump to before exiting (if not set there is no limit)",
    )


def filename(parser):
    parser.add_argument("filename", type=str, help="Output file name")
