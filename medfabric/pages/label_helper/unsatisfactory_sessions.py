from medfabric.api.image_evaluation_input import (
    region_score_requirements,
    validate_evaluation_scores,
    VerificationMode,
)
from medfabric.pages.label_helper.session_initialization import (
    ImageEvaluationSession,
)


def score_based_evaluation(img: ImageEvaluationSession) -> bool:
    """Check if the image has valid scores based on its region."""
    has_scores = False
    if region_score_requirements(
        img.region,
        img.basal_score_central_left,
        img.basal_score_central_right,
        img.basal_score_cortex_left,
        img.basal_score_cortex_right,
        img.corona_score_left,
        img.corona_score_right,
        mode=VerificationMode.LENIENT,
    ) and validate_evaluation_scores(
        mode=VerificationMode.LENIENT,
        basal_score_central_left=img.basal_score_central_left,
        basal_score_central_right=img.basal_score_central_right,
        basal_score_cortex_left=img.basal_score_cortex_left,
        basal_score_cortex_right=img.basal_score_cortex_right,
        corona_score_left=img.corona_score_left,
        corona_score_right=img.corona_score_right,
    ):
        has_scores = True
    return has_scores
