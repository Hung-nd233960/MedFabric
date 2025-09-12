from medfabric.db.utils.delete_db import delete_all_tables
from medfabric.db.utils.init_db import init_db


def reset_database():
    delete_all_tables()
    init_db()
    print("Database has been reset.")


if __name__ == "__main__":
    reset_database()
