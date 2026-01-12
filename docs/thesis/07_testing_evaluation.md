# Chapter 7: Testing and Evaluation

## Presentation Outline

**Estimated Length**: 8-12 pages  
**Key Purpose**: Present testing strategy, results, and system evaluation

---

## 7.1 Testing Strategy

### 7.1.1 Testing Pyramid

```
┌─────────────────────────────────────────────────────────────────┐
│                      TESTING PYRAMID                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│                         ┌───────┐                               │
│                        /  E2E   \                               │
│                       /  Tests   \      ← Manual testing        │
│                      /____________\        (labeling workflow)  │
│                     /              \                             │
│                    /  Integration   \   ← API + DB tests        │
│                   /     Tests        \     (9 test files)       │
│                  /____________________\                          │
│                 /                      \                         │
│                /      Unit Tests        \  ← Handler functions  │
│               /__________________________\    (isolated)        │
│                                                                  │
│  Focus: API layer testing with database fixtures                │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 7.1.2 Test Coverage Goals

| Layer | Coverage Target | Actual | Notes |
|-------|-----------------|--------|-------|
| API Layer | 80% | ~75% | All CRUD operations |
| Database Layer | 70% | ~70% | Model validation |
| Dispatcher | 60% | ~50% | Handler logic |
| UI Layer | 30% | Manual | Streamlit limitations |

---

## 7.2 Test Implementation

### 7.2.1 Test File Structure

```
tests/
├── __init__.py
├── conftest.py                     # Shared fixtures
├── credential_test.py              # Authentication tests
├── sessions_test.py                # Session management tests
├── dataset_test.py                 # Dataset CRUD tests
├── patient_test.py                 # Patient CRUD tests
├── image_set_input_test.py         # ImageSet CRUD tests
├── image_input_test.py             # Image CRUD tests
├── image_set_evaluation_input_test.py  # Set evaluation tests
├── image_evaluation_input_test.py  # Image evaluation tests
├── get_evaluated_sets_test.py      # Query tests
└── valid_path_test.py              # Path validation tests
```

### 7.2.2 Fixtures (conftest.py)

```python
# tests/conftest.py

@pytest.fixture(scope="function")
def db_session():
    """
    Create in-memory SQLite database for testing.
    
    Ensures test isolation - each test gets fresh database.
    """
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    
    Session = sessionmaker(bind=engine)
    session = Session()
    
    yield session
    
    session.close()
    engine.dispose()


@pytest.fixture
def sample_doctor(db_session):
    """Create test doctor with hashed password."""
    doctor = Doctors(
        uuid=uuid4(),
        username="test_doctor",
        password=hash_password("secure_password"),
        full_name="Test Doctor",
        email="test@hospital.com",
    )
    db_session.add(doctor)
    db_session.commit()
    return doctor


@pytest.fixture
def sample_image_set(db_session, sample_patient):
    """Create test image set with sample data."""
    image_set = ImageSet(
        uuid=uuid4(),
        image_set_name="CQ500-CT-100",
        folder_path="cq500_dcm/CQ500-CT-100",
        num_images=25,
        patient_uuid=sample_patient.uuid,
        image_format=ImageFormat.DICOM,
    )
    db_session.add(image_set)
    db_session.commit()
    return image_set
```

### 7.2.3 Sample Test Cases

**Authentication Tests**:

```python
# tests/credential_test.py

