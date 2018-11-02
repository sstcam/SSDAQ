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

def pretty_cam_print(data_dict,size=4,type='s',tm_numbers=False):
    size+=1
    ms = ''
    fms = ''
    for i in range(6):
        ms += '|%%-%d%s|'%(size,type)
        fms += '|%s|'%(' '*size)

    tbs = ' '*(size+2)
    ftbs = ' '*(size+2)
    for i in range(4):
        tbs += '|%%-%d%s|'%(size,type)
        ftbs += '|%s|'%(' '*size)
    tbs += ' '*size
    
    print(ftbs)
    if(tm_numbers): print(tbs%(tuple([('TM-%02d'%(1+i)).center(size,' ') for i in range(0,4)])))
    print(tbs%(tuple([data_dict[i].center(size,' ') for i in range(0,4)])))
    print(ftbs);print(fms)
    if(tm_numbers): print(ms%(tuple([('TM-%02d'%(1+i)).center(size,' ') for i in range(4,10)])))
    print(ms%(tuple([data_dict[i].center(size,' ') for i in range(4,10)])))
    print(fms);print(fms)
    if(tm_numbers): print(ms%(tuple([('TM-%02d'%(1+i)).center(size,' ') for i in range(10,16)])))
    print(ms%(tuple([data_dict[i].center(size,' ') for i in range(10,16)])))
    print(fms);print(fms)
    if(tm_numbers): print(ms%(tuple([('TM-%02d'%(1+i)).center(size,' ') for i in range(16,22)])))
    print(ms%(tuple([data_dict[i].center(size,' ') for i in range(16,22)])))
    print(fms);print(fms)
    if(tm_numbers): print(ms%(tuple([('TM-%02d'%(1+i)).center(size,' ') for i in range(22,28)])))
    print(ms%(tuple([data_dict[i].center(size,' ') for i in range(22,28)])))
    print(fms);print(ftbs)
    if(tm_numbers): print(tbs%(tuple([('TM-%02d'%(1+i)).center(size,' ') for i in range(28,32)])))
    print(tbs%(tuple([data_dict[i].center(size,' ') for i in range(28,32)])))
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
