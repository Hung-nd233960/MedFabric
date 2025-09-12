# medfabric/db/utils/delete_db.py
# pylint: disable=missing-module-docstring, missing-function-docstring, unused-import
from medfabric.db.database import Base, return_engine
from medfabric.db import orm_model


def delete_all_tables():
    print("Dropping all tables...")
    print("Discovered tables:", Base.metadata.tables.keys())
    engine = return_engine()
    Base.metadata.drop_all(engine)
    print("✅ Tables dropped successfully.")


if __name__ == "__main__":
    delete_all_tables()
