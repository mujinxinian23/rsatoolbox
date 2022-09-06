#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# cython: profile=True

import cython
from cython.view cimport array as cvarray
from libc.math cimport log, sqrt, isnan, NAN
from cpython.mem cimport PyMem_Malloc, PyMem_Realloc, PyMem_Free
cimport scipy.linalg.cython_blas as blas
# import numpy as np

# np.import_array()

@cython.boundscheck(False)
@cython.cdivision(True)
cpdef double [:] calc(
    double [:, :] data, long [:] desc,
    long [:] cv_desc, int n,
    int method_idx, double [:, :] noise=None,
    double prior_lambda=1, double prior_weight=0.1,
    int weighting=1, int crossval=0):
    # calculates an RDM from a double array of data with integer descriptors
    # There are no checks or saveguards in this function!
    # All entries in desc should be in [0, n-1]. They will be used for indexing
    # into the RDM running into segfaults if they are outside the range.
    # Inputs:
    # double [:, :] data : the data
    # long [:] desc : defines the patterns
    # long [:] cv_desc : rows with equal values are excluded from the computation
    # int n : defines the RDM size, all desc should be < n
    # int method_idx: which method to use:
    #     1: method == 'euclidean'
    #     2: method == 'correlation'
    #     3: method in ['mahalanobis', 'crossnobis']
    #     4: method in ['poisson', 'poisson_cv']
    # double [:, :] noise = None: noise for Mahalanobis/Crossnobis
    # double prior_lambda=1 : for poisson KL
    # double prior_weight=0.1 : for poisson KL
    # int weighting=1 : controls weighting of rows:
    #     0: each row has equal weight
    #     1: rows weighted by number of valid measurements
    cdef:
        double [:] vec_i
        double [:] vec_j
        double weight, sim
        double [:] weights
        double [:] values
        int i, j, idx
        int n_rdm = (n * (n-1)) / 2
        int n_dim = data.shape[1]
        double prior_lambda_l = prior_lambda * prior_weight
        double prior_weight_l = 1 + prior_weight
        double [:, :] log_data
    if (method_idx > 4) or (method_idx < 1):
        raise ValueError('dissimilarity method not recognized!')
    # precompute stuff for poisson KL
    if method_idx == 4:
        data = data.copy()
        log_data = data.copy()
        for i in range(data.shape[0]):
            for j in range(n_dim):
                data[i, j] = (data[i, j] + prior_lambda_l) / prior_weight_l
                log_data[i, j] = log(data[i, j])
    weights = <double [:(n_rdm+n)]> PyMem_Malloc((n_rdm+n) * sizeof(double))
    values = <double [:(n_rdm+n)]> PyMem_Malloc((n_rdm+n) * sizeof(double))
    for idx in range(n_rdm + n):
        weights[idx] = 0
        values[idx] = 0
    for i in range(data.shape[0]):
        if not crossval:
            if method_idx == 1: # method == 'euclidean':
                sim, weight = euclid(data[i], data[i], n_dim)
            elif method_idx == 2: # method == 'correlation':
                sim, weight = correlation(data[i], data[i], n_dim)
            elif method_idx == 3: # method in ['mahalanobis', 'crossnobis']:
                if noise is None:
                    sim, weight = euclid(data[i], data[i], n_dim)
                else:
                    sim = mahalanobis(data[i], data[i], n_dim, noise)
                    weight = <double> n_dim
            elif method_idx == 4: # method in ['poisson', 'poisson_cv']:
                sim, weight = poisson_cv(data[i], data[i], log_data[i], log_data[i], n_dim)
            idx = desc[i]
            if weighting == 1: #'number':
                values[idx] += sim / 2
                weights[idx] += weight / 2
            elif weighting == 0: #'equal':
                values[idx] += sim / weight / 2
                weights[idx] += 1 / 2
        for j in range(i + 1, data.shape[0]):
            if not crossval or not cv_desc[i] == cv_desc[j]:
                #vec_i = data[i]
                #vec_j = data[j]
                if method_idx == 1: # method == 'euclidean':
                    sim, weight = euclid(data[i], data[j], n_dim)
                elif method_idx == 2: # method == 'correlation':
                    sim, weight = correlation(data[i], data[j], n_dim)
                elif method_idx == 3: # method in ['mahalanobis', 'crossnobis']:
                    if noise is None:
                        sim, weight = euclid(data[i], data[i], n_dim)
                    else:
                        sim = mahalanobis(data[i], data[j], n_dim, noise)
                        weight = <double> n_dim
                elif method_idx == 4: # method in ['poisson', 'poisson_cv']:
                    sim, weight = poisson_cv(data[i], data[j], log_data[i], log_data[j], n_dim)
                if weight > 0:
                    if desc[i] == desc[j]:
                        idx = desc[i]
                    else:
                        if desc[j] > desc[i]:
                            idx = (n - 1) * desc[i] - (((desc[i] + 1) * desc[i]) / 2) + desc[j] - 1 + n
                        else:
                            idx = (n - 1) * desc[j] - (((desc[j] + 1) * desc[j]) / 2) + desc[i] - 1 + n
                    if weighting == 1: #'number':
                        values[idx] += sim
                        weights[idx] += weight
                    elif weighting == 0: #'equal':
                        values[idx] += sim / weight
                        weights[idx] += 1
    for idx in range(n_rdm + n):
        if weights[idx] > 0:
            values[idx] = values[idx] / weights[idx]
        else:
            values[idx] = NAN
    return values


