#!/usr/bin/env python3

import torch

# Checking for PyTorch
try:
	print(f"PyTorch version: {torch.__version__}")
except:
	print("PyTorch is not installed or there was an error checking its version.")
	exit()

# Checking for Cuda
if not torch.cuda.is_available():
	print("CUDA is not available. This program requires a GPU.")
	exit()

print("Environment is ready.")
