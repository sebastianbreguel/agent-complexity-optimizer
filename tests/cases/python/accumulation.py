import copy

import numpy as np
import pandas as pd


def concat_frames(frames):
    df = pd.DataFrame()
    for frame in frames:
        df = pd.concat([df, frame])  # expect: quadratic-accumulation
    return df


def list_plus(items):
    out = []
    for item in items:
        out = out + [item]  # expect: quadratic-accumulation
    return out


def dict_spread(pairs):
    merged = {}
    for key, value in pairs:
        merged = {**merged, key: value}  # expect: quadratic-accumulation
    return merged


def set_union(groups):
    seen = set()
    for group in groups:
        seen = seen | {group.key}  # expect: quadratic-accumulation
    return seen


def extend_in_place(items):
    out = []
    for item in items:
        out += [item]
    return out


def np_append(values):
    arr = np.array([])
    for v in values:
        arr = np.append(arr, v)  # expect: quadratic-accumulation
    return arr


def queue_pop(queue):
    while queue:
        queue.pop(0)  # expect: list-shift-in-loop


def stack_pop(stack):
    while stack:
        stack.pop()


def iterate_rows(df):
    for _, row in df.iterrows():  # expect: dataframe-row-loop
        print(row)


def apply_rows(df):
    return df.apply(lambda r: r.a + r.b, axis=1)  # expect: dataframe-row-loop


def vectorized(df):
    return df["a"] + df["b"]


def deep_copies(items, template):
    return [copy.deepcopy(template) for _ in items]  # expect: deep-copy-in-loop


def sort_each_group(groups):
    for group in groups:
        group.sort()


def resort(items, extra):
    for x in extra:
        items.append(x)
        items.sort()  # expect: sort-in-loop
