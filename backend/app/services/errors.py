"""Domain exception hierarchy for MedFabric 3.0."""


class MedFabricError(Exception):
    """Base for all MedFabric errors."""


# Auth / credentials
class AuthError(MedFabricError):
    pass


class InvalidCredentialsError(AuthError):
    pass


class UserNotFoundError(AuthError):
    pass


class UnauthorizedError(AuthError):
    pass


class InactiveAccountError(AuthError):
    pass


# Database
class DatabaseError(MedFabricError):
    pass


class DuplicateEntryError(DatabaseError):
    pass


class ConstraintViolationError(DatabaseError):
    pass


# DataSet
class DataSetError(MedFabricError):
    pass


class DataSetNotFoundError(DataSetError):
    pass


class DataSetAlreadyExistsError(DataSetError):
    pass


class InvalidDataSetError(DataSetError):
    pass


# Patient
class PatientError(MedFabricError):
    pass


class PatientNotFoundError(PatientError):
    pass


class PatientAlreadyExistsError(PatientError):
    pass


class PatientInvalidDataError(PatientError):
    pass


# ImageSet
class ImageSetError(MedFabricError):
    pass


class ImageSetNotFoundError(ImageSetError):
    pass


class ImageSetAlreadyExistsError(ImageSetError):
    pass


class InvalidImageSetError(ImageSetError):
    pass


class InvalidImageSetPathError(ImageSetError):
    pass


# Image
class ImageError(MedFabricError):
    pass


class ImageNotFoundError(ImageError):
    pass


class InvalidImageError(ImageError):
    pass


# Evaluation
class EvaluationError(MedFabricError):
    pass


class EvaluationNotFoundError(EvaluationError):
    pass


class EvaluationAlreadyExistsError(EvaluationError):
    pass


class InvalidEvaluationError(EvaluationError):
    pass


# Annotation session
class AnnotationSessionError(MedFabricError):
    pass


class AnnotationSessionNotFoundError(AnnotationSessionError):
    pass


class AnnotationSessionAlreadySubmittedError(AnnotationSessionError):
    pass


# Login session
class LoginSessionError(MedFabricError):
    pass


class LoginSessionNotFoundError(LoginSessionError):
    pass


# Assignment
class AssignmentError(MedFabricError):
    pass


class AssignmentNotFoundError(AssignmentError):
    pass


# DICOM
class InvalidDicomFileError(MedFabricError):
    pass
