# pylint: disable=unused-import, missing-function-docstring, missing-module-docstring, unused-import
# medfabric/db/init_db.py
from medfabric.db.database import Base, return_engine
from medfabric.db import orm_model

engine = return_engine()
print(engine.url)


def init_db():
    print("Creating all tables...")
    print("Discovered tables:", Base.metadata.tables.keys())
    Base.metadata.create_all(bind=engine)
    print("✅ Tables created successfully.")


if __name__ == "__main__":
    init_db()
