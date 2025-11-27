pipeline {
    agent any

    options {
        timestamps()
        skipDefaultCheckout(true)
    }

    environment {
        // MLflow yerel klasörü (workspace altı)
        MLFLOW_TRACKING_URI = "file:${WORKSPACE}/mlruns"
        PYTHONUNBUFFERED    = '1'
        PYTHONIOENCODING    = 'utf-8'
        LLM_MODEL_NAME      = 'sshleifer/tiny-gpt2'
        PATH                = 'C:\\Program Files\\Git\\cmd;%PATH%'
        GIT_PYTHON_GIT_EXECUTABLE = 'C:\\Program Files\\Git\\cmd\\git.exe'

        // Git & DVC ayarları
        GIT_TARGET_BRANCH   = 'main'

        // Local DVC remote
        DVC_REMOTE_NAME     = 'local-storage'
        DVC_REMOTE_PATH     = 'C:\\dvc-storage'

        // GitHub repo yolun: owner/repo
        GIT_REPO_PATH       = 'SeyitKaanGunes/mlflow'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Setup Python') {
            steps {
                bat '''
                  if not exist ".venv\\Scripts\\python.exe" (
                    py -3 -m venv .venv
                  )
                  call .venv\\Scripts\\activate
                  if not exist "%WORKSPACE%\\.pip-cache" (
                    mkdir "%WORKSPACE%\\.pip-cache"
                  )
                  set "PIP_CACHE_DIR=%WORKSPACE%\\.pip-cache"
                  python -m pip install --upgrade pip
                  if exist requirements.txt (
                    python -m pip install -r requirements.txt
                  )
                '''
            }
        }

        stage('Static Checks') {
            steps {
                bat '''
                  call .venv\\Scripts\\activate
                  python -m py_compile main.py
                '''
            }
        }

        stage('Train Model') {
            steps {
                bat '''
                  call .venv\\Scripts\\activate
                  python main.py --samples 300 --experiment-name JenkinsTrain ^
                    --llm-model-name %LLM_MODEL_NAME%
                '''
            }
        }

        stage('Retrain (Smoke)') {
            steps {
                bat '''
                  call .venv\\Scripts\\activate
                  python main.py --samples 80 --experiment-name JenkinsSmoke ^
                    --artifact-dir temp_artifacts\\jenkins_smoke ^
                    --llm-model-name %LLM_MODEL_NAME%
                '''
            }
        }

        stage('MLSecOps (Garak)') {
            steps {
                bat '''
                  call .venv\\Scripts\\activate
                  python run_mlsecops.py --model-name %LLM_MODEL_NAME% ^
                    --probes promptinject.HijackNevermind,dan.Dan_8_0 ^
                    --generations 2 ^
                    --output-dir artifacts\\mlsecops
                '''
            }
        }

        stage('DVC Snapshot') {
            steps {
                withCredentials([
                    string(credentialsId: 'github-push', variable: 'GIT_TOKEN')
                ]) {
                    bat '''
                      call .venv\\Scripts\\activate
                      setlocal EnableDelayedExpansion

                      echo [DVC] Git user set
                      set "GIT_CONFIG_GLOBAL=nul"
                      set "GIT_CONFIG_SYSTEM=nul"
                      set "GIT_TERMINAL_PROMPT=0"
                      set "GIT_ASKPASS=echo"
                      set "GCM_INTERACTIVE=Never"
                      git config user.email "jenkins@local"
                      git config user.name  "Jenkins CI"

                      for %%D in (artifacts mlruns) do (
                        if exist "%%D" (
                          echo [DVC] dvc add %%D
                          python -m dvc add "%%D"
                        ) else (
                          echo [DVC] Skipping %%D because it does not exist.
                        )
                      )

                      if exist artifacts.dvc git add artifacts.dvc
                      if exist mlruns.dvc    git add mlruns.dvc
                      if exist .gitignore    git add .gitignore
                      if exist Jenkinsfile   git add Jenkinsfile
                      if exist requirements.txt git add requirements.txt

                      git diff --cached --quiet
                      if errorlevel 1 (
                        echo [DVC] Git commit
                        git commit -m "chore: snapshot data via Jenkins"
                        set "SHOULD_PUSH=1"
                      ) else (
                        echo [DVC] No git changes detected.
                        set "SHOULD_PUSH=0"
                      )

                      echo [DVC] Configure DVC remote %DVC_REMOTE_NAME% -> %DVC_REMOTE_PATH%
                      if not exist "%DVC_REMOTE_PATH%" (
                        mkdir "%DVC_REMOTE_PATH%" || (
                          echo [DVC] Unable to create DVC remote path %DVC_REMOTE_PATH%.
                          exit /b 1
                        )
                      )
                      python -m dvc remote add --local %DVC_REMOTE_NAME% "%DVC_REMOTE_PATH%" --force

                      echo [DVC] dvc push
                      python -m dvc push -r %DVC_REMOTE_NAME% -v

                      if "!SHOULD_PUSH!"=="1" (
                        set "PUSH_REMOTE=https://github.com/%GIT_REPO_PATH%.git"
                        echo [DVC] git push to !PUSH_REMOTE! (http.extraheader, bearer token)

                        git -c credential.helper= ^
                            -c http.extraheader="AUTHORIZATION: bearer %GIT_TOKEN%" ^
                            push "!PUSH_REMOTE!" HEAD:%GIT_TARGET_BRANCH% || (
                                echo [DVC] Git push failed, but build will continue.
                                exit /b 0
                            )
                      ) else (
                        echo [DVC] Git push skipped; nothing to commit.
                      )

                      endlocal
                    '''
                }
            }
        }

        stage('Post Actions') {
            steps {
                bat '''
                  if exist artifacts (
                    echo [Post] Archiving artifacts directory
                  )
                '''
                archiveArtifacts artifacts: 'artifacts/**/*', fingerprint: true, allowEmptyArchive: true
                archiveArtifacts artifacts: 'mlruns/**/*',     fingerprint: true, allowEmptyArchive: true
            }
        }
    }
}
