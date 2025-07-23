# Multi-Generation Resume Tailoring with Quality Scoring

## Overview

This feature enhancement addresses the inconsistency in resume tailoring quality by implementing a multi-candidate generation approach with automated quality scoring and selection. Instead of generating a single tailored resume, the system will create multiple candidates and select the best one based on comprehensive quality metrics.

## Problem Statement

The current single-generation approach sometimes produces resumes with:
- **Inconsistent content density** - Some resumes are over-pruned with sparse sections
- **Variable quality** - Output depends on single LLM generation "luck"
- **No quality validation** - No automated check for content adequacy
- **Layout awareness gaps** - PDF reduction without visual context understanding

## Proposed Solution

### 1. Multi-Candidate Generation

Generate 3 diverse resume candidates using slight prompt variations:

```python
async def generate_multiple_candidates(
    self,
    job_metadata: dict,
    master_tex: str,
    notion_page_id: str,
    candidate_count: int = 3
) -> list[ResumeCandidateScore]:
    """Generate multiple tailored resume candidates with scoring."""

    candidates = []

    for i in range(candidate_count):
        # Apply slight prompt variation for diversity
        variant_prompt = self._create_prompt_variant(base_prompt, variation_index=i)

        # Generate candidate
        candidate_tex = await self._generate_single_resume(
            variant_prompt, job_metadata, master_tex
        )

        # Score the candidate
        score = await self._score_candidate(candidate_tex, job_metadata)

        candidates.append(ResumeCandidateScore(
            tex_content=candidate_tex,
            score=score,
            generation_index=i
        ))

    return candidates
```

### 2. Prompt Variation Strategies

Create diversity through systematic prompt variations:

- **Variation A**: Standard approach with balanced optimization
- **Variation B**: Slightly more conservative content preservation
- **Variation C**: Focus on keyword density and relevance

### 3. Comprehensive Quality Scoring System

#### Core Scoring Metrics

```python
@dataclass
class QualityScore:
    content_density: float        # 0-1: Measures content adequacy
    relevance_score: float        # 0-1: Job alignment strength
    page_utilization: float       # 0-1: Effective space usage
    structural_integrity: float   # 0-1: LaTeX validity & formatting
    keyword_coverage: float       # 0-1: Important terms preserved
    overall_score: float          # Weighted composite score

    # Detailed breakdowns
    skills_per_category: dict[str, int]
    bullets_per_section: dict[str, int]
    metrics_preserved: int
    latex_errors: list[str]
```

#### Scoring Algorithm

```python
async def _score_candidate(
    self,
    candidate_tex: str,
    job_metadata: dict
) -> QualityScore:
    """Comprehensive candidate scoring."""

    # 1. Content Density Analysis (30% weight)
    content_density = self._analyze_content_density(candidate_tex)

    # 2. Relevance Scoring (25% weight)
    relevance_score = await self._calculate_relevance_score(
        candidate_tex, job_metadata
    )

    # 3. Page Utilization (20% weight)
    page_utilization = await self._measure_page_utilization(candidate_tex)

    # 4. Structural Integrity (15% weight)
    structural_integrity = self._validate_latex_structure(candidate_tex)

    # 5. Keyword Coverage (10% weight)
    keyword_coverage = self._analyze_keyword_preservation(
        candidate_tex, job_metadata
    )

    # Calculate weighted overall score
    overall_score = (
        content_density * 0.30 +
        relevance_score * 0.25 +
        page_utilization * 0.20 +
        structural_integrity * 0.15 +
        keyword_coverage * 0.10
    )

    return QualityScore(...)
```

### 4. Content Density Analysis