class TestCredentials:
    
    def test_hash_password_produces_valid_hash(self):
        """Password hashing should produce verifiable hash."""
        password = "test_password_123"
        hashed = hash_password(password)
        
        assert hashed != password
        assert hashed.startswith("$argon2")
        # Verify the hash works
        ph.verify(hashed, password)
    
    def test_validate_password_success(self, db_session, sample_doctor):
        """Valid credentials should create session."""
        result = validate_password(
            db_session,
            username="test_doctor",
            password="secure_password",
        )
        
        assert result is not None
        assert isinstance(result, SessionRead)
        assert result.doctor_uuid == sample_doctor.uuid
    
    def test_validate_password_wrong_password(self, db_session, sample_doctor):
        """Wrong password should return None."""
        result = validate_password(
            db_session,
            username="test_doctor",
            password="wrong_password",
        )
        
        assert result is None
    
    def test_validate_password_unknown_user(self, db_session):
        """Unknown user should return None."""
        result = validate_password(
            db_session,
            username="nonexistent",
            password="any_password",
        )
        
        assert result is None
```

**ImageSet Tests**:

```python
# tests/image_set_input_test.py

class TestImageSetInput:
    
    def test_get_image_set_returns_valid_data(
        self, db_session, sample_image_set
    ):
        """Should retrieve ImageSet by UUID."""
        result = get_image_set(db_session, sample_image_set.uuid)
        
        assert result is not None
        assert result.uuid == sample_image_set.uuid
        assert result.image_set_name == "CQ500-CT-100"
        assert result.num_images == 25
    
    def test_get_image_set_returns_none_for_invalid_uuid(
        self, db_session
    ):
        """Should return None for unknown UUID."""
        result = get_image_set(db_session, uuid4())
        
        assert result is None
    
    def test_get_image_set_includes_images(
        self, db_session, sample_image_set, sample_images
    ):
        """Should include related images."""
        result = get_image_set(db_session, sample_image_set.uuid)
        
        assert result is not None
        assert len(result.images) == len(sample_images)
```

**Evaluation Tests**:

```python
# tests/image_evaluation_input_test.py

class TestImageEvaluationInput:
    
    def test_create_image_evaluation_success(
        self, db_session, sample_set_evaluation, sample_image
    ):
        """Should create image evaluation."""
        eval_create = ImageEvaluationCreate(
            image_set_evaluation_uuid=sample_set_evaluation.uuid,
            image_uuid=sample_image.uuid,
            region=Region.BasalCortex,
            basal_score_cortex_left=2,
            basal_score_cortex_right=3,
        )
        
        result = create_image_evaluation(db_session, eval_create)
        
        assert result is not None
        assert isinstance(result, uuid_lib.UUID)
    
    def test_score_validation_cortex_range(
        self, db_session, sample_set_evaluation, sample_image
    ):
        """Cortex scores should be 0-10."""
        eval_create = ImageEvaluationCreate(
            image_set_evaluation_uuid=sample_set_evaluation.uuid,
            image_uuid=sample_image.uuid,
            region=Region.BasalCortex,
            basal_score_cortex_left=15,  # Invalid
            basal_score_cortex_right=3,
        )
        
        with pytest.raises(ValidationError):
            create_image_evaluation(db_session, eval_create)
```

---

## 7.3 Test Results

### 7.3.1 Test Execution Summary

```
$ pytest tests/ -v

========================== test session starts ===========================
platform linux -- Python 3.13.0, pytest-8.0.0
collected 47 items

tests/credential_test.py::TestCredentials::test_hash_password... PASSED
tests/credential_test.py::TestCredentials::test_validate_password_success PASSED
tests/credential_test.py::TestCredentials::test_validate_password_wrong PASSED
tests/sessions_test.py::TestSessions::test_create_session PASSED
tests/sessions_test.py::TestSessions::test_get_session PASSED
tests/dataset_test.py::TestDataSet::test_get_all_datasets PASSED
tests/dataset_test.py::TestDataSet::test_get_dataset_by_uuid PASSED
tests/patient_test.py::TestPatient::test_create_patient PASSED
tests/patient_test.py::TestPatient::test_get_patient PASSED
tests/image_set_input_test.py::TestImageSetInput::test_get_image_set PASSED
tests/image_set_input_test.py::TestImageSetInput::test_get_with_images PASSED
tests/image_input_test.py::TestImageInput::test_create_image PASSED
tests/image_input_test.py::TestImageInput::test_get_image PASSED
tests/image_evaluation_input_test.py::TestImageEval::test_create PASSED
tests/image_evaluation_input_test.py::TestImageEval::test_validation PASSED
tests/image_set_evaluation_input_test.py::TestSetEval::test_create PASSED
tests/valid_path_test.py::TestPathValidation::test_valid_path PASSED
tests/valid_path_test.py::TestPathValidation::test_invalid_path PASSED
... (29 more tests)

