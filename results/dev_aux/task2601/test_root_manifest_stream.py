import pytest

from results.dev_aux.task2601.audit_train_root_concentration_v2 import (
    extract_object_value,
)


def test_skips_nested_non_target_array_without_decoding_its_rows():
    text = r'{"evaluation":[{"literal":"]}","escaped":"\\\"["}],"train":[{"id":1}]}'
    assert extract_object_value(text, "train") == [{"id": 1}]


def test_reads_target_when_it_is_first_and_skips_later_object():
    text = '{"train":[1,2],"evaluation":{"nested":[true,null]}}'
    assert extract_object_value(text, "train") == [1, 2]


def test_missing_target_is_not_silently_accepted():
    with pytest.raises(KeyError):
        extract_object_value('{"evaluation":[]}', "train")
