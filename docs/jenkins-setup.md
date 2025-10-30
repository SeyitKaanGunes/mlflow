# Jenkins Pipeline Integration

This repository ships with a declarative Jenkins pipeline (`Jenkinsfile`) that automates running the AutoGluon + MLflow demo. The structure mirrors the ["Jenkins Tutorial"](https://www.datacamp.com/tutorial/jenkins-tutorial) from DataCamp, with stages adapted to this project.

## Prerequisites

1. A Jenkins controller (LTS 2.426+ recommended) with Docker installed on the build agent. The pipeline executes inside the lightweight `python:3.10-slim` container, so no Python needs to be pre-installed on the host.
2. A Jenkins credential with permission to clone this repository (for private repos).
3. Sufficient disk space (~6 GB) and network access so AutoGluon can download its model backbones during the first run.

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
     - spin up the Docker agent defined in the Jenkinsfile,  
     - install system-level dependencies required by AutoGluon and Matplotlib,  
     - create a virtual environment, install Python packages from `requirements.txt`,  
     - run `main.py`, logging metrics and artefacts to MLflow.

## MLflow Outputs

- The pipeline forces `MLFLOW_TRACKING_URI=file:${WORKSPACE}/mlruns`, so each build writes to a local MLflow file store kept in the job workspace.
- Jenkins archives both `artifacts/` and `mlruns/` directories, making them downloadable from the build page (**Build -> Artifacts**). You can import the MLflow run directory into a local MLflow UI if desired.

## Customisation Tips

- **Experiment parameters** — edit the `python main.py ...` line inside the `Train Model` stage to tweak sample count, runtime, or MLflow experiment names used during CI runs.
- **GPU / larger instances** — swap the Docker image with one that includes CUDA, or remove the Docker block entirely if you want to target a dedicated machine label.
- **Parallel agents** — wrap the stages in `when { branch "main" }` or similar if you only want the ML pipeline on selected branches, following the conditional examples in the DataCamp tutorial.

After the job succeeds you can extend the pipeline with additional stages (testing, model evaluation, deployment) reusing the skeleton provided in the tutorial and this Jenkinsfile.
