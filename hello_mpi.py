"""Hello, MPI. Every rank runs this same program.

    mpiexec -n 4 python hello_mpi.py
"""

import socket

from mpi4py import MPI

comm = MPI.COMM_WORLD
rank = comm.Get_rank()           # this copy's number: 0, 1, 2, ...
size = comm.Get_size()           # how many copies are running

print(f"rank {rank} of {size} on {socket.gethostname()}")

# Each rank holds one number; reduce adds them all up on rank 0.
total = comm.reduce(rank, op=MPI.SUM, root=0)
if rank == 0:
    print(f"rank 0 received the sum of every rank: {total}")
