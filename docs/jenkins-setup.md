# Jenkins Pipeline Integration

This repository ships with a declarative Jenkins pipeline (`Jenkinsfile`) that automates running the scikit-learn + MLflow demo. The structure mirrors the ["Jenkins Tutorial"](https://www.datacamp.com/tutorial/jenkins-tutorial) from DataCamp, with stages adapted to this project.

## Prerequisites

1. A Jenkins controller (LTS 2.426+ recommended) running on Windows. The provided Jenkinsfile assumes the agent can execute Windows `bat` steps.
2. A Python 3.x installation on the Jenkins agent together with the Windows `py` launcher (default option). The Jenkinsfile invokes `py -3 -m venv ...`, so the launcher must be on `PATH` for the service account.
3. A Jenkins credential with permission to clone this repository (for private repos).
4. Sufficient disk space (~1 GB) and network access so Python packages can be downloaded during the first run.

## Jenkins Job Setup

1. **Create a Pipeline job**  
   - In Jenkins, click **New Item -> Pipeline**.  
   - Give it a name (for example, `aieng-mlflow-demo`) and click **OK**.
2. **Point the job at this repository**  
   - Under **Pipeline** set **Definition** to `Pipeline script from SCM`.  
   - Choose `Git`, supply the repository URL, and select the relevant credentials/branch.  
   - Ensure the `Script Path` remains `Jenkinsfile`.
3. **Apply and build**  
   - Save the configuration and trigger **Build Now**. Jenkins will:  
     - check out the repository,  
     - create a Python virtual environment and install packages from `requirements.txt`,  
     - run `main.py`, logging metrics and artefacts to MLflow.

## MLflow Outputs

- The pipeline forces `MLFLOW_TRACKING_URI=file:${WORKSPACE}/mlruns`, so each build writes to a local MLflow file store kept in the job workspace.
- Jenkins archives both `artifacts/` and `mlruns/` directories, making them downloadable from the build page (**Build -> Artifacts**). You can import the MLflow run directory into a local MLflow UI if desired.

## Customisation Tips

- **Experiment parameters** — edit the `python main.py ...` line inside the `Train Model` stage to tweak sample count, runtime, or MLflow experiment names used during CI runs.
- **GPU / larger instances** - label the Jenkins agent that has the required hardware and update the job to target that label.
- **Parallel agents** — wrap the stages in `when { branch "main" }` or similar if you only want the ML pipeline on selected branches, following the conditional examples in the DataCamp tutorial.

After the job succeeds you can extend the pipeline with additional stages (testing, model evaluation, deployment) reusing the skeleton provided in the tutorial and this Jenkinsfile.
