from typing import List
from medfabric.api.image_evaluation_input import (
    region_score_requirements,
    validate_evaluation_scores,
    VerificationMode,
)
from medfabric.pages.label_helper.session_initialization import (
    ImageSetEvaluationSession,
    ImageEvaluationSession,
)
from medfabric.db.models import Region


def find_unsatisfactory_sessions(
    sessions: List[ImageSetEvaluationSession],
) -> List[int]:
    """Identify indices of image set evaluation sessions that do not meet quality criteria.
    Criteria for satisfactory sessions:
    1. If marked as low_quality or irrelevant_data, automatically satisfactory.
    2. Must contain at least one image evaluated in the CoronaRadiata region.
    3. Must contain at least one image evaluated in the BasalCentral region."""

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

    unsatisfactory = []

    for idx, sess in enumerate(sessions):
        # Case 1: if low_quality or irrelevant, it's automatically satisfactory
        if sess.low_quality or sess.irrelevant_data:
            continue

        all_scores_valid = True
        required_regions = {
            Region.CoronaRadiata: False,
            Region.BasalCentral: False,
            Region.BasalCortex: False,
        }

        for img in sess.images_sessions:
            if not score_based_evaluation(img):
                all_scores_valid = False
            if img.region in required_regions:
                required_regions[img.region] = True

        # check completeness
        has_all_required = all(required_regions.values())

        if not (all_scores_valid and has_all_required):
            unsatisfactory.append(idx)

    return unsatisfactory
