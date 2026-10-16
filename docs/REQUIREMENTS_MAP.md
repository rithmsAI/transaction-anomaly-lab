# Employer requirements to inspectable evidence

Reviewed October 16, 2026. These official employer postings guide skill selection, not an assertion of qualification, salary fit, or application eligibility. Several are senior roles that require experience beyond this project.

| Employer / role | Relevant emphasis | Evidence in this repository | Remaining gap |
|---|---|---|---|
| [Zscaler: Senior Machine Learning Engineer](https://job-boards.greenhouse.io/zscaler/jobs/5246776007) | Risk identification, precision/recall, deployment and monitoring | Baseline comparison; fixed-threshold evaluation; drift diagnostic; CI | No agent implementation, threat research, or production monitoring |
| [Alpaca: Senior Data Scientist, AI Evaluation](https://job-boards.greenhouse.io/alpaca/jobs/6147548004) | Repeatable evaluations, Python/SQL, statistical rigor | Five-seed experiment; variability reporting; SQL audit aggregates | No LLM evaluation, human-ground-truth validation, or production experience demonstrated |
| [Canonical: Python and Kubernetes Software Engineer](https://job-boards.greenhouse.io/canonical/jobs/5703396) | Python delivery, containers, testing, cloud workflows | Typed API; Docker; unit/integration tests; container CI | No Kubernetes cluster or cloud deployment demonstrated |

## What a reviewer can inspect quickly

1. Read the result table and limitations in the README.
2. Open `api.py` to inspect validation, authentication, persistence, and retry behavior.
3. Read `tests/test_api.py` for failure cases, concurrent retries, and restart persistence.
4. Review `evaluate_shift.py` and the recorded five-seed output.
5. Open GitHub Actions to check the actual latest test and container results.

## Next portfolio directions

- A separate retrieval/LLM evaluation project with a frozen question set, citation correctness checks, abstention handling, and cost/latency measurements.
- A separate cloud-infrastructure project with infrastructure as code, least-privilege access, deployment evidence, and teardown instructions.

These are future work, not capabilities claimed by the current repository. A portfolio complements education and experience; it does not replace seniority requirements.
