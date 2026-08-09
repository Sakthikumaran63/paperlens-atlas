import app.db.sqlite_shim  # noqa: F401
from sqlalchemy.orm import DeclarativeBase



class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy 2.x models in PaperLens.
    """
    pass
