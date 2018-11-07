import sys
import argparse



def parse_args(parser, commands):
    # Divide argv by commands
    split_argv = [[]]
    for c in sys.argv[1:]:
        if c in commands.choices:
            split_argv.append([c])
        else:
            split_argv[-1].append(c)
    # Initialize namespace
    args = argparse.Namespace()
    for c in commands.choices:
        setattr(args, c, None)
    # Parse each command
    parser.parse_args(split_argv[0], namespace=args)  # Without command
    for argv in split_argv[1:]:  # Commands
        n = argparse.Namespace()
        setattr(args, argv[0], n)
        parser.parse_args(argv, namespace=n)
    return args

from pyparsing import alphas, oneOf, delimitedList,nums, Literal, Word, Combine, Optional, Suppress

ESC = Literal('\x1b')
integer = Word(nums)
escapeSeq = Combine(ESC + '[' + Optional(delimitedList(integer,';')) + 
                oneOf(list(alphas)))

nonAnsiString = lambda s : Suppress(escapeSeq).transformString(s)

def tof(strc):
    if(strc == 'True'):
        return msg.colr('gf',strc)
    elif(strc == 'False'):
        return msg.colr('rf',strc)
    else:
        return strc

def pretty_cam_print(data_dict,size=4,type='s',tm_numbers=False):
    size+=1
    ms = ''
    fms = ''
    for i in range(6):
        ms += '|%%-%d%s|'%(size*0,type)
        fms += '|%s|'%(' '*size)

    tbs = ' '*(size+2)
    ftbs = ' '*(size+2)
    for i in range(4):
        tbs += '|%%-%d%s|'%(size*0,type)
        ftbs += '|%s|'%(' '*size)
    
    for k,v in data_dict.items():
        data_dict[k] = v.center(len(v)-len(nonAnsiString(v))+size,' ')
    enum_tm = {}
    for i in range(32):
        s = msg.colr('fv','TM-%02d'%(i))
        enum_tm[i] = s.center(len(s)-len(nonAnsiString(s))+size,' ')
    
    print(ftbs)
    if(tm_numbers): print(tbs%(tuple([enum_tm[i] for i in range(0,4)])))
    print(tbs%(tuple([data_dict[i] for i in range(0,4)])))
    print(ftbs);print(fms)
    if(tm_numbers): print(ms%(tuple([enum_tm[i] for i in range(4,10)])))
    print(ms%(tuple([data_dict[i] for i in range(4,10)])))
    print(fms);print(fms)
    if(tm_numbers): print(ms%(tuple([enum_tm[i] for i in range(10,16)])))
    print(ms%(tuple([data_dict[i] for i in range(10,16)])))
    print(fms);print(fms)
    if(tm_numbers): print(ms%(tuple([enum_tm[i] for i in range(16,22)])))
    print(ms%(tuple([data_dict[i] for i in range(16,22)])))
    print(fms);print(fms)
    if(tm_numbers): print(ms%(tuple([enum_tm[i] for i in range(22,28)])))
    print(ms%(tuple([data_dict[i] for i in range(22,28)])))
    print(fms);print(ftbs)
    if(tm_numbers): print(tbs%(tuple([enum_tm[i] for i in range(28,32)])))
    print(tbs%(tuple([data_dict[i] for i in range(28,32)])))
    print(ftbs)

def clear_pretty_cam_print(tm_numbers=False):
    if(tm_numbers):
        print('\033[25A ')
    else:
        print('\033[19A ')

def print_message(msg):
    print('Received reply from: %s@%s'%(msg['name'],msg['ip']))
    print('Status: %s'%msg['status'])
    print(msg['msg'])

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    colrmap = {'v':HEADER,'b':OKBLUE,'g':OKGREEN,'y':WARNING,'r':FAIL,'f':BOLD,'u':UNDERLINE,'e':ENDC}

class msg:
    
    @staticmethod
    def colr(fmt,s):
        if(len(fmt)>1):
            return "".join([bcolors.colrmap[k] for k in fmt])+s+bcolors.colrmap['e']
        else:
            return bcolors.colrmap[fmt]+s+bcolors.colrmap['e']
    
    @staticmethod
    def warn(s):
        return bcolors.WARNING+bcolors.BOLD+"Warning:"+bcolors.ENDC+bcolors.WARNING+" %s"%s+bcolors.ENDC
    
    @staticmethod
    def err(s):
        print(bcolors.FAIL+"Error: %s"%s+bcolors.ENDC)


# # noinspection PyShadowingNames
# def parse_args(parser, commands):
#     # Divide argv by commands
#     split_argv = []
#     for c in sys.argv[1:]:
#         print(parser._option_string_actions.keys())
#         # noinspection PyProtectedMember
#         if c in commands.choices or c in parser._option_string_actions.keys():
#             if c == '-h' and len(split_argv) >= 1:
#                 split_argv[-1].append(c)
#             else:
#                 split_argv.append([c])
#         else:
#             raise Exception('Argument "{0}" unknown.'.format(c))
#     # Initialize namespace
#     args = argparse.Namespace()
#     for c in commands.choices:
#         setattr(args, c, None)
#     # Parse each command
#     if len(split_argv) == 0:
#         split_argv.append(['-h'])  # if no command was given
#     parser.parse_args(split_argv[0], namespace=args)  # Without command
#     for argv in split_argv[1:]:  # Commands
#         n = argparse.Namespace()
#         setattr(args, argv[0], n)
#         parser.parse_args(argv, namespace=n)
#     return args