@cython.boundscheck(False)
@cython.cdivision(True)
cpdef (double, double) calc_one(
    double [:, :] data_i, double [:, :] data_j,
    long [:] cv_desc_i, long [:] cv_desc_j,
    int n_i, int n_j,
    int method_idx, double [:, :] noise=None,
    double prior_lambda=1, double prior_weight=0.1,
    int weighting=1):
    cdef:
        #double [:] values = np.zeros(n_i * n_j)
        #double [:] weights = np.zeros(n_i * n_j)
        double [:] vec_i
        double [:] vec_j
        double weight, sim, weight_sum, value
        int i, j
        int n_dim = data_i.shape[1]
        double prior_lambda_l = prior_lambda * prior_weight
        double prior_weight_l = 1 + prior_weight
        double [:, :] log_data_i
        double [:, :] log_data_j
    if (method_idx > 4) or (method_idx < 1):
        raise ValueError('dissimilarity method not recognized!')
    # precompute stuff for poisson KL
    if method_idx == 4:
        data_i = data_i.copy()
        log_data_i = data_i.copy()
        for i in range(data_i.shape[0]):
            for j in range(n_dim):
                data_i[i, j] = (data_i[i, j] + prior_lambda_l) / prior_weight_l
                log_data_i[i, j] = log(data_i[i, j])
        data_j = data_j.copy()
        log_data_j = data_j.copy()
        for i in range(data_j.shape[0]):
            for j in range(n_dim):
                data_j[i, j] = (data_j[i, j] + prior_lambda_l) / prior_weight_l
                log_data_j[i, j] = log(data_j[i, j])
    weight_sum = 0
    for i in range(n_i):
        for j in range(n_j):
            if not cv_desc_i[i] == cv_desc_j[j]:
                if method_idx == 1: # method == 'euclidean':
                    sim, weight = euclid(data_i[i], data_j[j], n_dim)
                elif method_idx == 2: # method == 'correlation':
                    sim, weight = correlation(data_i[i], data_j[j], n_dim)
                elif method_idx == 3: # method in ['mahalanobis', 'crossnobis']:
                    if noise is None:
                        sim, weight = euclid(data_i[i], data_j[j], n_dim)
                    else:
                        sim = mahalanobis(data_i[i], data_j[j], n_dim, noise)
                        weight = <double> n_dim
                elif method_idx == 4: # method in ['poisson', 'poisson_cv']:
                    sim, weight = poisson_cv(data_i[i], data_j[j], log_data_i[i], log_data_j[j], n_dim)
                if weight > 0:
                    if weighting == 1: #'number':
                        value += sim
                        weight_sum += weight
                    elif weighting == 0: #'equal':
                        value += sim / weight
                        weight_sum += 1
    if weight_sum > 0:
        value = value / weight_sum
    else:
        value = NAN
    return value, weight_sum


@cython.boundscheck(False)
cpdef (double, double) similarity(double [:] vec_i, double [:] vec_j, int method_idx,
                       int n_dim, double [:, :] noise):
    """
    double similarity(double [:] vec_i, double [:] vec_j, int method_idx,
                      int n_dim, double [:, :] noise=None)

    This is a single similarity computation in cython.
    remember to call everything with continuous numpy arrays.
    In particular, noise must be such an array for Mahalanobis distances!

    Mahalanobis distances require full measurement vectors at the moment!
    """
    cdef double sim
    cdef double weight
    if method_idx == 1: # method == 'euclidean':
        sim, weight = euclid(vec_i, vec_j, n_dim)
    elif method_idx == 2: # method == 'correlation':
        sim, weight = correlation(vec_i, vec_j, n_dim)
    elif method_idx == 3: # method in ['mahalanobis', 'crossnobis']:
        if noise is None:
            sim, weight = euclid(vec_i, vec_j, n_dim)
        else:
            sim = mahalanobis(vec_i, vec_j, n_dim, noise)
            weight = <double> n_dim
    return sim, weight


