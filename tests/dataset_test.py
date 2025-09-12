# tests/dataset_test.py
# pylint: disable=missing-function-docstring, missing-module-docstring
import uuid as uuid_lib
import pytest
from sqlalchemy.orm import Session
from medfabric.db.orm_model import DataSet
from medfabric.api.data_sets import (
    check_data_set_exists_by_uuid,
    check_data_set_exists_by_name,
    add_data_set,
    get_all_data_sets,
)

from medfabric.api.errors import (
    DataSetAlreadyExistsError,
    InvalidDataSetError,
)


def test_add_data_set_success_minimal(db_session: Session):
    ds = add_data_set(db_session, "TestSet1")
    assert ds.name == "TestSet1"
    assert ds.description is None
    assert isinstance(ds.dataset_uuid, uuid_lib.UUID)
    assert check_data_set_exists_by_name(db_session, "TestSet1") is True
    assert check_data_set_exists_by_uuid(db_session, ds.dataset_uuid) is True


def test_add_data_set_success_full(db_session: Session):
    ds_uuid = uuid_lib.uuid4()
    ds = add_data_set(
        db_session,
        "TestSet2",
        description="A test data set",
        dataset_uuid=ds_uuid,
    )
    assert ds.name == "TestSet2"
    assert ds.description == "A test data set"
    assert ds.dataset_uuid == ds_uuid
    assert check_data_set_exists_by_name(db_session, "TestSet2") is True
    assert check_data_set_exists_by_uuid(db_session, ds_uuid) is True


def test_add_data_set_duplicate_name(db_session: Session):
    add_data_set(db_session, "TestSet3")
    with pytest.raises(DataSetAlreadyExistsError):
        add_data_set(db_session, "TestSet3")  # same name


def test_add_data_set_invalid_name(db_session: Session):
    with pytest.raises(InvalidDataSetError):
        add_data_set(db_session, "")  # empty name


def test_get_all_data_sets(db_session: Session):
    # Clear existing data sets
    db_session.query(DataSet).delete()
    db_session.commit()

    add_data_set(db_session, "SetA")
    add_data_set(db_session, "SetB", description="Second set")

    all_sets = get_all_data_sets(db_session)
    assert len(all_sets) == 2
    names = {ds.name for ds in all_sets}
    assert names == {"SetA", "SetB"}


def test_check_data_set_exists_by_name(db_session: Session):
    add_data_set(db_session, "UniqueSet")
    assert check_data_set_exists_by_name(db_session, "UniqueSet") is True
    assert check_data_set_exists_by_name(db_session, "NonExistentSet") is False


def test_check_data_set_exists_by_uuid(db_session: Session):
    ds = add_data_set(db_session, "UUIDSet")
    assert check_data_set_exists_by_uuid(db_session, ds.dataset_uuid) is True
    assert check_data_set_exists_by_uuid(db_session, uuid_lib.uuid4()) is False
