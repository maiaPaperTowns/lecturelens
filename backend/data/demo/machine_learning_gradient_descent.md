# Lecture 5 — Gradient Descent and the Bias–Variance Tradeoff

## Motivation

This lecture introduces gradient descent, the workhorse optimisation algorithm
behind most of modern machine learning, and then connects model capacity to
generalisation through the bias–variance tradeoff. The prerequisite is basic
multivariable calculus: the gradient of a scalar function is the vector of its
partial derivatives and points in the direction of steepest increase.

## Definition of the Learning Problem

Supervised learning is defined as the task of estimating a function from labelled
examples so that it predicts well on unseen data. We choose a model family
parameterised by a weight vector, define a loss function that measures error on
the training set, and search for weights that make the loss small.

The *empirical risk* is the average loss over the training set. The *true risk*
is the expected loss over the underlying data distribution, which we never
observe directly.

## Gradient Descent

Gradient descent is an iterative algorithm that updates the weights by taking a
step in the direction opposite to the gradient of the loss. The step size is
called the learning rate.

Step 1: initialise the weights, often to small random values.
Step 2: compute the gradient of the loss with respect to the weights.
Step 3: subtract the learning rate times the gradient from the weights.
Step 4: repeat until the loss stops decreasing.

Rule: if the loss function is convex and the learning rate is small enough,
gradient descent converges to the global minimum. For non-convex losses, such
as those of neural networks, it converges only to a stationary point.

## Stochastic and Mini-Batch Variants

Batch gradient descent computes the gradient over the entire training set before
each update, which is accurate but slow. Stochastic gradient descent estimates
the gradient from a single example, and mini-batch gradient descent uses a small
random subset. The mini-batch approach is the standard compromise: it is far
cheaper per step and the gradient noise it introduces can help escape sharp
minima.

## Implementation Detail

```python
def sgd_step(weights, grad_fn, batch, lr=0.01):
    grad = grad_fn(weights, batch)
    return weights - lr * grad
```

A learning rate that is too large causes the loss to oscillate or diverge; one
that is too small makes training needlessly slow. Learning-rate schedules and
adaptive methods such as Adam adjust the effective step size per parameter over
the course of training.

## Overfitting and the Bias–Variance Tradeoff

Overfitting occurs when a model fits noise in the training data and therefore
generalises poorly. The bias–variance tradeoff explains this. Bias is the error
from wrong modelling assumptions; a linear model has high bias on a curved
relationship. Variance is the error from sensitivity to the particular training
sample; a very flexible model has high variance.

Theorem: the expected test error decomposes into bias squared, variance, and
irreducible noise. Reducing one term often increases another, so the goal is to
choose model capacity that minimises their sum.

## Regularisation

L2 regularisation adds a penalty proportional to the squared norm of the weights
to the loss, which shrinks weights toward zero and reduces variance. L1
regularisation adds a penalty proportional to the absolute value of the weights
and tends to drive some of them exactly to zero, producing a sparse model.

For example, adding L2 regularisation to linear regression yields ridge
regression, whose closed-form solution simply adds a small constant to the
diagonal before inverting.

## Comparison

Compared with gradient descent, second-order methods such as Newton's method use
curvature information and converge in fewer iterations, but each iteration costs
far more because it forms and inverts a Hessian matrix. In contrast, gradient
descent needs only first derivatives and scales to models with billions of
parameters, which is why it dominates deep learning.
