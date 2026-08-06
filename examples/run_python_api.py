from aiskg import run_pipeline

result = run_pipeline(
    "configs/manuscript_frozen.yaml",
    run_id="python-api-example",
    clean=True,
)
print(result["release_zip"])
