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

        stage('Python Dependencies') {
            steps {
                bat '''
                  py -3 -m venv .venv
                  call .venv\\Scripts\\activate
                  python -m pip install --upgrade pip
                  if exist requirements.txt (
                    python -m pip install -r requirements.txt
                  )
                  rem DVC'yi venv'e kur (PATH derdi olmasın)
                  python -m pip install dvc
                '''
            }
        }

        stage('Train Model') {
            steps {
                bat '''
                  call .venv\\Scripts\\activate
                  python main.py --samples 200 --experiment-name JenkinsDemo
                '''
            }
        }

        stage('Publish Code & DVC Data') {
            steps {
                withCredentials([
                    usernamePassword(credentialsId: 'github-push', usernameVariable: 'GIT_USERNAME', passwordVariable: 'GIT_TOKEN')
                ]) {
                    bat '''
                      call .venv\\Scripts\\activate
                      setlocal EnableDelayedExpansion

                      echo [Publish] Git user set
                      git config user.email "jenkins@local"
                      git config user.name  "Jenkins CI"

                      rem --- DVC add: artifacts & mlruns varsa ekle ---
                      for %%D in (artifacts mlruns) do (
                        if exist "%%D" (
                          echo [Publish] dvc add %%D
                          py -m dvc add "%%D"
                        ) else (
                          echo [Publish] Skipping %%D because it does not exist.
                        )
                      )

                      rem --- Git commit hazırlığı ---
                      if exist artifacts.dvc git add artifacts.dvc
                      if exist mlruns.dvc    git add mlruns.dvc
                      if exist .gitignore    git add .gitignore
                      if exist Jenkinsfile   git add Jenkinsfile
                      if exist requirements.txt git add requirements.txt

                      git diff --cached --quiet
                      if errorlevel 1 (
                        echo [Publish] Git commit
                        git commit -m "chore: update tracked data via Jenkins"
                        set "SHOULD_PUSH=1"
                      ) else (
                        echo [Publish] No git changes detected.
                        set "SHOULD_PUSH=0"
                      )

                      rem --- DVC remote (local) ---
                      echo [Publish] Configure DVC remote %DVC_REMOTE_NAME% -> %DVC_REMOTE_PATH%
                      py -m dvc remote remove %DVC_REMOTE_NAME% 2>nul
                      py -m dvc remote add --local %DVC_REMOTE_NAME% "%DVC_REMOTE_PATH%" --force
                      py -m dvc remote default %DVC_REMOTE_NAME% 1>nul 2>nul

                      rem --- DVC push ---
                      echo [Publish] DVC push
                      py -m dvc push -r %DVC_REMOTE_NAME% -v

                      rem --- Git push (PAT ile güvenli URL) ---
                      if "!SHOULD_PUSH!"=="1" (
                        set "PUSH_URL=https://%GIT_USERNAME%:%GIT_TOKEN%@github.com/%GIT_REPO_PATH%.git"
                        echo [Publish] git push to !PUSH_URL!
                        git push "!PUSH_URL!" HEAD:%GIT_TARGET_BRANCH%
                      ) else (
                        echo [Publish] Git push skipped; nothing to commit.
                      )

                      endlocal
                    '''
                }
            }
        }
    }

    post {
        success {
            archiveArtifacts artifacts: 'artifacts/**/*', fingerprint: true, allowEmptyArchive: true
            archiveArtifacts artifacts: 'mlruns/**/*',     fingerprint: true, allowEmptyArchive: true
        }
        always {
            bat 'if exist .venv rmdir /S /Q .venv'
        }
    }
}