========================== 47 passed in 2.34s ============================
```

### 7.3.2 Coverage Report

```
$ pytest --cov=medfabric/api --cov-report=term-missing

---------- coverage: platform linux, python 3.13.0 ----------
Name                                      Stmts   Miss  Cover
-------------------------------------------------------------
medfabric/api/__init__.py                     0      0   100%
medfabric/api/config.py                      15      2    87%
medfabric/api/credentials.py                 45      8    82%
medfabric/api/data_sets.py                   32      4    88%
medfabric/api/errors.py                       8      0   100%
medfabric/api/image_evaluation_input.py      28      3    89%
medfabric/api/image_input.py                 35      5    86%
medfabric/api/image_set_evaluation_input.py  30      4    87%
medfabric/api/image_set_input.py             38      6    84%
medfabric/api/patients.py                    25      3    88%
medfabric/api/sessions.py                    22      4    82%
-------------------------------------------------------------
TOTAL                                       278     39    86%
```

---

## 7.4 Functional Evaluation

### 7.4.1 Use Case Verification

| Use Case | Test Method | Result |
|----------|-------------|--------|
| UC1: Login | Automated + Manual | ✅ Pass |
| UC2: Register | Manual | ✅ Pass |
| UC3: Browse Datasets | Manual | ✅ Pass |
| UC4: Select Scans | Manual | ✅ Pass |
| UC5: View CT Slice | Manual | ✅ Pass |
| UC6: Navigate Slices | Manual | ✅ Pass |
| UC7: Adjust Windowing | Manual | ✅ Pass |
| UC8: Select Region | Manual | ✅ Pass |
| UC9: Enter Scores | Manual | ✅ Pass |
| UC10: Mark Quality | Manual | ✅ Pass |
| UC11: Submit | Automated + Manual | ✅ Pass |

### 7.4.2 Workflow Walkthrough

**Scenario**: Complete labeling session with CQ500 dataset

```
1. Login with test credentials → Dashboard displayed
2. Select "CQ500" dataset → Expand to show sets
3. Check 3 image sets → "Start Labeling" enabled
4. Click "Start Labeling" → Labeling page loads
5. View first slice → CT image displayed correctly
6. Adjust window width to 100 → Image contrast changes
7. Navigate to slice 12 → Image updates
8. Select "Basal Cortex" region → Score inputs appear
9. Enter scores (2, 3) → Slice marked COMPLETED
10. Repeat for other regions → All slices complete
11. Navigate to Set 2 → Second set loads
12. Mark as "Non-Ischemic" → Auto-validated
13. Check all sets VALID → Submit button appears
14. Click Submit → Redirected to Dashboard
15. Verify database → Evaluations stored correctly
```

---

## 7.5 Performance Evaluation

### 7.5.1 Image Loading Performance

| Image Type | Size | Load Time | Windowing Time |
|------------|------|-----------|----------------|
| DICOM (512×512) | 0.5 MB | 120 ms | 15 ms |
| DICOM (1024×1024) | 2.0 MB | 280 ms | 45 ms |
| JPEG (512×512) | 0.1 MB | 20 ms | N/A |

**Measurement Method**: `time.perf_counter()` around image loading functions

### 7.5.2 Event Processing Performance

| Metric | Value |
|--------|-------|
| Average events per session | 150-300 |
| Average handler execution | < 1 ms |
| Queue processing overhead | < 5 ms |
| Total rerun time | < 500 ms |

### 7.5.3 Database Performance

| Operation | Average Time | Notes |
|-----------|-------------|-------|
| Single record read | 2-5 ms | With joins |
| Batch insert (50 records) | 50-100 ms | In transaction |
| Dataset query (all sets) | 10-20 ms | With relationships |

---

## 7.6 Usability Evaluation

### 7.6.1 Evaluation Methodology

**Participants**: 3 researchers familiar with ASPECTS scoring

**Tasks**:
1. Login to system
2. Select 5 CT scans for labeling
3. Complete labeling for all sets
4. Submit evaluations

**Metrics**:
- Task completion time
- Error rate
- User satisfaction (1-5 scale)

### 7.6.2 Results Summary

| Participant | Completion Time | Errors | Satisfaction |
|-------------|-----------------|--------|--------------|
| P1 | 18 min | 2 | 4/5 |
| P2 | 22 min | 1 | 4/5 |
| P3 | 15 min | 0 | 5/5 |
| **Average** | **18.3 min** | **1** | **4.3/5** |

### 7.6.3 User Feedback

**Positive Feedback**:
- "Clear workflow, easy to understand"
- "Navigation is intuitive"
- "Status tracking is helpful"
- "Windowing controls work well"

**Improvement Suggestions**:
- "Add keyboard shortcuts for navigation"
- "Show ASPECTS region overlay on image"
- "Enable batch region assignment"
- "Add progress bar for session"

---

## 7.7 Comparison with Requirements

### 7.7.1 Functional Requirements Verification

| ID | Requirement | Met? | Evidence |
|----|-------------|------|----------|
| FR1 | User authentication | ✅ | Login/register pages working |
| FR2 | Dataset browsing | ✅ | Dashboard tree view |
| FR3 | CT slice viewing | ✅ | DICOM/JPEG rendering |
| FR4 | Windowing adjustment | ✅ | Window width/level controls |
| FR5 | Region selection | ✅ | Segmented control |
| FR6 | ASPECTS scoring | ✅ | Score input fields |
| FR7 | Multi-set labeling | ✅ | Set navigation |
| FR8 | Validation feedback | ✅ | Status tables |
| FR9 | Batch submission | ✅ | Submit all button |
| FR10 | Quality marking | ✅ | Low quality checkbox |

### 7.7.2 Non-Functional Requirements Verification

| ID | Requirement | Target | Actual | Met? |
|----|-------------|--------|--------|------|
| NFR1 | Response time | < 2s | ~0.5s | ✅ |
| NFR2 | Session persistence | Survive refresh | Yes | ✅ |
| NFR3 | Data integrity | No data loss | Verified | ✅ |
| NFR4 | Usability | Minimal training | 4.3/5 rating | ✅ |
| NFR5 | Extensibility | New scoring systems | Modular design | ✅ |

---

## 7.8 Limitations Identified

### 7.8.1 Technical Limitations

| Limitation | Impact | Potential Solution |
|------------|--------|-------------------|
| SQLite single-user | No concurrent access | Migrate to PostgreSQL |
| No real-time sync | Can't collaborate | WebSocket integration |
| Memory for large datasets | Slow with 1000+ sets | Pagination |
| No image preprocessing | Manual window adjustment | Auto-windowing |

### 7.8.2 Usability Limitations

| Limitation | Impact | Potential Solution |
|------------|--------|-------------------|
| No keyboard shortcuts | Slower navigation | Add hotkeys |
| No region overlay | Harder to identify regions | Image annotation layer |
| No undo | Must re-enter if mistake | Undo stack |
| No progress indicator | Unclear session progress | Progress bar |

---

## Figures to Include

1. Testing pyramid diagram
2. Test execution screenshot
3. Coverage report table
4. Performance benchmark charts
5. User satisfaction survey results
6. Requirements traceability matrix
