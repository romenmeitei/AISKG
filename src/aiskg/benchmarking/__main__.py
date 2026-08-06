import argparse
from . import run

parser=argparse.ArgumentParser(description="Run AISKG benchmarking stage")
parser.add_argument("--config", default="config.yaml")
parser.add_argument("--run-id")
args=parser.parse_args()
result=run(args.config,args.run_id)
print(result["release_zip"])
