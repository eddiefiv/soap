import argparse

from argparse import ArgumentParser

argparser = ArgumentParser()

# add an argument
argparser.add_argument("--agent_count", type = int, default = 3)
argparser.add_argument("-d", "--device", default = "cuda", help = "device to use for inferencing", type = str)
argparser.add_argument("-v", "--verbose", help = "increase output verbosity", action = "store_true")
argparser.add_argument("--cl_blast", help = "use CLBlast during inference")

args = argparser.parse_args()

print(args.cl_blast)