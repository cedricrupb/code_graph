import os
import argparse
import json

from time import time

from tqdm import tqdm

from glob import glob

import code_graph as cg

def load_examples(files):
    for n, file in enumerate(files):
        name = os.path.basename(file)
        desc = "File %d / %d: %s" % (n+1, len(files), name)
        total = sum(1 for _ in open(file, "r"))
        with open(file, "r") as lines:
            for line in tqdm(lines, total = total, desc = desc):
                yield json.loads(line)

def tokens_to_text(tokens):
    method_text =  " ".join(tokens)
    return "public class Test{\n%s\n}" % method_text


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input_dir")
    parser.add_argument("result_file")
    args = parser.parse_args()

    if os.path.isfile(args.input_dir):
        files = [args.input_dir]
    else:
        files = glob(os.path.join(args.input_dir, "*.jsonl"))

    run_times = open(args.result_file, "w")

    for example in load_examples(files):
        tokens = example["tokens"]
        length = len(tokens)
        code   = tokens_to_text(tokens)

        start_time = time()

        try:
            graph = cg.codegraph(code, lang = "java", syntax_error = "raise")
        except Exception as e:
            print(e)
            continue

        end_time = time() - start_time
        
        run_times.write(json.dumps([length, len(graph), end_time]) + "\n")

if __name__ == '__main__':
    main()