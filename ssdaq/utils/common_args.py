import ssdaq


def verbosity(parser):
    parser.add_argument('-V','--verbosity',nargs='?',const='DEBUG',default='INFO', dest='verbose', type=str,
                        help='Set log level',choices=['DEBUG','INFO','WARN','ERROR','FATAL'])

def version(parser):
    parser.add_argument('-v', '--version', action='version', version='%(prog)s ' + ssdaq.__version__)