```python
def _analyze_content_density(self, tex_content: str) -> float:
    """Measure content adequacy across sections."""

    density_metrics = {
        'skills_per_category': self._count_skills_per_category(tex_content),
        'bullets_per_experience': self._count_experience_bullets(tex_content),
        'bullets_per_project': self._count_project_bullets(tex_content),
        'summary_sentences': self._count_summary_sentences(tex_content)
    }

    # Apply thresholds from content density requirements
    thresholds = {
        'min_skills_per_category': 6,
        'min_bullets_per_experience': 3,
        'min_bullets_per_project': 2,
        'min_summary_sentences': 2
    }

    # Calculate density score based on threshold compliance
    return self._calculate_density_score(density_metrics, thresholds)
```

### 5. Visual Layout Integration

Enhance PDF reduction with screenshot analysis:

```python
async def _reduce_pdf_with_visual_context(
    self,
    current_tex: str,
    current_pdf_path: Path,
    target_output_dir: Path
) -> tuple[str, Path]:
    """PDF reduction with visual layout awareness."""

    # Convert PDF to images for visual analysis
    pdf_screenshots = self._convert_pdf_to_images(current_pdf_path)

    # Enhanced reduction prompt with visual context
    reduction_prompt = self._build_visual_reduction_prompt(
        current_tex=current_tex,
        screenshots=pdf_screenshots,
        page_count=self.latex_service.get_pdf_page_count(current_pdf_path)
    )

    # Generate multiple reduction candidates
    reduction_candidates = await self._generate_reduction_candidates(
        reduction_prompt, candidate_count=2
    )

    # Score and select best reduction
    best_reduction = await self._select_best_reduction(reduction_candidates)

    return best_reduction
```

## Implementation Plan

### Phase 1: Core Multi-Generation Framework
- [ ] Implement `generate_multiple_candidates()` method
- [ ] Create prompt variation system
- [ ] Add basic candidate storage and comparison
- [ ] Update `TailorService.tailor_resume()` to use multi-generation

### Phase 2: Quality Scoring System
- [ ] Implement content density analysis
- [ ] Add relevance scoring with keyword matching
- [ ] Create LaTeX structure validation
- [ ] Build composite scoring algorithm

### Phase 3: Visual Layout Integration
- [ ] Add PDF-to-image conversion using `pdf2image`
- [ ] Enhance reduction prompts with screenshot context
- [ ] Update `_reduce_pdf_to_one_page()` with visual awareness
- [ ] Add page utilization scoring

### Phase 4: Configuration and Optimization
- [ ] Add configuration options for candidate count
- [ ] Implement scoring weight customization
- [ ] Add performance monitoring and logging
- [ ] Create quality metrics dashboard

## Configuration Options

```python
# In settings
MULTI_GENERATION_ENABLED: bool = True
GENERATION_CANDIDATE_COUNT: int = 3
SCORING_WEIGHTS: dict = {
    "content_density": 0.30,
    "relevance_score": 0.25,
    "page_utilization": 0.20,
    "structural_integrity": 0.15,
    "keyword_coverage": 0.10
}
MIN_CONTENT_THRESHOLDS: dict = {
    "skills_per_category": 6,
    "bullets_per_experience": 3,
    "bullets_per_project": 2
}
```

## Expected Benefits

1. **Consistency**: Eliminates single-generation variance
2. **Quality Assurance**: Automated validation of content adequacy
3. **Visual Awareness**: PDF reduction with layout understanding
4. **Measurable Improvement**: Quantifiable quality metrics
5. **Adaptability**: Tunable scoring weights for different priorities

## Performance Considerations

- **Generation Time**: ~3x increase (mitigated by parallel generation)
- **Token Usage**: ~3x increase in generation tokens
- **Processing Overhead**: Scoring computation adds ~10-15% overhead
- **Storage**: Temporary storage for multiple candidates

## Metrics & Monitoring

Track system performance with:
- Average quality scores over time
- Score distribution across generation variants
- Content density compliance rates
- User satisfaction indicators (manual feedback)
- Generation time and token usage statistics

## Future Enhancements

- **Adaptive Scoring**: Machine learning to improve scoring accuracy
- **User Feedback Integration**: Learn from manual quality assessments
- **Domain-Specific Scoring**: Different weights for different job types
- **Real-time Quality Indicators**: Live scoring during generation
