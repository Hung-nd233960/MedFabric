from typing import Optional, List
import uuid as uuid_lib
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from pydantic import ValidationError
from medfabric.db.orm_model import DataSet
from medfabric.db.pydantic_model import DataSetCreate, DataSetRead
from medfabric.api.errors import (
    DataSetAlreadyExistsError,
    InvalidDataSetError,
    DatabaseError,
)


def check_data_set_exists_by_name(session: Session, name: str) -> bool:
    """
    Check if a data set with the given name exists.

    Args:
        session (Session): SQLAlchemy DB session
        name (str): Name of the data set to check
    Returns:
        True if exists, False otherwise
    """
    return session.query(DataSet).filter_by(name=name).one_or_none() is not None


def check_data_set_exists_by_uuid(
    session: Session, data_set_uuid: uuid_lib.UUID
) -> bool:
    """
    Check if a data set with the given UUID exists.

    Args:
        session (Session): SQLAlchemy DB session
        data_set_uuid (uuid.UUID): UUID of the data set to check
    Returns:
        True if exists, False otherwise
    """
    return (
        session.query(DataSet).filter_by(dataset_uuid=data_set_uuid).one_or_none()
        is not None
    )


def add_data_set(
    session: Session,
    name: str,
    description: Optional[str] = None,
    dataset_uuid: Optional[uuid_lib.UUID] = None,
) -> DataSet:
    """
    Add a new data set to the database.

    Args:
        session (Session): SQLAlchemy DB session
        name (str): Name of the data set
        description (str, optional): Description of the data set
        dataset_uuid (uuid.UUID, optional): UUID for the data set. If None, a new UUID will be generated.

    Returns:
        The created DataSet object

    Raises:
        DataSetAlreadyExistsError: If a data set with the same name already exists
        InvalidDataSetError: If the provided name is invalid
        DatabaseError: If there is a database error during the operation
    """
    try:
        data_set_validator = DataSetCreate(
            name=name, description=description, dataset_uuid=dataset_uuid
        )
        name_ = data_set_validator.name
        description_ = data_set_validator.description
        dataset_uuid_ = data_set_validator.dataset_uuid
    except ValidationError as exc:
        raise InvalidDataSetError(f"Invalid data set data: {exc}") from exc

    if not name_ or not name_.strip():
        raise InvalidDataSetError("Data set name cannot be empty.")

    if check_data_set_exists_by_name(session, name_):
        raise DataSetAlreadyExistsError(f"Data set with name '{name_}' already exists.")
    if dataset_uuid_:
        if check_data_set_exists_by_uuid(session, dataset_uuid_):
            raise DataSetAlreadyExistsError(
                f"Data set with ID '{dataset_uuid_}' already exists."
            )
    data_set = DataSet(name=name_, description=description_, dataset_uuid=dataset_uuid_)
    try:
        session.add(data_set)
        session.commit()
        session.refresh(data_set)
        return data_set
    except SQLAlchemyError as exc:
        session.rollback()
        raise DatabaseError(f"Failed to add data set: {exc}") from exc


def get_data_set(session: Session, uuid: uuid_lib.UUID) -> Optional[DataSetRead]:
    """
    Retrieve a data set by its UUID.

    Args:
        session (Session): SQLAlchemy DB session
        uuid (uuid.UUID): UUID of the data set to retrieve

    Returns:
        DataSet if found, None otherwise
    """
    data_set = session.query(DataSet).filter_by(dataset_uuid=uuid).first()
    if data_set:
        return DataSetRead.model_validate(
            data_set
        )  # validate or not does not matter to be honest since SQLAlchemy output corresponding data
    return None


def get_all_data_sets(session: Session) -> List[DataSetRead]:
    """
    Retrieve all data sets from the database.

    Args:
        session (Session): SQLAlchemy DB session
    Returns:
        List of all DataSet records
    """
    data_sets = session.query(DataSet).all()
    return [DataSetRead.model_validate(ds) for ds in data_sets]


def exist_any_data_set(session: Session) -> bool:
    """
    Check if there is at least one data set in the database.

    Args:
        session (Session): SQLAlchemy DB session
    Returns:
        True if at least one data set exists, False otherwise
    """
    return session.query(DataSet).first() is not None
