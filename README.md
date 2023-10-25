# concurrent
Experimenting with some parallelization designs.

Potentially feasible use cases:

1. Process monitoring from separate thread. 
2. Loading pickle files in separate process. This makes it easier to clean up unused memory after reading a file.
  + see [this](https://stackoverflow.com/questions/1316767/how-can-i-explicitly-free-memory-in-python/1316799#1316799) and [this](https://stackoverflow.com/questions/1316767/how-can-i-explicitly-free-memory-in-python/1316799#1316799)
3. Manage database queries in separate process.

