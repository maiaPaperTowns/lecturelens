# Lecture 7 — CPU Scheduling in Operating Systems

## Introduction

This lecture covers how an operating system decides which ready process or
thread should run next on a CPU. Scheduling sits at the heart of the kernel and
directly shapes responsiveness, throughput and fairness. In this course we will
build on the process model introduced earlier: a process is a program in
execution, together with its address space, open files and register state.

## Key Definitions

A *ready queue* is the set of processes that are runnable and waiting for a CPU.

The *scheduler* is the kernel component that selects a process from the ready
queue; the *dispatcher* is the mechanism that performs the context switch to
give that process control of the CPU.

A context switch refers to saving the register state of the currently running
process and restoring the register state of the next one. Context switches are
pure overhead: no useful work happens while one is in progress.

*CPU burst* denotes an interval during which a process uses the CPU without
blocking; an *I/O burst* is an interval spent waiting for a device.

## Scheduling Metrics

We evaluate a scheduling policy along several axes. Throughput is the number of
processes completed per unit time. Turnaround time is the total time from
submission to completion. Waiting time is the time spent in the ready queue.
Response time is the delay from submission until the first response is produced.

Rule of thumb: interactive systems optimise for low response time, whereas batch
systems optimise for high throughput and low turnaround time.

## First-Come, First-Served

First-come, first-served scheduling runs processes in arrival order and never
preempts them. It is trivial to implement with a FIFO queue. However, it suffers
from the convoy effect: one long CPU-bound process forces many short processes
to wait behind it, inflating average waiting time.

## Shortest Job First

Shortest job first selects the process with the smallest next CPU burst.

Theorem: shortest job first is optimal in the sense that it minimises average
waiting time for a fixed set of processes. The catch is that the length of the
next CPU burst is not known in advance and must be estimated, typically with an
exponential moving average of previous bursts.

## Round Robin

Round robin scheduling gives each process a fixed time quantum and then preempts
it, moving it to the back of the ready queue. Choosing the quantum is a
tradeoff: a very small quantum improves response time but wastes CPU cycles on
frequent context switches, while a very large quantum degenerates into
first-come, first-served.

## Priority and Multilevel Feedback Queues

Priority scheduling runs the highest-priority ready process first. A well-known
hazard is starvation: a steady stream of high-priority work can prevent a
low-priority process from ever running. The standard remedy is aging, which
gradually raises the priority of processes that have waited a long time.

The multilevel feedback queue generalises this: it maintains several queues with
different quanta and priorities, and moves a process between queues based on its
observed behaviour, so that I/O-bound and interactive jobs float to the top.

## Comparison

Compared with first-come, first-served, round robin bounds response time at the
cost of more context switches. Compared with strict priority scheduling, a
multilevel feedback queue adapts to workload and avoids starvation through
aging, but it introduces several parameters that must be tuned per system.

## Implementation Note

In a real kernel the scheduler runs inside the timer interrupt handler. The
handler updates accounting, decrements the current process's remaining quantum,
and, if the quantum has expired or a higher-priority task became ready, sets a
flag that triggers the dispatcher on the return path from the interrupt.
