import os
import gc
import itertools
import numpy as np
import pandas as pd
# local import
import vcfpandas as vp


def default_mapper(fun, iterator):
    return (fun(el) for el in iterator)


def pairwise_diff_mat(df):
    """
    Calculate pairwise difference data frame.
    For Genotype 0,1,2 data frame.
    Uses numpy matrix multiplication.
    """
    cols = df.columns
    diff = pairwise_diff_numpy(df.values)
    gc.collect()
    return pd.DataFrame(diff, index=cols, columns=cols)


def pairwise_diff_numpy(gen_arr):
    """
    ATTENTION: This does not handle nans
    for missing data implement a mask 
    Setting missing to zero beforehand would be wrong.
    """
    n = np.dot(gen_arr.T, np.logical_not(gen_arr)) + \
        np.dot(np.logical_not(gen_arr.T), gen_arr)
    return n


def pw_diff_to_individual(hap_pairwise_diff):
    ind_pairwise_diff = hap_pairwise_diff.sum(
        axis=1, level=0).sum(axis=0, level=0)
    denum = np.ones(ind_pairwise_diff.shape) * 4.
    np.fill_diagonal(denum, 2.)
    return ind_pairwise_diff / denum


def get_pairwise_diff(fn, samples=None, chrom=None, start=None, end=None,
                      dropna=True, chunksize=50000, apply_fun=None,
                      get_result_fun=None):
    """
    Read haplotypes from specific region tabixed vcf.gz file
    and calculate pairwise differences.

    """
    assert dropna, "Na handling not implemented, please use dropna=True"

    def get_pwd(chunk0, chunk1):
        chunk0.columns = pd.MultiIndex.from_arrays(
            [chunk0.columns, [0] * len(chunk0.columns)])
        chunk1.columns = pd.MultiIndex.from_arrays(
            [chunk1.columns, [1] * len(chunk1.columns)])
        hap_chunk = pd.concat([chunk0, chunk1], axis=1).sortlevel(axis=1)
        if dropna:
            hap_chunk.dropna(axis=0, inplace=True)
        dm = pairwise_diff_mat(hap_chunk)
        return dm

    def reduce_fun(pwds):
        dm = reduce(lambda a, b: a + b, pwds)
        dm_ind = pw_diff_to_individual(dm)
        return dm_ind

    dm = vp.map_reduce_haplo(fn, get_pwd, samples_h0=samples,
                             samples_h1=samples, chrom=chrom,
                             start=start, end=end,
                             chunksize=chunksize, apply_fun=apply_fun,
                             get_result_fun=get_result_fun,
                             reduce_fun=reduce_fun)

    return dm

# backwards compatability
get_pairwise_diff_region = get_pairwise_diff
