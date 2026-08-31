# Slab Allocator Architecture
- Multi-class power-of-two slab pools (32B to 4KB).
- 64B cache line alignment + 0xDEADBEEF canary guards.
