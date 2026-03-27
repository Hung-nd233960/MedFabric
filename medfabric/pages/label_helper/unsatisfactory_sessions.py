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
    scores = {
        "c_left_score": img.c_left_score,
        "c_right_score": img.c_right_score,
        "ic_left_score": img.ic_left_score,
        "ic_right_score": img.ic_right_score,
        "l_left_score": img.l_left_score,
        "l_right_score": img.l_right_score,
        "i_left_score": img.i_left_score,
        "i_right_score": img.i_right_score,
        "m1_left_score": img.m1_left_score,
        "m1_right_score": img.m1_right_score,
        "m2_left_score": img.m2_left_score,
        "m2_right_score": img.m2_right_score,
        "m3_left_score": img.m3_left_score,
        "m3_right_score": img.m3_right_score,
        "m4_left_score": img.m4_left_score,
        "m4_right_score": img.m4_right_score,
        "m5_left_score": img.m5_left_score,
        "m5_right_score": img.m5_right_score,
        "m6_left_score": img.m6_left_score,
        "m6_right_score": img.m6_right_score,
    }
    return region_score_requirements(
        img.region,
        mode=VerificationMode.LENIENT,
        **scores,
    ) and validate_evaluation_scores(
        mode=VerificationMode.LENIENT,
        **scores,
    )
