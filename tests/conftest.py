import copy

import pytest

from commercegraph.dataset import load_dataset
from commercegraph.graph import build_graph


@pytest.fixture
def dataset():
    return load_dataset()[0]


@pytest.fixture
def raw(dataset):
    return copy.deepcopy(dataset.model_dump(mode="json"))


@pytest.fixture
def graph(dataset):
    return build_graph(dataset)
