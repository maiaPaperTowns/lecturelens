# Lecture 3 — Binary Search and Divide-and-Conquer

## Background and Motivation

This lecture introduces binary search and situates it within the broader family
of divide-and-conquer algorithms. Before we begin, recall that a *sorted array*
is one in which every element is less than or equal to the element that follows
it. Linear search inspects elements one at a time and therefore takes time
proportional to the number of elements. For large datasets that cost becomes
unacceptable, which is the motivation for a faster approach.

Historically, the idea of repeatedly halving a search interval predates
computers; it appears in numerical methods such as the bisection method for
finding roots of a continuous function.

## Definition

Binary search is defined as an algorithm that locates a target value within a
sorted array by repeatedly dividing the search interval in half. At each step it
compares the target with the middle element of the current interval and discards
the half that cannot contain the target.

The *search interval* is the contiguous range of indices, described by a low
bound and a high bound, that might still contain the target.

## The Core Rule

Theorem: on an array of n elements, binary search runs in O(log n) time in the
worst case, because each comparison halves the number of remaining candidates.

The loop invariant maintained by binary search is that if the target appears in
the array, then its index always lies between the current low and high bounds.
This invariant is what makes the algorithm correct: when the interval becomes
empty, we can conclude the target is absent.

## Process

Step 1: initialise low to 0 and high to n minus 1.
Step 2: while low is less than or equal to high, compute the midpoint.
Step 3: if the middle element equals the target, return the midpoint.
Step 4: if the middle element is smaller than the target, move low above the midpoint.
Step 5: otherwise move high below the midpoint, and repeat from Step 2.

## Implementation Detail

```python
def binary_search(a: list[int], target: int) -> int:
    lo, hi = 0, len(a) - 1
    while lo <= hi:
        mid = lo + (hi - lo) // 2
        if a[mid] == target:
            return mid
        if a[mid] < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1
```

Watch for integer overflow when computing the midpoint: writing
`mid = lo + (hi - lo) // 2` avoids overflowing in languages with fixed-width
integers. The function returns -1 when the key is absent, so every caller must
check the return value before using it as an index.

## Worked Example

For example, searching for 9 in the array [1, 3, 4, 7, 9, 11, 15] proceeds as
follows. The first midpoint is index 3 holding value 7; since 7 is smaller than
9, we move low to index 4. The next midpoint is index 5 holding value 11; since
11 is larger than 9, we move high to index 4. Finally low equals high equals 4,
the middle element is 9, and we return index 4.

## Comparison with Alternatives

Unlike linear search, binary search requires the input to be sorted, but it is
dramatically faster on large inputs. Compared with a hash table, binary search
is slower for pure membership queries — a hash table offers average constant
time lookup — but binary search preserves order, so it also answers
predecessor, successor and range queries that a hash table cannot.

Binary search versus interpolation search: interpolation search can reach
O(log log n) on uniformly distributed data but degrades to O(n) on skewed data,
whereas binary search is a dependable O(log n) regardless of distribution.

## Divide and Conquer in General

Binary search is the simplest divide-and-conquer algorithm: it divides the
problem into subproblems, but only ever recurses into one of them. Merge sort
and quicksort recurse into both halves and then combine results. The master
theorem gives the asymptotic complexity of such recurrences in closed form.