@cython.boundscheck(False)
cdef (double, double) euclid(double [:] vec_i, double [:] vec_j, int n_dim):
    cdef:
        double sim = 0
        double weight = 0
        int i
    for i in range(n_dim):
        if not isnan(vec_i[i]) and not isnan(vec_j[i]):
            sim += vec_i[i] * vec_j[i]
            weight += 1
    return sim, weight


@cython.boundscheck(False)
@cython.cdivision(True)
cdef (double, double) poisson_cv(double [:] vec_i, double [:] vec_j,
                                 double [:] log_vec_i, double [:] log_vec_j,
                                 int n_dim):
    cdef:
        double sim = 0
        double weight = 0
        int i
    for i in range(n_dim):
        if not isnan(vec_i[i]) and not isnan(vec_j[i]):
            sim += (vec_j[i] - vec_i[i]) * (log_vec_i[i] - log_vec_j[i])
            weight += 1
    sim = sim / 2.0
    return (sim, weight)


@cython.boundscheck(False)
cdef double mahalanobis(double [:] vec_i, double [:] vec_j, int n_dim,
                        double [:, :] noise):
    cdef:
        double *vec1
        double *vec2
        int *finite
        int zero = 0
        int one = 1
        double onef = 1.0
        double zerof = 0.0
        char trans = b'n'
        double sim = 0.0
        int i, j, k, l, n_finite
        double [:, :] noise_small
    finite = <int*> PyMem_Malloc(n_dim * sizeof(int))
    # use finite as a bool to choose the non-nan values
    n_finite = 0
    for i in range(n_dim):
        if not isnan(vec_i[i]) and not isnan(vec_j[i]):
            finite[i] = 1
            n_finite += 1
        else:
            finite[i] = 0
    vec1 = <double*> PyMem_Malloc(n_finite * sizeof(double))
    vec2 = <double*> PyMem_Malloc(n_finite * sizeof(double))
    vec3 = <double*> PyMem_Malloc(n_finite * sizeof(double))
    #noise_small = <double [:n_finite, :n_finite]> PyMem_Malloc(n_finite * n_finite * sizeof(double))
    noise_small = cvarray(shape=(n_finite, n_finite), itemsize=sizeof(double), format="d")
    k = 0
    for i in range(n_dim):
        if finite[i]:
            vec1[k] = vec_i[i]
            vec2[k] = vec_j[i]
            l = 0
            for j in range(n_dim):
                if finite[j]:
                    noise_small[k, l] = noise[i, j]
                    l += 1
            k += 1
    blas.dgemv(&trans, &n_finite, &n_finite, &onef, &noise_small[0, 0], &n_finite, vec2, &one, &zerof, vec3, &one)
    for i in range(n_dim):
        sim += vec1[i] * vec3[i]
    PyMem_Free(vec1)
    PyMem_Free(vec2)
    PyMem_Free(vec3)
    PyMem_Free(finite)
    return sim


@cython.boundscheck(False)
@cython.cdivision(True)
cdef (double, double) correlation(double [:] vec_i, double [:] vec_j, int n_dim):
    cdef:
        double si = 0.0
        double sj = 0.0
        double si2 = 0.0
        double sj2 = 0.0
        double sij = 0.0
        double sim
        double weight = 0
        int i
    for i in range(n_dim):
        if not isnan(vec_i[i]) and not isnan(vec_j[i]):
            si += vec_i[i]
            sj += vec_j[i]
            si2 += vec_i[i] * vec_i[i]
            sj2 += vec_j[i] * vec_j[i]
            sij += vec_i[i] * vec_j[i]
            weight += 1
    if si2 > 0 and sj2 > 0:
        # sim = (np.sum(vec_i * vec_j) / np.sqrt(norm_i) / np.sqrt(norm_j))
        sim = sij - (si * sj / n_dim)
        sim /= sqrt(si2 - (si * si / n_dim))
        sim /= sqrt(sj2 - (sj * sj / n_dim))
    else:
        sim = 1
    sim = sim * n_dim / 2
    return sim, weight
